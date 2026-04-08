"""Data access layer for papers, runs, and scores."""

import json
import logging
import sqlite3
from datetime import datetime, timezone

from research_digest.models import Paper, RunRecord, ScoredPaper

logger = logging.getLogger(__name__)


class PaperRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    # ── Paper CRUD ──────────────────────────────────────────────

    def upsert_paper(self, paper: Paper) -> int:
        """Insert or ignore (dedup by source+external_id). Returns row id."""
        cursor = self.conn.execute(
            """INSERT OR IGNORE INTO papers
               (source, external_id, title, authors, abstract, categories,
                published_at, updated_at, canonical_url, pdf_url, code_url, resource_links)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                paper.source,
                paper.external_id,
                paper.title,
                json.dumps(paper.authors),
                paper.abstract,
                json.dumps(paper.categories),
                paper.published_at.isoformat(),
                paper.updated_at.isoformat() if paper.updated_at else None,
                paper.canonical_url,
                paper.pdf_url,
                paper.code_url,
                json.dumps(paper.resource_links),
            ),
        )
        self.conn.commit()
        if cursor.rowcount > 0:
            return cursor.lastrowid  # type: ignore[return-value]
        # Already existed — look up the id
        row = self.conn.execute(
            "SELECT id FROM papers WHERE source=? AND external_id=?",
            (paper.source, paper.external_id),
        ).fetchone()
        return row["id"]

    def upsert_papers(self, papers: list[Paper]) -> tuple[int, int]:
        """Bulk upsert. Returns (total_attempted, newly_inserted)."""
        new_count = 0
        for paper in papers:
            cursor = self.conn.execute(
                """INSERT OR IGNORE INTO papers
                   (source, external_id, title, authors, abstract, categories,
                    published_at, updated_at, canonical_url, pdf_url, code_url, resource_links)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    paper.source,
                    paper.external_id,
                    paper.title,
                    json.dumps(paper.authors),
                    paper.abstract,
                    json.dumps(paper.categories),
                    paper.published_at.isoformat(),
                    paper.updated_at.isoformat() if paper.updated_at else None,
                    paper.canonical_url,
                    paper.pdf_url,
                    paper.code_url,
                    json.dumps(paper.resource_links),
                ),
            )
            if cursor.rowcount > 0:
                new_count += 1
        self.conn.commit()
        return (len(papers), new_count)

    def get_paper_by_external_id(self, source: str, external_id: str) -> Paper | None:
        row = self.conn.execute(
            "SELECT * FROM papers WHERE source=? AND external_id=?",
            (source, external_id),
        ).fetchone()
        return self._row_to_paper(row) if row else None

    def get_papers_in_date_range(self, start: datetime, end: datetime) -> list[Paper]:
        rows = self.conn.execute(
            "SELECT * FROM papers WHERE published_at >= ? AND published_at <= ? ORDER BY published_at DESC",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        return [self._row_to_paper(r) for r in rows]

    def get_all_papers(self) -> list[Paper]:
        rows = self.conn.execute("SELECT * FROM papers ORDER BY published_at DESC").fetchall()
        return [self._row_to_paper(r) for r in rows]

    # ── Run lifecycle ───────────────────────────────────────────

    def create_run(self, run_id: str) -> None:
        self.conn.execute(
            "INSERT INTO runs (run_id, started_at, status) VALUES (?, ?, ?)",
            (run_id, datetime.now(timezone.utc).isoformat(), "running"),
        )
        self.conn.commit()

    def complete_run(
        self,
        run_id: str,
        *,
        status: str,
        papers_fetched: int = 0,
        papers_new: int = 0,
        papers_ranked: int = 0,
        digest_path: str | None = None,
    ) -> None:
        self.conn.execute(
            """UPDATE runs SET completed_at=?, status=?, papers_fetched=?,
               papers_new=?, papers_ranked=?, digest_path=? WHERE run_id=?""",
            (
                datetime.now(timezone.utc).isoformat(),
                status,
                papers_fetched,
                papers_new,
                papers_ranked,
                digest_path,
                run_id,
            ),
        )
        self.conn.commit()

    def get_last_successful_run(self) -> RunRecord | None:
        row = self.conn.execute(
            "SELECT * FROM runs WHERE status='completed' ORDER BY completed_at DESC LIMIT 1"
        ).fetchone()
        return self._row_to_run(row) if row else None

    def get_most_recent_run(self) -> RunRecord | None:
        row = self.conn.execute(
            "SELECT * FROM runs ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        return self._row_to_run(row) if row else None

    # ── Scoring ─────────────────────────────────────────────────

    def save_scores(self, run_id: str, scored_papers: list[ScoredPaper]) -> None:
        for sp in scored_papers:
            paper_id = self.get_paper_id(sp.paper.source, sp.paper.external_id)
            if paper_id is None:
                continue
            self.conn.execute(
                """INSERT OR REPLACE INTO paper_scores
                   (paper_id, run_id, score, rank, reason) VALUES (?, ?, ?, ?, ?)""",
                (paper_id, run_id, sp.score, sp.rank, sp.reason),
            )
        self.conn.commit()

    def get_top_scored(self, run_id: str, limit: int) -> list[ScoredPaper]:
        rows = self.conn.execute(
            """SELECT p.*, ps.score, ps.rank, ps.reason
               FROM paper_scores ps JOIN papers p ON ps.paper_id = p.id
               WHERE ps.run_id=? ORDER BY ps.score DESC LIMIT ?""",
            (run_id, limit),
        ).fetchall()
        return [
            ScoredPaper(
                paper=self._row_to_paper(r),
                score=r["score"],
                rank=r["rank"],
                reason=r["reason"] or "",
            )
            for r in rows
        ]

    def mark_digest_included(self, run_id: str, paper_ids: list[int]) -> None:
        if not paper_ids:
            return
        placeholders = ",".join("?" for _ in paper_ids)
        self.conn.execute(
            f"UPDATE paper_scores SET included_in_digest=1 WHERE run_id=? AND paper_id IN ({placeholders})",
            [run_id, *paper_ids],
        )
        self.conn.commit()

    # ── Helpers ─────────────────────────────────────────────────

    def get_paper_id(self, source: str, external_id: str) -> int | None:
        row = self.conn.execute(
            "SELECT id FROM papers WHERE source=? AND external_id=?",
            (source, external_id),
        ).fetchone()
        return row["id"] if row else None

    @staticmethod
    def _row_to_paper(row: sqlite3.Row) -> Paper:
        return Paper(
            source=row["source"],
            external_id=row["external_id"],
            title=row["title"],
            authors=json.loads(row["authors"]),
            abstract=row["abstract"],
            categories=json.loads(row["categories"]),
            published_at=datetime.fromisoformat(row["published_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
            canonical_url=row["canonical_url"],
            pdf_url=row["pdf_url"],
            code_url=row["code_url"] if "code_url" in row.keys() else None,
            resource_links=json.loads(row["resource_links"]) if "resource_links" in row.keys() and row["resource_links"] else {},
        )

    @staticmethod
    def _row_to_run(row: sqlite3.Row) -> RunRecord:
        return RunRecord(
            run_id=row["run_id"],
            started_at=datetime.fromisoformat(row["started_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            status=row["status"],
            papers_fetched=row["papers_fetched"],
            papers_new=row["papers_new"],
            papers_ranked=row["papers_ranked"],
            digest_path=row["digest_path"],
        )
