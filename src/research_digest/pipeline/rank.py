"""Filtering, scoring, and ranking of papers."""

import logging
from datetime import datetime, timedelta, timezone

from research_digest.config import AppConfig, FiltersConfig
from research_digest.models import Paper, ScoredPaper
from research_digest.storage.repository import PaperRepository

logger = logging.getLogger(__name__)


def run_rank(
    config: AppConfig,
    repo: PaperRepository,
    run_id: str,
) -> list[ScoredPaper]:
    """Execute the rank step: filter, score, sort, save."""
    papers = repo.get_all_papers()
    logger.info("Ranking %d candidate papers", len(papers))

    filtered = apply_filters(papers, config.filters)
    logger.info("%d papers after filtering (%d removed)", len(filtered), len(papers) - len(filtered))

    scored: list[tuple[float, str, Paper]] = []
    for paper in filtered:
        score, reason = score_paper(paper, config)
        scored.append((score, reason, paper))

    scored.sort(key=lambda x: x[0], reverse=True)

    limit = config.ranking.max_candidates_for_digest
    top = scored[:limit]

    result = [
        ScoredPaper(paper=paper, score=score, rank=i + 1, reason=reason)
        for i, (score, reason, paper) in enumerate(top)
    ]

    repo.save_scores(run_id, result)
    logger.info("Ranked %d papers, top score: %.1f", len(result), result[0].score if result else 0)
    return result


def apply_filters(papers: list[Paper], filters: FiltersConfig) -> list[Paper]:
    """Apply exclusion/inclusion filters."""
    result = papers

    if filters.excluded_keywords:
        result = [
            p for p in result
            if not _any_keyword_in_text(filters.excluded_keywords, p.title, p.abstract)
        ]

    if filters.required_keywords:
        result = [
            p for p in result
            if _any_keyword_in_text(filters.required_keywords, p.title, p.abstract)
        ]

    if filters.max_authors is not None:
        result = [p for p in result if len(p.authors) <= filters.max_authors]

    return result


def score_paper(paper: Paper, config: AppConfig) -> tuple[float, str]:
    """Deterministic scoring. Returns (score, reason_string)."""
    score = 0.0
    reasons: list[str] = []

    # Category matches (+10 each)
    cfg_cats = set(config.sources.arxiv.categories)
    for cat in paper.categories:
        if cat in cfg_cats:
            score += 10
            reasons.append(f"category:{cat}(+10)")

    # Keyword matches in title (+15) and abstract (+5)
    if config.ranking.prioritize_keyword_matches:
        title_lower = paper.title.lower()
        abstract_lower = paper.abstract.lower()
        for kw in config.sources.arxiv.keyword_queries:
            kw_lower = kw.lower()
            if kw_lower in title_lower:
                score += 15
                reasons.append(f"keyword:'{kw}' in title(+15)")
            if kw_lower in abstract_lower:
                score += 5
                reasons.append(f"keyword:'{kw}' in abstract(+5)")

    # Required keyword bonus (+20 each)
    for kw in config.filters.required_keywords:
        kw_lower = kw.lower()
        if kw_lower in paper.title.lower() or kw_lower in paper.abstract.lower():
            score += 20
            reasons.append(f"required:'{kw}'(+20)")

    # Recency bonus
    if config.ranking.prioritize_recency:
        now = datetime.now(timezone.utc)
        age = now - paper.published_at
        if age < timedelta(hours=24):
            score += 10
            reasons.append("recent:24h(+10)")
        elif age < timedelta(hours=72):
            score += 5
            reasons.append("recent:72h(+5)")

    # Author count penalty
    if config.filters.max_authors and len(paper.authors) > config.filters.max_authors:
        score -= 5
        reasons.append(f"authors:{len(paper.authors)}(-5)")

    reason_str = ", ".join(reasons) + f" \u2192 {score:.1f}" if reasons else "no matching signals \u2192 0.0"
    return (score, reason_str)


def _any_keyword_in_text(keywords: list[str], *texts: str) -> bool:
    """Check if any keyword appears in any of the text fields (case-insensitive)."""
    combined = " ".join(texts).lower()
    return any(kw.lower() in combined for kw in keywords)
