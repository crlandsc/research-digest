"""Tests for summarization providers."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from research_digest.config import AppConfig
from research_digest.models import Paper
from research_digest.summarization.extractive import ExtractiveProvider
from research_digest.summarization.providers import get_provider


def _paper(**kw) -> Paper:
    defaults = dict(
        source="arxiv", external_id="2401.00001", title="Test Paper",
        authors=["Alice"], abstract="First sentence. Second sentence. Third sentence. Fourth.",
        categories=["cs.SD"],
        published_at=datetime(2024, 1, 15, tzinfo=timezone.utc),
        canonical_url="http://arxiv.org/abs/2401.00001",
    )
    defaults.update(kw)
    return Paper(**defaults)


class TestExtractiveProvider:
    def test_summarizes_paper(self) -> None:
        provider = ExtractiveProvider()
        result = provider.summarize_paper(_paper())
        assert "First sentence" in result.text
        assert "Fourth" not in result.text
        assert result.source == "extractive"

    def test_summarizes_multiple(self) -> None:
        provider = ExtractiveProvider()
        papers = [_paper(external_id=f"p{i}") for i in range(3)]
        results = provider.summarize_papers(papers)
        assert len(results) == 3
        assert all(eid in results for eid in ["p0", "p1", "p2"])
        assert all(r.source == "extractive" for r in results.values())


class TestProviderFactory:
    def test_default_is_extractive(self) -> None:
        cfg = AppConfig()
        provider = get_provider(cfg)
        assert isinstance(provider, ExtractiveProvider)

    def test_extractive_when_mode_extractive(self) -> None:
        cfg = AppConfig()
        cfg.summarization.mode = "extractive"
        provider = get_provider(cfg)
        assert isinstance(provider, ExtractiveProvider)

    def test_gemini_when_configured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")
        cfg = AppConfig()
        cfg.summarization.mode = "llm"
        cfg.summarization.provider = "gemini"
        provider = get_provider(cfg)
        from research_digest.summarization.gemini import GeminiProvider
        assert isinstance(provider, GeminiProvider)

    def test_gemini_missing_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        cfg = AppConfig()
        cfg.summarization.mode = "llm"
        cfg.summarization.provider = "gemini"
        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            get_provider(cfg)


class TestGeminiProvider:
    def test_summarize_paper_calls_api(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        from research_digest.summarization.gemini import GeminiProvider

        provider = GeminiProvider()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "A concise summary of the paper."}]}}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(provider._client, "post", return_value=mock_response):
            result = provider.summarize_paper(_paper())

        assert result.text == "A concise summary of the paper."
        assert result.source == "gemini-3-flash-preview"

    def test_fallback_on_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        from research_digest.summarization.gemini import GeminiProvider

        provider = GeminiProvider()
        with patch.object(provider._client, "post", side_effect=Exception("API down")):
            results = provider.summarize_papers([_paper()])

        # Should fall back to extractive
        assert "2401.00001" in results
        assert "First sentence" in results["2401.00001"].text
        assert results["2401.00001"].source == "extractive"

    def test_timeout_falls_through_to_next_model(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Timeout on one model should try the next, not skip to extractive."""
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        import httpx as _httpx
        from research_digest.summarization.gemini import GeminiProvider

        provider = GeminiProvider()

        ok_response = MagicMock()
        ok_response.status_code = 200
        ok_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Summary from later model."}]}}]
        }

        call_count = 0
        def mock_post(url, **kwargs):
            nonlocal call_count
            call_count += 1
            # First 3 models timeout, 4th succeeds (gemini-2.5-flash)
            if call_count <= 3:
                raise _httpx.ReadTimeout("timed out")
            return ok_response

        with patch.object(provider._client, "post", side_effect=mock_post):
            result = provider.summarize_paper(_paper())

        assert result.text == "Summary from later model."
        assert result.source == "gemini-2.5-flash"
        assert call_count == 4  # 3 timeouts + 1 success
