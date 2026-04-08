"""Provider factory for summarization."""

import logging

from research_digest.config import AppConfig
from research_digest.summarization.base import SummarizationProvider

logger = logging.getLogger(__name__)


def get_provider(config: AppConfig) -> SummarizationProvider:
    """Get the configured summarization provider."""
    mode = config.summarization.mode
    provider_name = config.summarization.provider

    if mode == "llm" and provider_name == "gemini":
        from research_digest.summarization.gemini import GeminiProvider
        logger.info("Using Gemini summarization provider")
        return GeminiProvider()

    # Default to extractive
    from research_digest.summarization.extractive import ExtractiveProvider
    logger.info("Using extractive summarization (no LLM)")
    return ExtractiveProvider()
