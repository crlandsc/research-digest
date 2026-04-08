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
            path = run_pipeline(sample_config)

        assert path is not None

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


def _write_to_tmp(content: str, tmp_path: Path) -> Path:
    out = tmp_path / "digest.md"
    out.write_text(content)
    return out
