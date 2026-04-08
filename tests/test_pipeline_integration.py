"""Integration tests for the full pipeline with mocked fetcher."""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from research_digest.config import AppConfig
from research_digest.models import Paper
from research_digest.pipeline import run_pipeline
from research_digest.pipeline.build_digest import run_build
from research_digest.pipeline.fetch import run_fetch
from research_digest.pipeline.rank import run_rank
from research_digest.storage.db import init_schema
from research_digest.storage.repository import PaperRepository


def _mock_papers() -> list[Paper]:
    now = datetime.now(timezone.utc)
    return [
        Paper(
            source="arxiv",
            external_id=f"2401.{i:05d}",
            title=f"Paper {i} on Music Generation" if i % 2 == 0 else f"Paper {i} on Graph Theory",
            authors=[f"Author {i}"],
            abstract=f"Abstract {i}. Music generation is discussed." if i % 2 == 0 else f"Abstract {i}.",
            categories=["cs.SD"] if i % 2 == 0 else ["math.CO"],
            published_at=now - timedelta(hours=i * 12),
            canonical_url=f"http://arxiv.org/abs/2401.{i:05d}",
            pdf_url=f"http://arxiv.org/pdf/2401.{i:05d}" if i % 2 == 0 else None,
        )
        for i in range(6)
    ]


