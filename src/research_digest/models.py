"""Core data models for the research-digest pipeline."""

from datetime import datetime

from pydantic import BaseModel


class Paper(BaseModel):
    """Normalized paper metadata from any source."""

    source: str
    external_id: str
    title: str
    authors: list[str]
    abstract: str
    categories: list[str]
    published_at: datetime
    updated_at: datetime | None = None
    canonical_url: str
    pdf_url: str | None = None
    code_url: str | None = None
    resource_links: dict[str, str] = {}  # label -> URL (e.g., "Model": "https://huggingface.co/...")


class ScoredPaper(BaseModel):
    """Paper with scoring results from the ranking step."""

    paper: Paper
    score: float
    rank: int
    reason: str
    topic_group: str = "Other"


class RunRecord(BaseModel):
    """Pipeline execution record."""

    run_id: str
    started_at: datetime
    completed_at: datetime | None = None
    status: str = "running"
    papers_fetched: int = 0
    papers_new: int = 0
    papers_ranked: int = 0
    digest_path: str | None = None


class SummaryResult(BaseModel):
    """Result of a summarization attempt."""

    text: str
    source: str  # model name (e.g. "gemini-3-flash-preview") or "extractive"


class DigestEntry(BaseModel):
    """Paper prepared for digest rendering."""

    paper: Paper
    score: float
    rank: int
    reason: str
    abstract_excerpt: str | None = None
    summary_source: str | None = None  # which model/method produced the summary
    topic_group: str = "Other"
