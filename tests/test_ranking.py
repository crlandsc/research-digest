"""Tests for filtering, scoring, and ranking."""

from datetime import datetime, timedelta, timezone

import pytest

from research_digest.config import AppConfig, FiltersConfig
from research_digest.models import Paper
from research_digest.pipeline.rank import apply_filters, score_paper


def _paper(**kwargs) -> Paper:
    defaults = dict(
        source="arxiv",
        external_id="2401.00001",
        title="Test Paper Title",
        authors=["Alice"],
        abstract="Test abstract content.",
        categories=["cs.SD"],
        published_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
        canonical_url="http://arxiv.org/abs/2401.00001",
    )
    defaults.update(kwargs)
    return Paper(**defaults)


class TestScoring:
    def test_category_match_single(self, sample_config: AppConfig) -> None:
        paper = _paper(categories=["cs.SD"])
        score, reason, _ = score_paper(paper, sample_config)
        assert score >= 10
        assert "category:cs.SD(+10)" in reason

    def test_category_match_multiple(self, sample_config: AppConfig) -> None:
        paper = _paper(categories=["cs.SD", "eess.AS"])
        score, _, _ = score_paper(paper, sample_config)
        assert score >= 20  # +10 per matching category

    def test_keyword_in_title(self, sample_config: AppConfig) -> None:
        paper = _paper(title="Music Generation with Transformers")
        score, reason, _ = score_paper(paper, sample_config)
        assert score >= 15
        assert "title(+15)" in reason

    def test_keyword_in_abstract(self, sample_config: AppConfig) -> None:
        paper = _paper(
            title="A New Method",
            abstract="We study music generation approaches.",
        )
        score, reason, _ = score_paper(paper, sample_config)
        assert score >= 5
        assert "abstract(+5)" in reason

    def test_keyword_in_both(self, sample_config: AppConfig) -> None:
        paper = _paper(
            title="Music Generation Models",
            abstract="This paper on music generation presents...",
        )
        score, _, _ = score_paper(paper, sample_config)
        # +15 title + +5 abstract = +20 for this keyword alone
        assert score >= 20

    def test_recency_within_24h(self, sample_config: AppConfig) -> None:
        paper = _paper(published_at=datetime.now(timezone.utc) - timedelta(hours=12))
        score, reason, _ = score_paper(paper, sample_config)
        assert "recent:24h(+10)" in reason

    def test_recency_within_72h(self, sample_config: AppConfig) -> None:
        paper = _paper(published_at=datetime.now(timezone.utc) - timedelta(hours=48))
        score, reason, _ = score_paper(paper, sample_config)
        assert "recent:72h(+5)" in reason

    def test_recency_old(self, sample_config: AppConfig) -> None:
        paper = _paper(published_at=datetime.now(timezone.utc) - timedelta(days=7))
        _, reason, _ = score_paper(paper, sample_config)
        assert "recent" not in reason

    def test_recency_disabled(self, sample_config: AppConfig) -> None:
        sample_config.ranking.prioritize_recency = False
        paper = _paper(published_at=datetime.now(timezone.utc) - timedelta(hours=12))
        _, reason, _ = score_paper(paper, sample_config)
        assert "recent" not in reason

    def test_no_matches(self, sample_config: AppConfig) -> None:
        paper = _paper(
            categories=["math.CO"],
            title="Graph Theory Result",
            abstract="Pure mathematics content.",
            published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        score, _, _ = score_paper(paper, sample_config)
        assert score == 0.0

    def test_multiple_signals_cumulative(self, sample_config: AppConfig) -> None:
        paper = _paper(
            categories=["cs.SD"],
            title="Source Separation with Diffusion",
            abstract="We propose a source separation method.",
            published_at=datetime.now(timezone.utc) - timedelta(hours=6),
        )
        score, _, _ = score_paper(paper, sample_config)
        # +10 category + +15 title kw + +5 abstract kw + +10 recency = 40+
        assert score >= 40

    def test_required_keyword_bonus(self) -> None:
        cfg = AppConfig()
        cfg.filters.required_keywords = ["diffusion"]
        paper = _paper(abstract="We use diffusion models.")
        score, reason, _ = score_paper(paper, cfg)
        assert score >= 20
        assert "required:'diffusion'(+20)" in reason

    def test_author_penalty(self, sample_config: AppConfig) -> None:
        sample_config.filters.max_authors = 2
        paper = _paper(authors=["A", "B", "C"])
        score, reason, _ = score_paper(paper, sample_config)
        assert "(-5)" in reason


class TestFiltering:
    def test_excludes_survey(self) -> None:
        papers = [_paper(title="A Survey of Audio Methods"), _paper(external_id="keep", title="Audio Model")]
        result = apply_filters(papers, FiltersConfig(excluded_keywords=["survey"]))
        assert len(result) == 1
        assert result[0].external_id == "keep"

    def test_excludes_case_insensitive(self) -> None:
        papers = [_paper(title="A SURVEY of Methods")]
        result = apply_filters(papers, FiltersConfig(excluded_keywords=["survey"]))
        assert len(result) == 0

    def test_required_present(self) -> None:
        papers = [_paper(abstract="Uses diffusion models.")]
        result = apply_filters(papers, FiltersConfig(required_keywords=["diffusion"]))
        assert len(result) == 1

    def test_required_absent(self) -> None:
        papers = [_paper(abstract="Uses GAN models.")]
        result = apply_filters(papers, FiltersConfig(required_keywords=["diffusion"]))
        assert len(result) == 0

    def test_required_empty_means_no_filter(self) -> None:
        papers = [_paper()]
        result = apply_filters(papers, FiltersConfig(required_keywords=[]))
        assert len(result) == 1

    def test_max_authors(self) -> None:
        papers = [_paper(authors=["A", "B", "C"])]
        result = apply_filters(papers, FiltersConfig(max_authors=2))
        assert len(result) == 0


class TestRanking:
    def test_ordering(self, sample_config: AppConfig) -> None:
        from research_digest.pipeline.rank import run_rank
        import sqlite3
        from research_digest.storage.db import init_schema
        from research_digest.storage.repository import PaperRepository

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        init_schema(conn)
        repo = PaperRepository(conn)

        high = _paper(external_id="high", categories=["cs.SD"], title="Music Generation Model")
        low = _paper(external_id="low", categories=["math.CO"], title="Graph Theory")
        repo.upsert_paper(high)
        repo.upsert_paper(low)
        repo.create_run("test-run")

        result = run_rank(sample_config, repo, "test-run")
        assert result[0].paper.external_id == "high"
        assert result[0].rank == 1

    def test_respects_max_candidates(self, sample_config: AppConfig) -> None:
        import sqlite3
        from research_digest.pipeline.rank import run_rank
        from research_digest.storage.db import init_schema
        from research_digest.storage.repository import PaperRepository

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        init_schema(conn)
        repo = PaperRepository(conn)

        for i in range(15):
            repo.upsert_paper(_paper(external_id=f"p-{i}"))
        repo.create_run("test-run")

        sample_config.ranking.max_candidates_for_digest = 5
        result = run_rank(sample_config, repo, "test-run")
        assert len(result) == 5

    def test_reason_contains_signals(self, sample_config: AppConfig) -> None:
        paper = _paper(categories=["cs.SD"], title="Source Separation")
        _, reason, _ = score_paper(paper, sample_config)
        assert "→" in reason
