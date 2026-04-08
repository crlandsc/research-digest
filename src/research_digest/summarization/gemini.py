"""Google Gemini summarization provider."""

import logging
import os
import time

import httpx

from research_digest.models import Paper
from research_digest.summarization.base import SummarizationProvider

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

_SYSTEM_PROMPT = """\
You write concise research paper summaries for a daily email digest read by \
AI/ML engineers working in music and audio. Your summaries are 2-3 sentences max. \
Lead with the key result or contribution in plain language. Mention the approach \
only if it's novel or noteworthy. Skip background context the reader already knows. \
Write in active voice. Never start with "This paper" or "The authors" or "Researchers". \
Never repeat the paper title. No jargon that isn't essential."""

_USER_TEMPLATE = """\
Title: {title}
Abstract: {abstract}

Summarize in 2-3 sentences for a newsletter."""


class GeminiProvider(SummarizationProvider):
    """Summarization via Google Gemini Flash (free tier)."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY not set. Get a free key at https://aistudio.google.com/apikey"
            )
        self._client = httpx.Client(timeout=30.0)
        logger.info("Gemini provider initialized (key: %s...)", self.api_key[:8])

    def summarize_paper(self, paper: Paper) -> str:
        prompt = _USER_TEMPLATE.format(
            title=paper.title,
            abstract=paper.abstract,
        )
        return self._call_gemini(prompt)

    def summarize_papers(self, papers: list[Paper]) -> dict[str, str]:
        logger.info("Summarizing %d papers with Gemini", len(papers))
        results: dict[str, str] = {}
        for i, paper in enumerate(papers):
            if i > 0:
                time.sleep(1)
            try:
                summary = self.summarize_paper(paper)
                results[paper.external_id] = summary
                logger.info("Gemini summary for %s (%d/%d): %s",
                            paper.external_id, i + 1, len(papers), summary[:80])
            except Exception as e:
                logger.error("Gemini failed for %s: %s", paper.external_id, e, exc_info=True)
                from research_digest.pipeline.summarize import extractive_summary
                results[paper.external_id] = extractive_summary(paper.abstract)
        return results

    def _call_gemini(self, prompt: str) -> str:
        url = f"{GEMINI_API_URL}?key={self.api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 150,
            },
        }
        logger.debug("Gemini request to %s", GEMINI_API_URL)
        response = self._client.post(url, json=payload)
        logger.debug("Gemini response: HTTP %d", response.status_code)

        if response.status_code != 200:
            logger.error("Gemini API error %d: %s", response.status_code, response.text[:300])
            response.raise_for_status()

        data = response.json()
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError) as e:
            logger.error("Unexpected Gemini response structure: %s", data)
            raise ValueError(f"Bad Gemini response: {e}") from e

        return text
