"""Base summarization provider interface."""

from abc import ABC, abstractmethod

from research_digest.models import Paper


class SummarizationProvider(ABC):
    """Abstract base for LLM summarization providers."""

    @abstractmethod
    def summarize_paper(self, paper: Paper) -> str:
        """Generate a concise newsletter-style summary for a single paper."""

    def summarize_papers(self, papers: list[Paper]) -> dict[str, str]:
        """Summarize multiple papers. Returns {external_id: summary}.

        Default implementation calls summarize_paper() sequentially.
        Providers can override for batch efficiency.
        """
        return {p.external_id: self.summarize_paper(p) for p in papers}
