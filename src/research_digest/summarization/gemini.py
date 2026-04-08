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
You are a research digest editor writing concise newsletter blurbs for an audience of \
AI/ML researchers and engineers focused on music and audio. \
For each paper, write a 2-3 sentence summary in the style of the TLDR newsletter: \
lead with the key contribution or finding, mention the method briefly, \
and note why it matters. Be direct and informative, not promotional. \
Do not start with "This paper" or "The authors". \
Do not include the paper title in the summary."""

_USER_TEMPLATE = """\
Paper title: {title}
Authors: {authors}
Categories: {categories}
Abstract: {abstract}

Write a 2-3 sentence newsletter-style summary."""


class GeminiProvider(SummarizationProvider):
    """Summarization via Google Gemini Flash (free tier)."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY not set. Get a free key at https://aistudio.google.com/apikey"
            )
        self._client = httpx.Client(timeout=30.0)

    def summarize_paper(self, paper: Paper) -> str:
        prompt = _USER_TEMPLATE.format(
            title=paper.title,
            authors=", ".join(paper.authors),
            categories=", ".join(paper.categories),
            abstract=paper.abstract,
        )
        return self._call_gemini(prompt)

    def summarize_papers(self, papers: list[Paper]) -> dict[str, str]:
        results: dict[str, str] = {}
        for i, paper in enumerate(papers):
            if i > 0:
                time.sleep(1)  # rate limit courtesy
            try:
                results[paper.external_id] = self.summarize_paper(paper)
            except Exception:
                logger.warning("Failed to summarize %s, using extractive fallback", paper.external_id, exc_info=True)
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
                "maxOutputTokens": 200,
            },
        }
        response = self._client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
