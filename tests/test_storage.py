"""Tests for SQLite storage layer."""

import sqlite3
from datetime import datetime, timezone

import pytest

from research_digest.models import Paper, ScoredPaper
from research_digest.storage.db import init_schema
from research_digest.storage.repository import PaperRepository


@pytest.fixture
def db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    init_schema(conn)
    return conn


@pytest.fixture
def repo(db: sqlite3.Connection) -> PaperRepository:
    return PaperRepository(db)


def _make_paper(eid: str = "2401.12345", **kwargs) -> Paper:
    defaults = dict(
        source="arxiv",
        external_id=eid,
        title="Test Paper",
        authors=["Alice"],
        abstract="Test abstract.",
        categories=["cs.SD"],
        published_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
        canonical_url=f"http://arxiv.org/abs/{eid}",
    )
    defaults.update(kwargs)
    return Paper(**defaults)


class TestSchema:
    def test_creates_tables(self, db: sqlite3.Connection) -> None:
        tables = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert {"papers", "runs", "paper_scores"} <= tables


class TestPaperCRUD:
    def test_upsert_new(self, repo: PaperRepository) -> None:
        paper = _make_paper()
        pid = repo.upsert_paper(paper)
        assert pid > 0
        stored = repo.get_paper_by_external_id("arxiv", "2401.12345")
        assert stored is not None
        assert stored.title == "Test Paper"
        assert stored.authors == ["Alice"]

    def test_upsert_duplicate(self, repo: PaperRepository) -> None:
        paper = _make_paper()
        repo.upsert_paper(paper)
        repo.upsert_paper(paper)
        count = repo.conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        assert count == 1

    def test_upsert_bulk(self, repo: PaperRepository) -> None:
        papers = [_make_paper(f"id-{i}") for i in range(5)]
        papers.append(_make_paper("id-0"))  # duplicate
        papers.append(_make_paper("id-1"))  # duplicate
        total, new = repo.upsert_papers(papers)
        assert total == 7
        assert new == 5

    def test_get_by_external_id_not_found(self, repo: PaperRepository) -> None:
        assert repo.get_paper_by_external_id("arxiv", "nonexistent") is None

    def test_get_papers_in_date_range(self, repo: PaperRepository) -> None:
        repo.upsert_paper(_make_paper("a", published_at=datetime(2024, 1, 10, tzinfo=timezone.utc)))
        repo.upsert_paper(_make_paper("b", published_at=datetime(2024, 1, 15, tzinfo=timezone.utc)))
        repo.upsert_paper(_make_paper("c", published_at=datetime(2024, 1, 20, tzinfo=timezone.utc)))
        results = repo.get_papers_in_date_range(
            datetime(2024, 1, 12, tzinfo=timezone.utc),
            datetime(2024, 1, 18, tzinfo=timezone.utc),
        )
        assert len(results) == 1
        assert results[0].external_id == "b"


class TestRuns:
    def test_create_and_complete(self, repo: PaperRepository) -> None:
        repo.create_run("run-1")
        repo.complete_run("run-1", status="completed", papers_fetched=10, papers_new=8)
        run = repo.get_most_recent_run()
        assert run is not None
        assert run.status == "completed"
        assert run.papers_fetched == 10
        assert run.papers_new == 8

    def test_get_last_successful_run(self, repo: PaperRepository) -> None:
        repo.create_run("run-1")
        repo.complete_run("run-1", status="completed", papers_fetched=5)
        repo.create_run("run-2")
        repo.complete_run("run-2", status="failed")
        run = repo.get_last_successful_run()
        assert run is not None
        assert run.run_id == "run-1"

    def test_get_most_recent_run(self, repo: PaperRepository) -> None:
        repo.create_run("run-1")
        repo.complete_run("run-1", status="completed")
        repo.create_run("run-2")
        run = repo.get_most_recent_run()
        assert run is not None
        assert run.run_id == "run-2"

    def test_no_runs(self, repo: PaperRepository) -> None:
        assert repo.get_last_successful_run() is None
        assert repo.get_most_recent_run() is None


class TestScoring:
    def test_save_and_get_top_scored(self, repo: PaperRepository) -> None:
        papers = [_make_paper(f"p-{i}") for i in range(5)]
        for p in papers:
            repo.upsert_paper(p)
        repo.create_run("run-1")

        scored = [
            ScoredPaper(paper=papers[i], score=float(i * 10), rank=5 - i, reason=f"score {i}")
            for i in range(5)
        ]
        repo.save_scores("run-1", scored)

        top3 = repo.get_top_scored("run-1", limit=3)
        assert len(top3) == 3
        assert top3[0].score == 40.0
        assert top3[0].paper.external_id == "p-4"

    def test_mark_digest_included(self, repo: PaperRepository) -> None:
        paper = _make_paper()
        pid = repo.upsert_paper(paper)
        repo.create_run("run-1")
        repo.save_scores("run-1", [ScoredPaper(paper=paper, score=10.0, rank=1, reason="test")])
        repo.mark_digest_included("run-1", [pid])
        row = repo.conn.execute(
            "SELECT included_in_digest FROM paper_scores WHERE run_id='run-1'"
        ).fetchone()
        assert row[0] == 1
