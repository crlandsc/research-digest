"""arXiv Atom/XML API fetcher and parser."""

import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import httpx

from research_digest.config import ArxivSourceConfig
from research_digest.models import Paper

logger = logging.getLogger(__name__)

ARXIV_API_URL = "https://export.arxiv.org/api/query"
NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
    "arxiv": "http://arxiv.org/schemas/atom",
}
REQUEST_DELAY_SECONDS = 3.0
MAX_RESULTS_PER_PAGE = 2000
USER_AGENT = "research-digest/0.1.0 (local CLI tool)"

_VERSION_RE = re.compile(r"v\d+$")


def build_query(
    config: ArxivSourceConfig,
    start_date: datetime,
    end_date: datetime,
) -> str:
    """Build the search_query parameter for the arXiv API.

    Returns plain text — httpx handles URL encoding when passed as a param.
    Combines categories (OR'd), keywords (OR'd), joined with AND if both present.
    Date filter is always appended.
    """
    parts: list[str] = []

    if config.categories:
        cats = " OR ".join(f"cat:{c}" for c in config.categories)
        parts.append(f"({cats})")

    if config.keyword_queries:
        kws = " OR ".join(f'all:"{kw}"' for kw in config.keyword_queries)
        parts.append(f"({kws})")

    query = " AND ".join(parts) if parts else "all:*"

    # Date range in YYYYMMDDHHMM format (GMT)
    start_str = start_date.strftime("%Y%m%d%H%M")
    end_str = end_date.strftime("%Y%m%d%H%M")
    query += f" AND submittedDate:[{start_str} TO {end_str}]"

    return query


def compute_date_range(
    lookback_days: int,
    since_last_run: datetime | None = None,
) -> tuple[datetime, datetime]:
    """Compute (start_date, end_date) for a fetch query.

    If since_last_run is provided, uses that as start. Otherwise uses lookback_days + 1 day buffer.
    """
    end_date = datetime.now(timezone.utc)
    if since_last_run is not None:
        return (since_last_run, end_date)
    # +1 day buffer for arXiv submission-to-listing lag
    start_date = end_date - timedelta(days=lookback_days + 1)
    return (start_date, end_date)


def fetch_papers(
    config: ArxivSourceConfig,
    start_date: datetime,
    end_date: datetime,
) -> list[Paper]:
    """Fetch papers from arXiv API with pagination."""
    query = build_query(config, start_date, end_date)
    all_papers: dict[str, Paper] = {}
    start = 0
    max_to_fetch = config.max_results_per_run
    page_size = min(MAX_RESULTS_PER_PAGE, max_to_fetch)

    logger.info("arXiv query: %s", query)

    with httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=60.0,
    ) as client:
        while start < max_to_fetch:
            params = {
                "search_query": query,
                "start": str(start),
                "max_results": str(min(page_size, max_to_fetch - start)),
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
            logger.debug("Fetching page start=%d", start)
            response = _request_with_retry(client, params)
            papers, total = parse_arxiv_response(response.text)

            if not papers:
                break

            for p in papers:
                all_papers.setdefault(p.external_id, p)

            start += len(papers)
            if start >= total or start >= max_to_fetch:
                break

            time.sleep(REQUEST_DELAY_SECONDS)

    result = list(all_papers.values())
    logger.info("Fetched %d unique papers from arXiv", len(result))
    return result


def _request_with_retry(
    client: httpx.Client,
    params: dict[str, str],
    max_retries: int = 2,
) -> httpx.Response:
    """Make request with retry on 429/503."""
    for attempt in range(max_retries + 1):
        response = client.get(ARXIV_API_URL, params=params)
        if response.status_code in (429, 503) and attempt < max_retries:
            wait = int(response.headers.get("Retry-After", 10))
            logger.warning("arXiv returned %d, retrying in %ds...", response.status_code, wait)
            time.sleep(wait)
            continue
        response.raise_for_status()
        return response
    raise RuntimeError("unreachable")


def parse_arxiv_response(xml_text: str) -> tuple[list[Paper], int]:
    """Parse Atom XML response into Papers. Returns (papers, total_results)."""
    root = ET.fromstring(xml_text)

    total_el = root.find("opensearch:totalResults", NAMESPACES)
    total = int(total_el.text) if total_el is not None and total_el.text else 0

    papers: list[Paper] = []
    for entry in root.findall("atom:entry", NAMESPACES):
        id_el = entry.find("atom:id", NAMESPACES)
        if id_el is None or id_el.text is None:
            continue
        # Skip error entries
        if "/api/errors#" in id_el.text:
            continue
        try:
            papers.append(_entry_to_paper(entry))
        except Exception:
            logger.warning("Failed to parse entry: %s", id_el.text, exc_info=True)

    return (papers, total)


def _entry_to_paper(entry: ET.Element) -> Paper:
    """Convert a single Atom entry to a Paper model."""
    id_text = _text(entry, "atom:id")
    raw_id = id_text.replace("http://arxiv.org/abs/", "").replace("https://arxiv.org/abs/", "")
    external_id = _VERSION_RE.sub("", raw_id)

    title = _normalize_whitespace(_text(entry, "atom:title"))
    abstract = _normalize_whitespace(_text(entry, "atom:summary"))

    authors = [
        name_el.text
        for author in entry.findall("atom:author", NAMESPACES)
        if (name_el := author.find("atom:name", NAMESPACES)) is not None and name_el.text
    ]

    categories = [
        cat.get("term")
        for cat in entry.findall("atom:category", NAMESPACES)
        if cat.get("term")
    ]

    published_at = _parse_datetime(_text(entry, "atom:published"))
    updated_text = entry.find("atom:updated", NAMESPACES)
    updated_at = _parse_datetime(updated_text.text) if updated_text is not None and updated_text.text else None

    canonical_url = id_text

    pdf_url = None
    for link in entry.findall("atom:link", NAMESPACES):
        if link.get("title") == "pdf":
            pdf_url = link.get("href")
            break

    return Paper(
        source="arxiv",
        external_id=external_id,
        title=title,
        authors=authors,
        abstract=abstract,
        categories=categories,
        published_at=published_at,
        updated_at=updated_at,
        canonical_url=canonical_url,
        pdf_url=pdf_url,
    )


def _text(element: ET.Element, tag: str) -> str:
    """Extract text from a child element or return empty string."""
    el = element.find(tag, NAMESPACES)
    return el.text.strip() if el is not None and el.text else ""


def _normalize_whitespace(s: str) -> str:
    """Collapse newlines and multiple spaces into single spaces."""
    return " ".join(s.split())


def _parse_datetime(s: str) -> datetime:
    """Parse ISO 8601 datetime string to UTC datetime."""
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)
