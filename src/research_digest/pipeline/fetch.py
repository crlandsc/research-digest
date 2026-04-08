"""Pipeline fetch step: orchestrate arXiv fetch and storage."""

import logging

from research_digest.config import AppConfig
from research_digest.fetchers.arxiv import compute_date_range, fetch_papers
from research_digest.storage.repository import PaperRepository

logger = logging.getLogger(__name__)


def run_fetch(
    config: AppConfig,
    repo: PaperRepository,
    run_id: str,
    since_last_run: bool = False,
    lookback_days_override: int | None = None,
) -> tuple[int, int]:
    """Execute the fetch step.

    Returns (papers_fetched, papers_new).
    """
    arxiv_cfg = config.sources.arxiv
    last_run_time = None

    if since_last_run:
        last = repo.get_last_successful_run()
        if last and last.completed_at:
            last_run_time = last.completed_at
            logger.info("Since-last-run mode: using %s", last_run_time.isoformat())
        else:
            logger.info("No previous successful run found, falling back to lookback_days")

    lookback = lookback_days_override or arxiv_cfg.lookback_days
    start_date, end_date = compute_date_range(lookback, since_last_run=last_run_time)
    logger.info("Fetch date range: %s to %s", start_date.isoformat(), end_date.isoformat())

    papers = fetch_papers(arxiv_cfg, start_date, end_date)
    total, new = repo.upsert_papers(papers)

    logger.info("Fetched %d papers (%d new)", total, new)
    return (total, new)
