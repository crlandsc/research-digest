"""Extractive summarization provider (no LLM, local only)."""

from research_digest.models import Paper
from research_digest.pipeline.summarize import extractive_summary
from research_digest.summarization.base import SummarizationProvider


class ExtractiveProvider(SummarizationProvider):
    """Fallback provider using first N sentences of abstract."""

    def summarize_paper(self, paper: Paper) -> str:
        return extractive_summary(paper.abstract)
