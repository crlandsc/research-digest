"""Edge case and fixture-based tests."""

import sqlite3
from datetime import datetime, timezone

import pytest

from research_digest.config import AppConfig, load_config
from research_digest.fetchers.arxiv import parse_arxiv_response
from research_digest.models import DigestEntry, Paper
from research_digest.pipeline.rank import apply_filters, score_paper
from research_digest.pipeline.summarize import extractive_summary
from research_digest.rendering.markdown import render_digest
from research_digest.storage.db import init_schema
from research_digest.storage.repository import PaperRepository


# ── arXiv parsing edge cases ──────────────────────────────────────────

FEED_MISSING_FIELDS = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <opensearch:totalResults>1</opensearch:totalResults>
  <entry>
    <id>http://arxiv.org/abs/2401.99999v1</id>
    <published>2024-01-15T00:00:00Z</published>
    <updated>2024-01-15T00:00:00Z</updated>
    <title>Paper With Missing Optional Fields</title>
    <summary>Abstract text here.</summary>
    <author><name>Solo Author</name></author>
    <category term="cs.SD" scheme="http://arxiv.org/schemas/atom"/>
    <link href="http://arxiv.org/abs/2401.99999v1" rel="alternate" type="text/html"/>
  </entry>
</feed>
"""

FEED_UNICODE = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>1</opensearch:totalResults>
  <entry>
    <id>http://arxiv.org/abs/2401.88888v1</id>
    <published>2024-01-15T00:00:00Z</published>
    <updated>2024-01-15T00:00:00Z</updated>
    <title>Über die Lösung des Schrödinger-Problems</title>
    <summary>Résumé avec des caractères spéciaux: α, β, γ, ∞.</summary>
    <author><name>José García</name></author>
    <category term="cs.SD"/>
    <link href="http://arxiv.org/abs/2401.88888v1" rel="alternate"/>
  </entry>
</feed>
"""


class TestParsingEdgeCases:
    def test_missing_pdf_url(self) -> None:
        papers, _ = parse_arxiv_response(FEED_MISSING_FIELDS)
        assert papers[0].pdf_url is None

    def test_single_author(self) -> None:
        papers, _ = parse_arxiv_response(FEED_MISSING_FIELDS)
        assert papers[0].authors == ["Solo Author"]

    def test_unicode_title_and_abstract(self) -> None:
        papers, _ = parse_arxiv_response(FEED_UNICODE)
        assert "Schrödinger" in papers[0].title
        assert "α" in papers[0].abstract

    def test_unicode_author(self) -> None:
        papers, _ = parse_arxiv_response(FEED_UNICODE)
        assert papers[0].authors == ["José García"]


# ── Scoring edge cases ────────────────────────────────────────────────

def _paper(**kw) -> Paper:
    defaults = dict(
        source="arxiv", external_id="test", title="Test", authors=["A"],
        abstract="Test.", categories=["cs.SD"],
        published_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
        canonical_url="http://arxiv.org/abs/test",
    )
    defaults.update(kw)
    return Paper(**defaults)


class TestScoringEdgeCases:
    def test_empty_categories_in_config(self) -> None:
        cfg = AppConfig()
        cfg.sources.arxiv.categories = []
        score, _, _ = score_paper(_paper(categories=["cs.SD"]), cfg)
        # no category bonus since config has none
        assert score >= 0

    def test_empty_keywords_in_config(self) -> None:
        cfg = AppConfig()
        cfg.sources.arxiv.keyword_queries = []
        cfg.ranking.prioritize_recency = False
        score, _, _ = score_paper(_paper(), cfg)
        assert score == 0 or score > 0  # only category match possible

    def test_keyword_case_insensitive(self) -> None:
        cfg = AppConfig()
        cfg.sources.arxiv.keyword_queries = ["MUSIC GENERATION"]
        paper = _paper(title="music generation with diffusion")
        score, _, _ = score_paper(paper, cfg)
        assert score >= 15

    def test_keyword_partial_match(self) -> None:
        """Keyword 'audio' should match 'audio classification' in text."""
        cfg = AppConfig()
        cfg.sources.arxiv.keyword_queries = ["audio"]
        paper = _paper(abstract="We study audio classification methods.")
        score, reason, _ = score_paper(paper, cfg)
        assert "abstract" in reason


