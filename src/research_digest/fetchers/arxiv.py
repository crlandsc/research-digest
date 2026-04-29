"""arXiv Atom/XML API fetcher and parser."""

import logging
import random
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

# Retry tuning. arXiv is fronted by Fastly; on shared CI egress IPs the rate-limit
# window can persist many minutes. Use exponential backoff with jitter and a generous
# per-attempt cap so a single fetch can survive a transient CDN throttle.
RETRY_BACKOFF_BASE = 30.0
RETRY_BACKOFF_CAP = 480.0
RETRY_JITTER = 30.0
DEFAULT_MAX_RETRIES = 6
# Random startup jitter desyncs us from other GH Actions cron jobs that fire at :05.
INITIAL_JITTER_MAX = 10.0


class ArxivRateLimitError(RuntimeError):
    """Raised when arXiv persistently returns 429 after all retries."""

_VERSION_RE = re.compile(r"v\d+$")

# Resource link patterns — order matters (more specific patterns first)
_RESOURCE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Demo", re.compile(r"https?://huggingface\.co/spaces/[^\s,;)}\]\"'<>]+", re.IGNORECASE)),
    ("Dataset", re.compile(r"https?://huggingface\.co/datasets/[^\s,;)}\]\"'<>]+", re.IGNORECASE)),
    ("Dataset", re.compile(r"https?://zenodo\.org/records?/[^\s,;)}\]\"'<>]+", re.IGNORECASE)),
    ("Model", re.compile(r"https?://huggingface\.co/(?!spaces/|datasets/|docs/|blog/|papers/)[^\s,;)}\]\"'<>]+", re.IGNORECASE)),
    ("Demo", re.compile(r"https?://replicate\.com/[^\s,;)}\]\"'<>]+", re.IGNORECASE)),
    ("Colab", re.compile(r"https?://colab\.research\.google\.com/[^\s,;)}\]\"'<>]+", re.IGNORECASE)),
    ("Code", re.compile(r"https?://(?:github\.com|gitlab\.com|bitbucket\.org)/[^\s,;)}\]\"'<>]+", re.IGNORECASE)),
]


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

    logger.info("arXiv query (%d categories, %d keywords): %s",
                len(config.categories), len(config.keyword_queries), query)
    logger.info("arXiv URL: %s", ARXIV_API_URL)
    logger.info("Max results: %d, page size: %d", max_to_fetch, page_size)

    jitter = random.uniform(0, INITIAL_JITTER_MAX)
    if jitter > 0:
        logger.info("Initial jitter: sleeping %.1fs before first arXiv request", jitter)
        time.sleep(jitter)

    with httpx.Client(
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/atom+xml, application/xml;q=0.9, */*;q=0.8",
        },
        timeout=90.0,
        follow_redirects=True,
    ) as client:
        while start < max_to_fetch:
            params = {
                "search_query": query,
                "start": str(start),
                "max_results": str(min(page_size, max_to_fetch - start)),
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
            logger.info("Fetching page start=%d", start)
            response = _request_with_retry(client, params)
            logger.info("Response: HTTP %d, %d bytes", response.status_code, len(response.text))
            papers, total = parse_arxiv_response(response.text)
            logger.info("Parsed %d papers from page (total available: %d)", len(papers), total)

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


def _compute_backoff(attempt: int) -> float:
    """Exponential backoff with jitter, capped at RETRY_BACKOFF_CAP.

    attempt is 0-indexed: 0 → ~30s, 1 → ~60s, 2 → ~120s, 3 → ~240s, 4+ → ~480s.
    """
    base = min(RETRY_BACKOFF_BASE * (2**attempt), RETRY_BACKOFF_CAP)
    return base + random.uniform(0, RETRY_JITTER)


def _request_with_retry(
    client: httpx.Client,
    params: dict[str, str],
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> httpx.Response:
    """Make request with exponential backoff + jitter on transient errors.

    Retries on: any 5xx, 406 (CDN block), 408 (timeout), 429 (rate limit),
    plus ReadTimeout and ConnectError exceptions.
    GH Actions shared egress IPs are commonly rate limited by arXiv's Fastly CDN
    and the rate-limit window can persist several minutes, so we backoff
    exponentially up to RETRY_BACKOFF_CAP per attempt and honor Retry-After
    when present. Persistent 429s raise ArxivRateLimitError so the caller
    (and CI workflow) can distinguish rate limiting from other failures.
    """
    url = httpx.URL(ARXIV_API_URL).copy_merge_params(params)
    logger.info("Request URL (first 200 chars): %s", str(url)[:200])

    last_status: int | None = None

    for attempt in range(max_retries + 1):
        attempt_label = f"attempt {attempt + 1}/{max_retries + 1}"
        logger.info("arXiv request %s starting...", attempt_label)
        start_time = time.monotonic()
        try:
            response = client.get(ARXIV_API_URL, params=params)
        except (httpx.ReadTimeout, httpx.ConnectError) as e:
            elapsed = time.monotonic() - start_time
            logger.error("arXiv %s error %s after %.1fs: %s",
                         type(e).__name__, attempt_label, elapsed, e)
            if attempt < max_retries:
                wait = _compute_backoff(attempt)
                logger.warning("Retrying in %.0fs...", wait)
                time.sleep(wait)
                continue
            logger.error("All %d attempts exhausted (network error).", max_retries + 1)
            raise

        elapsed = time.monotonic() - start_time
        last_status = response.status_code
        logger.info("arXiv response %s: HTTP %d in %.1fs, headers: %s",
                     attempt_label, response.status_code, elapsed,
                     {k: v for k, v in response.headers.items()
                      if k.lower() in ("retry-after", "x-ratelimit-remaining", "x-cache", "server", "content-type")})

        retryable = response.status_code >= 500 or response.status_code in (406, 408, 429)
        if retryable:
            if attempt < max_retries:
                retry_after = response.headers.get("Retry-After")
                backoff = _compute_backoff(attempt)
                try:
                    ra_seconds = float(retry_after) if retry_after else 0.0
                except ValueError:
                    ra_seconds = 0.0
                # Honor Retry-After when present, but never wait less than computed backoff.
                wait = max(ra_seconds, backoff)
                body_preview = response.text[:200] if response.text else "(empty)"
                logger.warning("arXiv returned %d. Retry-After: %s. Body: %s. Waiting %.0fs (attempt %d)...",
                               response.status_code, retry_after, body_preview, wait, attempt + 1)
                time.sleep(wait)
                continue
            # Out of retries on a retryable status — break out so we raise a typed error below.
            logger.error("arXiv unexpected status %d after final retry. Body: %s",
                         response.status_code, response.text[:500])
            break

        # Non-retryable response: raise immediately.
        response.raise_for_status()
        return response

    logger.error("All %d attempts exhausted. Last status: %s", max_retries + 1, last_status)
    if last_status == 429:
        raise ArxivRateLimitError(
            f"arXiv rate limit (HTTP 429) persisted after {max_retries + 1} attempts. "
            "Likely a shared CI egress IP is throttled by Fastly; retry from a fresh runner."
        )
    raise RuntimeError(f"arXiv API failed after {max_retries + 1} attempts (last status {last_status})")


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

    # Extract code URL and resource links from comment and abstract
    comment = _text(entry, "arxiv:comment")
    code_url, resource_links = _extract_resource_links(comment, abstract)

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
        code_url=code_url,
        resource_links=resource_links,
    )


def _extract_resource_links(*texts: str) -> tuple[str | None, dict[str, str]]:
    """Extract code URL and resource links from text fields.

    Returns (code_url, resource_links) where resource_links maps labels to URLs.
    Searches comment first, then abstract. Each pattern only matches once
    (first occurrence). Labels: Code, Model, Demo, Dataset, Colab.
    """
    combined = " ".join(texts)
    code_url = None
    links: dict[str, str] = {}

    for label, pattern in _RESOURCE_PATTERNS:
        if label in links:
            continue  # only first match per label
        match = pattern.search(combined)
        if match:
            url = match.group(0).rstrip(".")
            links[label] = url
            if label == "Code" and code_url is None:
                code_url = url

    return (code_url, links)


def _extract_code_url(*texts: str) -> str | None:
    """Find the first GitHub/GitLab/Bitbucket URL in any of the given texts."""
    code_url, _ = _extract_resource_links(*texts)
    return code_url


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