@pytest.fixture
def _db_and_repo(tmp_path: Path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    init_schema(conn)
    repo = PaperRepository(conn)
    return conn, repo, db_path


class TestFullPipeline:
    def test_mock_fetch_rank_build(self, sample_config: AppConfig, tmp_path: Path) -> None:
        mock_papers = _mock_papers()

        with (
            patch("research_digest.pipeline.fetch.fetch_papers", return_value=mock_papers),
            patch("research_digest.storage.db.get_db_path", return_value=tmp_path / "test.db"),
            patch("research_digest.rendering.markdown.write_digest") as mock_write,
        ):
            mock_write.side_effect = lambda content, **kw: _write_to_tmp(content, tmp_path)
            path, entries = run_pipeline(sample_config)

        assert path is not None
        assert len(entries) > 0

    def test_deduplication(self, sample_config: AppConfig, _db_and_repo) -> None:
        conn, repo, _ = _db_and_repo
        mock_papers = _mock_papers()

        # First run
        repo.create_run("run-1")
        with patch("research_digest.pipeline.fetch.fetch_papers", return_value=mock_papers):
            total1, new1 = run_fetch(sample_config, repo, "run-1")

        # Second run with same papers
        repo.create_run("run-2")
        with patch("research_digest.pipeline.fetch.fetch_papers", return_value=mock_papers):
            total2, new2 = run_fetch(sample_config, repo, "run-2")

        assert new1 == 6
        assert new2 == 0  # all duplicates
        count = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        assert count == 6

    def test_since_last_run(self, sample_config: AppConfig, _db_and_repo) -> None:
        conn, repo, _ = _db_and_repo

        repo.create_run("run-1")
        with patch("research_digest.pipeline.fetch.fetch_papers", return_value=_mock_papers()):
            run_fetch(sample_config, repo, "run-1")
        repo.complete_run("run-1", status="completed", papers_fetched=6, papers_new=6)

        repo.create_run("run-2")
        with patch("research_digest.pipeline.fetch.fetch_papers", return_value=[]) as mock_fetch:
            run_fetch(sample_config, repo, "run-2", since_last_run=True)
            # Verify the fetcher was called (since-last-run resolved from DB)
            mock_fetch.assert_called_once()


    def test_topic_groups_survive_pipeline(self, tmp_path: Path) -> None:
        """Verify topic_group is correctly assigned through the full pipeline.

        This catches the bug where topic_group was computed in run_rank but lost
        when run_build loaded papers from DB (where topic_group wasn't persisted).
        """
        config = AppConfig.model_validate({
            "version": 1,
            "sources": {"arxiv": {
                "categories": ["cs.SD", "eess.AS"],
                "keyword_queries": ["music generation", "source separation", "speech synthesis"],
            }},
            "keyword_groups": {
                "Music Generation": ["music generation"],
                "Source Separation": ["source separation"],
                "Speech & Voice": ["speech synthesis"],
            },
        })

        mock_papers = [
            Paper(
                source="arxiv", external_id="gen-1",
                title="Music Generation with Diffusion",
                authors=["A"], abstract="A music generation approach.",
                categories=["cs.SD"],
                published_at=datetime.now(timezone.utc) - timedelta(hours=6),
                canonical_url="http://arxiv.org/abs/gen-1",
            ),
            Paper(
                source="arxiv", external_id="sep-1",
                title="Neural Source Separation Model",
                authors=["B"], abstract="A source separation method.",
                categories=["cs.SD"],
                published_at=datetime.now(timezone.utc) - timedelta(hours=12),
                canonical_url="http://arxiv.org/abs/sep-1",
            ),
            Paper(
                source="arxiv", external_id="tts-1",
                title="Fast Speech Synthesis via Flow Matching",
                authors=["C"], abstract="A speech synthesis system.",
                categories=["eess.AS"],
                published_at=datetime.now(timezone.utc) - timedelta(hours=18),
                canonical_url="http://arxiv.org/abs/tts-1",
            ),
        ]

        with (
            patch("research_digest.pipeline.fetch.fetch_papers", return_value=mock_papers),
            patch("research_digest.storage.db.get_db_path", return_value=tmp_path / "test.db"),
            patch("research_digest.rendering.markdown.write_digest") as mock_write,
        ):
            mock_write.side_effect = lambda content, **kw: _write_to_tmp(content, tmp_path)
            path, entries = run_pipeline(config)

        assert len(entries) == 3

        groups = {e.paper.external_id: e.topic_group for e in entries}
        assert groups["gen-1"] == "Music Generation"
        assert groups["sep-1"] == "Source Separation"
        assert groups["tts-1"] == "Speech & Voice"

        # None should be "Other"
        assert "Other" not in [e.topic_group for e in entries]

    def test_email_entries_have_topic_groups(self, tmp_path: Path) -> None:
        """Verify entries passed to email rendering have correct topic groups."""
        config = AppConfig.model_validate({
            "version": 1,
            "sources": {"arxiv": {
                "categories": ["cs.SD"],
                "keyword_queries": ["audio classification"],
            }},
            "keyword_groups": {
                "Audio Classification": ["audio classification"],
            },
        })

        mock_papers = [
            Paper(
                source="arxiv", external_id="cls-1",
                title="Audio Classification with Transformers",
                authors=["A"], abstract="An audio classification approach.",
                categories=["cs.SD"],
                published_at=datetime.now(timezone.utc),
                canonical_url="http://arxiv.org/abs/cls-1",
            ),
        ]

        with (
            patch("research_digest.pipeline.fetch.fetch_papers", return_value=mock_papers),
            patch("research_digest.storage.db.get_db_path", return_value=tmp_path / "test.db"),
            patch("research_digest.rendering.markdown.write_digest") as mock_write,
        ):
            mock_write.side_effect = lambda content, **kw: _write_to_tmp(content, tmp_path)
            path, entries = run_pipeline(config)

        # These entries are what would be passed to _send_digest_from_entries
        assert entries[0].topic_group == "Audio Classification"

    def test_digest_markdown_contains_content(self, tmp_path: Path) -> None:
        """Verify the written Markdown digest has actual paper content."""
        config = AppConfig.model_validate({
            "version": 1,
            "sources": {"arxiv": {
                "categories": ["cs.SD"],
                "keyword_queries": ["music generation"],
            }},
        })

        mock_papers = [
            Paper(
                source="arxiv", external_id="test-1",
                title="Test Paper on Music Generation",
                authors=["Alice"], abstract="A novel approach to music generation.",
                categories=["cs.SD"],
                published_at=datetime.now(timezone.utc),
                canonical_url="http://arxiv.org/abs/test-1",
                pdf_url="http://arxiv.org/pdf/test-1",
            ),
        ]

        with (
            patch("research_digest.pipeline.fetch.fetch_papers", return_value=mock_papers),
            patch("research_digest.storage.db.get_db_path", return_value=tmp_path / "test.db"),
        ):
            path, entries = run_pipeline(config)

        assert path is not None
        content = path.read_text()
        assert "Test Paper on Music Generation" in content
        assert "arxiv.org/abs/test-1" in content
        assert "arxiv.org/pdf/test-1" in content


def _write_to_tmp(content: str, tmp_path: Path) -> Path:
    out = tmp_path / "digest.md"
    out.write_text(content)
    return out
