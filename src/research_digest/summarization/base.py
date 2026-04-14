"""Base summarization provider interface."""

from abc import ABC, abstractmethod

from research_digest.models import Paper, SummaryResult


class SummarizationProvider(ABC):
    """Abstract base for LLM summarization providers."""

    @abstractmethod
    def summarize_paper(self, paper: Paper) -> SummaryResult:
        """Generate a concise newsletter-style summary for a single paper."""

    def summarize_papers(self, papers: list[Paper]) -> dict[str, SummaryResult]:
        """Summarize multiple papers. Returns {external_id: SummaryResult}.

        Default implementation calls summarize_paper() sequentially.
        Providers can override for batch efficiency.
        """
        return {p.external_id: self.summarize_paper(p) for p in papers}
