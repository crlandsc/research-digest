"""Full pipeline orchestration: fetch -> rank -> build."""

import logging
from pathlib import Path
from uuid import uuid4

from research_digest.config import AppConfig
from research_digest.pipeline.build_digest import run_build
from research_digest.pipeline.fetch import run_fetch
from research_digest.pipeline.rank import run_rank
from research_digest.storage.db import get_connection
from research_digest.storage.repository import PaperRepository

logger = logging.getLogger(__name__)


def run_pipeline(
    config: AppConfig,
    since_last_run: bool = False,
    lookback_days_override: int | None = None,
    dry_run: bool = False,
) -> Path | None:
    """Execute the full pipeline: fetch, rank, build digest."""
    conn = get_connection()
    repo = PaperRepository(conn)
    run_id = str(uuid4())

    if dry_run:
        from research_digest.fetchers.arxiv import build_query, compute_date_range

        lb = lookback_days_override or config.sources.arxiv.lookback_days
        start, end = compute_date_range(lb)
        query = build_query(config.sources.arxiv, start, end)
        logger.info("Dry run — query: %s", query)
        return None

    repo.create_run(run_id)
    try:
        total, new = run_fetch(config, repo, run_id, since_last_run, lookback_days_override)
        scored = run_rank(config, repo, run_id)
        digest_path = run_build(config, repo, run_id)

        repo.complete_run(
            run_id,
            status="completed",
            papers_fetched=total,
            papers_new=new,
            papers_ranked=len(scored),
            digest_path=str(digest_path) if digest_path else None,
        )
        return digest_path

    except Exception:
        repo.complete_run(run_id, status="failed")
        raise
