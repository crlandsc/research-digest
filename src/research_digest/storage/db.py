"""SQLite database connection and schema management."""

import logging
import os
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS papers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT NOT NULL,
    external_id     TEXT NOT NULL,
    title           TEXT NOT NULL,
    authors         TEXT NOT NULL,
    abstract        TEXT NOT NULL,
    categories      TEXT NOT NULL,
    published_at    TEXT NOT NULL,
    updated_at      TEXT,
    canonical_url   TEXT NOT NULL,
    pdf_url         TEXT,
    code_url        TEXT,
    resource_links  TEXT NOT NULL DEFAULT '{}',
    first_seen      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(source, external_id)
);

CREATE TABLE IF NOT EXISTS runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL UNIQUE,
    started_at      TEXT NOT NULL,
    completed_at    TEXT,
    status          TEXT NOT NULL DEFAULT 'running',
    papers_fetched  INTEGER NOT NULL DEFAULT 0,
    papers_new      INTEGER NOT NULL DEFAULT 0,
    papers_ranked   INTEGER NOT NULL DEFAULT 0,
    digest_path     TEXT
);

CREATE TABLE IF NOT EXISTS paper_scores (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id            INTEGER NOT NULL REFERENCES papers(id),
    run_id              TEXT NOT NULL REFERENCES runs(run_id),
    score               REAL NOT NULL,
    rank                INTEGER,
    reason              TEXT,
    included_in_digest  INTEGER NOT NULL DEFAULT 0,
    scored_at           TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(paper_id, run_id)
);

CREATE INDEX IF NOT EXISTS idx_papers_source_eid ON papers(source, external_id);
CREATE INDEX IF NOT EXISTS idx_papers_published ON papers(published_at);
CREATE INDEX IF NOT EXISTS idx_scores_run ON paper_scores(run_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
"""


def get_db_path() -> Path:
    """Return DB path from DATABASE_URL env or default."""
    env = os.environ.get("DATABASE_URL", "")
    if env.startswith("sqlite:///"):
        return Path(env.removeprefix("sqlite:///"))
    return Path("data/research_digest.db")


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Open a connection with WAL mode and foreign keys. Auto-inits schema."""
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.debug("Opening database at %s", path)
    conn = sqlite3.connect(str(path), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    init_schema(conn)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create tables and indexes if they don't exist."""
    conn.executescript(_SCHEMA)
