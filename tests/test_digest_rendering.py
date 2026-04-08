"""Tests for Markdown digest rendering."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from research_digest.config import AppConfig
from research_digest.models import DigestEntry, Paper
from research_digest.pipeline.summarize import extractive_summary
from research_digest.rendering.markdown import render_digest, write_digest


def _entry(rank: int = 1, **kwargs) -> DigestEntry:
    paper_defaults = dict(
        source="arxiv",
        external_id=f"2401.{rank:05d}",
        title=f"Test Paper {rank}",
        authors=["Alice", "Bob"],
        abstract="First sentence. Second sentence. Third sentence. Fourth sentence.",
        categories=["cs.SD"],
        published_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
        canonical_url=f"http://arxiv.org/abs/2401.{rank:05d}",
        pdf_url=f"http://arxiv.org/pdf/2401.{rank:05d}",
    )
    paper_defaults.update(kwargs.pop("paper_overrides", {}))
    defaults = dict(
        paper=Paper(**paper_defaults),
        score=50.0 - rank * 10,
        rank=rank,
        reason=f"category:cs.SD(+10), keyword in title(+15) → {50.0 - rank * 10:.1f}",
        abstract_excerpt="First sentence. Second sentence. Third sentence.",
    )
    defaults.update(kwargs)
    return DigestEntry(**defaults)


class TestRenderDigest:
    def test_basic(self, sample_config: AppConfig) -> None:
        entries = [_entry(1), _entry(2), _entry(3)]
        md = render_digest(entries, sample_config, "abc12345", total_reviewed=20)
        assert "Test Digest" in md
        assert "Test Paper 1" in md
        assert "Test Paper 2" in md
        assert "Papers reviewed: 20" in md

    def test_empty_digest(self, sample_config: AppConfig) -> None:
        md = render_digest([], sample_config, "abc12345")
        assert "No papers matched" in md

    def test_includes_abstract_excerpt(self, sample_config: AppConfig) -> None:
        entries = [_entry(1)]
        md = render_digest(entries, sample_config, "abc12345")
        assert "First sentence" in md

    def test_includes_reason(self, sample_config: AppConfig) -> None:
        entries = [_entry(1)]
        md = render_digest(entries, sample_config, "abc12345")
        assert "Selected because:" in md

    def test_includes_links(self, sample_config: AppConfig) -> None:
        entries = [_entry(1)]
        md = render_digest(entries, sample_config, "abc12345")
        assert "[Abstract]" in md
        assert "[PDF]" in md

    def test_excludes_links_when_disabled(self, sample_config: AppConfig) -> None:
        sample_config.digest.include_links = False
        entries = [_entry(1)]
        md = render_digest(entries, sample_config, "abc12345")
        assert "[Abstract]" not in md


class TestWriteDigest:
    def test_creates_dated_directory(self, tmp_path: Path) -> None:
        path = write_digest("# Test", output_dir=str(tmp_path), date_str="2024-01-15")
        assert path.exists()
        assert "2024-01-15" in str(path)

    def test_file_contents(self, tmp_path: Path) -> None:
        content = "# My Digest\n\nSome content."
        path = write_digest(content, output_dir=str(tmp_path), date_str="2024-01-15")
        assert path.read_text() == content


class TestExtractiveSummary:
    def test_3_sentences(self) -> None:
        text = "First. Second. Third. Fourth. Fifth."
        result = extractive_summary(text, max_sentences=3)
        assert result == "First. Second. Third."

    def test_short_abstract(self) -> None:
        text = "Only two sentences. Here they are."
        result = extractive_summary(text, max_sentences=3)
        assert result == text

    def test_empty(self) -> None:
        assert extractive_summary("") == ""