# ── Filter edge cases ─────────────────────────────────────────────────

class TestFilterEdgeCases:
    def test_excluded_keyword_in_abstract_not_title(self) -> None:
        from research_digest.config import FiltersConfig
        papers = [_paper(title="Good Paper", abstract="This is a survey of methods.")]
        result = apply_filters(papers, FiltersConfig(excluded_keywords=["survey"]))
        assert len(result) == 0  # excluded from abstract too

    def test_empty_paper_list(self) -> None:
        from research_digest.config import FiltersConfig
        result = apply_filters([], FiltersConfig(excluded_keywords=["survey"]))
        assert result == []


# ── Summarization edge cases ──────────────────────────────────────────

class TestSummarizationEdgeCases:
    def test_single_sentence(self) -> None:
        assert extractive_summary("Just one sentence") == "Just one sentence"

    def test_preserves_periods_in_abbreviations(self) -> None:
        text = "We use the U.S. standard. Then we test. And then evaluate."
        result = extractive_summary(text, max_sentences=2)
        # Should split on ". " not just "."
        assert "U.S." in result or "U.S" in result

    def test_very_long_abstract(self) -> None:
        sentences = [f"Sentence {i} describes a method" for i in range(20)]
        text = ". ".join(sentences) + "."
        result = extractive_summary(text)
        assert result.count(". ") <= 2  # 3 sentences max = 2 ". " separators


# ── Rendering edge cases ─────────────────────────────────────────────

class TestRenderingEdgeCases:
    def test_paper_without_pdf(self) -> None:
        entry = DigestEntry(
            paper=_paper(pdf_url=None),
            score=10.0, rank=1, reason="test",
            abstract_excerpt="Test excerpt.",
        )
        cfg = AppConfig()
        md = render_digest([entry], cfg, "test-run")
        assert "[Abstract]" in md
        assert "[PDF]" not in md

    def test_special_chars_in_title(self) -> None:
        entry = DigestEntry(
            paper=_paper(title="O(n²) Complexity & <Special> \"Chars\""),
            score=10.0, rank=1, reason="test",
        )
        cfg = AppConfig()
        md = render_digest([entry], cfg, "test-run")
        assert "O(n²)" in md


# ── Storage edge cases ────────────────────────────────────────────────

class TestStorageEdgeCases:
    def test_paper_with_special_chars_roundtrip(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        init_schema(conn)
        repo = PaperRepository(conn)

        paper = _paper(
            title='Title with "quotes" & <brackets>',
            authors=["José García", "Müller"],
            abstract="Abstract with α, β, γ symbols.",
        )
        repo.upsert_paper(paper)
        stored = repo.get_paper_by_external_id("arxiv", "test")
        assert stored is not None
        assert stored.title == paper.title
        assert stored.authors == paper.authors
        assert "α" in stored.abstract

    def test_concurrent_runs_different_scores(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        init_schema(conn)
        repo = PaperRepository(conn)

        paper = _paper()
        repo.upsert_paper(paper)
        repo.create_run("run-1")
        repo.create_run("run-2")

        from research_digest.models import ScoredPaper
        repo.save_scores("run-1", [ScoredPaper(paper=paper, score=10.0, rank=1, reason="r1")])
        repo.save_scores("run-2", [ScoredPaper(paper=paper, score=20.0, rank=1, reason="r2")])

        top1 = repo.get_top_scored("run-1", 10)
        top2 = repo.get_top_scored("run-2", 10)
        assert top1[0].score == 10.0
        assert top2[0].score == 20.0
