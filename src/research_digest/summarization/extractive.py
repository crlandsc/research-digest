"""Extractive summarization provider (no LLM, local only)."""

from research_digest.models import Paper, SummaryResult
from research_digest.pipeline.summarize import extractive_summary
from research_digest.summarization.base import SummarizationProvider


class ExtractiveProvider(SummarizationProvider):
    """Fallback provider using first N sentences of abstract."""

    def summarize_paper(self, paper: Paper) -> SummaryResult:
        return SummaryResult(
            text=extractive_summary(paper.abstract),
            source="extractive",
        )
