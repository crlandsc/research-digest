"""Pipeline build step: generate digest from scored papers."""

import logging
from pathlib import Path

from research_digest.config import AppConfig
from research_digest.models import DigestEntry
from research_digest.pipeline.summarize import extractive_summary
from research_digest.rendering.markdown import render_digest, write_digest
from research_digest.storage.repository import PaperRepository
from research_digest.summarization.providers import get_provider

logger = logging.getLogger(__name__)


def run_build(
    config: AppConfig,
    repo: PaperRepository,
    run_id: str,
) -> Path | None:
    """Build a Markdown digest from the top-scored papers for a run."""
    limit = config.ranking.max_candidates_for_digest
    scored = repo.get_top_scored(run_id, limit)

    if not scored:
        logger.warning("No scored papers found for run %s", run_id)

    # Generate summaries via configured provider
    provider = get_provider(config)
    papers = [sp.paper for sp in scored]
    summaries = provider.summarize_papers(papers)

    entries = [
        DigestEntry(
            paper=sp.paper,
            score=sp.score,
            rank=sp.rank,
            reason=sp.reason,
            abstract_excerpt=summaries.get(sp.paper.external_id)
            or extractive_summary(sp.paper.abstract),
        )
        for sp in scored
    ]

    total_reviewed = len(repo.get_all_papers())
    content = render_digest(entries, config, run_id, total_reviewed)
    path = write_digest(content)

    # Mark papers as included in digest
    paper_ids = []
    for sp in scored:
        pid = repo._get_paper_id(sp.paper.source, sp.paper.external_id)
        if pid is not None:
            paper_ids.append(pid)
    repo.mark_digest_included(run_id, paper_ids)

    logger.info("Built digest with %d entries at %s", len(entries), path)
    return path


def _load_entries_from_last_run(config: AppConfig) -> list[DigestEntry]:
    """Load digest entries from the most recent successful run (for email rendering)."""
    from research_digest.storage.db import get_connection

    conn = get_connection()
    repo = PaperRepository(conn)

    last = repo.get_last_successful_run()
    if not last:
        return []

    limit = config.ranking.max_candidates_for_digest
    scored = repo.get_top_scored(last.run_id, limit)

    provider = get_provider(config)
    papers = [sp.paper for sp in scored]
    summaries = provider.summarize_papers(papers)

    return [
        DigestEntry(
            paper=sp.paper,
            score=sp.score,
            rank=sp.rank,
            reason=sp.reason,
            abstract_excerpt=summaries.get(sp.paper.external_id)
            or extractive_summary(sp.paper.abstract),
        )
        for sp in scored
    ]
