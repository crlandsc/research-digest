"""Google Gemini summarization provider with model fallback chain."""

import logging
import os
import time

import httpx

from research_digest.models import Paper, SummaryResult
from research_digest.summarization.base import SummarizationProvider

logger = logging.getLogger(__name__)

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# Fallback chain ordered by quality (benchmarks: GPQA Diamond / MMLU).
# Each model uses the same generateContent REST API.
#
# Model                            GPQA   MMLU   RPM   RPD
# -------------------------------- ------ ------ ----- -----
# gemini-3-flash-preview           90.4   91.8     5    20
# gemini-3.1-flash-lite-preview    86.9   88.9    15   500
# gemma-4-31b-it                   84.3   85.2    15  1500
# gemini-2.5-flash                 82.8   88.4     5    20
# gemini-2.5-flash-lite            64.6   81.1    10    20
MODEL_CHAIN = [
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
    "gemma-4-31b-it",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]

RETRIES_PER_MODEL = 2
RETRY_DELAY = 3  # seconds between retries on same model

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
    """Summarization via Google Gemini/Gemma models (free tier) with fallback chain."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY not set. Get a free key at https://aistudio.google.com/apikey"
            )
        self._client = httpx.Client(timeout=30.0)
        logger.info("Gemini provider initialized (key: %s...)", self.api_key[:8])

    def summarize_paper(self, paper: Paper) -> SummaryResult:
        prompt = _USER_TEMPLATE.format(
            title=paper.title,
            abstract=paper.abstract,
        )
        return self._call_with_fallback(prompt)

    def summarize_papers(self, papers: list[Paper]) -> dict[str, SummaryResult]:
        logger.info("Summarizing %d papers with Gemini (model chain: %s)",
                     len(papers), ", ".join(MODEL_CHAIN))
        results: dict[str, SummaryResult] = {}
        for i, paper in enumerate(papers):
            if i > 0:
                time.sleep(4)  # stay under 15 RPM free tier limit
            try:
                result = self.summarize_paper(paper)
                results[paper.external_id] = result
                logger.info("Summary for %s (%d/%d) via %s: %s",
                            paper.external_id, i + 1, len(papers),
                            result.source, result.text[:80])
            except Exception as e:
                logger.error("All models failed for %s: %s", paper.external_id, e, exc_info=True)
                from research_digest.pipeline.summarize import extractive_summary
                results[paper.external_id] = SummaryResult(
                    text=extractive_summary(paper.abstract),
                    source="extractive",
                )
        return results

    def _call_with_fallback(self, prompt: str) -> SummaryResult:
        """Try each model in the chain until one succeeds."""
        payload = {
            "system_instruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 8192,
            },
        }

        last_response = None
        for model in MODEL_CHAIN:
            url = f"{API_BASE}/{model}:generateContent?key={self.api_key}"
            for attempt in range(RETRIES_PER_MODEL):
                logger.debug("Requesting %s (attempt %d/%d)", model, attempt + 1, RETRIES_PER_MODEL)
                response = self._client.post(url, json=payload)
                logger.debug("Response from %s: HTTP %d", model, response.status_code)

                if response.status_code == 200:
                    data = response.json()
                    text = self._extract_answer(data)
                    if text is None:
                        logger.error("No answer text in response from %s: %s", model, data)
                        raise ValueError(f"No answer text in response from {model}")
                    return SummaryResult(text=text, source=model)

                last_response = response
                if response.status_code in (429, 503) and attempt < RETRIES_PER_MODEL - 1:
                    logger.warning("%s returned %d, retry %d/%d in %ds",
                                   model, response.status_code,
                                   attempt + 1, RETRIES_PER_MODEL, RETRY_DELAY)
                    time.sleep(RETRY_DELAY)
                    continue

                logger.warning("%s failed with %d, trying next model", model, response.status_code)
                break

        # all models exhausted
        logger.error("All %d models failed. Last: %d %s",
                     len(MODEL_CHAIN), last_response.status_code, last_response.text[:300])
        last_response.raise_for_status()

    @staticmethod
    def _extract_answer(data: dict) -> str | None:
        """Extract the non-thinking answer text from a generateContent response.

        Thinking models return parts with thought=true for reasoning and
        thought=false/absent for the actual answer. We skip thinking parts.
        """
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        # Prefer non-thinking parts
        answer_parts = [p["text"] for p in parts if "text" in p and not p.get("thought")]
        if answer_parts:
            return answer_parts[0].strip()
        # Fallback: any part with text (non-thinking models)
        all_text = [p["text"] for p in parts if "text" in p]
        return all_text[0].strip() if all_text else None
