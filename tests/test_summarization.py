"""Tests for summarization providers."""

import logging
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import httpx
import pytest

from research_digest.config import AppConfig
from research_digest.models import Paper
from research_digest.summarization.extractive import ExtractiveProvider
from research_digest.summarization.providers import get_provider

# Distinctive so hygiene tests can assert it never reaches a log record or a URL.
FAKE_KEY = "AIzaTESTKEY0000000000000000000000000000"


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


def _ok_response(text: str = "A concise summary of the paper.") -> MagicMock:
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = {"candidates": [{"content": {"parts": [{"text": text}]}}]}
    return r


def _status_response(code: int) -> MagicMock:
    r = MagicMock()
    r.status_code = code
    return r


class _Capture:
    """Records (url, kwargs) per call and replays a scripted response list; the last
    entry repeats once exhausted, so chain-exhaustion tests need only one entry.
    Signature matches the pre-existing stub style, `def mock_post(url, **kwargs)`.
    """

    def __init__(self, responses) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs))
        r = self._responses[min(len(self.calls) - 1, len(self._responses) - 1)]
        if isinstance(r, Exception):
            raise r
        return r

    @property
    def urls(self) -> list[str]:
        return [u for u, _ in self.calls]

    @property
    def payloads(self) -> list[dict]:
        return [kw["json"] for _, kw in self.calls]

    @property
    def models(self) -> list[str]:
        """Model id parsed back out of each URL, so chain-walk tests can assert which
        models were tried and in what order. URL cleanliness is asserted separately
        in TestGeminiRequestShape; this deliberately tolerates a query string so the
        two concerns stay independent.
        """
        return [
            u.rsplit("/", 1)[-1].split("?", 1)[0].removesuffix(":generateContent")
            for u in self.urls
        ]


@pytest.fixture
def gemini_provider(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)
    from research_digest.summarization.gemini import GeminiProvider
    return GeminiProvider()


@pytest.fixture
def short_chain(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Behaviour tests run against a synthetic chain so that editing the real
    MODEL_CHAIN never touches them. The real chain is pinned only in
    TestModelChainContract.
    """
    chain = ["model-a", "model-b", "model-c"]
    monkeypatch.setattr("research_digest.summarization.gemini.MODEL_CHAIN", chain)
    return chain


@pytest.fixture
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """RETRY_DELAY (3s) and the 4s inter-paper pacing would otherwise add seconds to
    every chain-walk test. gemini.py does `import time`, so patch the module
    attribute it resolves through.
    """
    import research_digest.summarization.gemini as gm
    monkeypatch.setattr(gm.time, "sleep", lambda *_: None)


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


class TestModelChainContract:
    """The single place the real chain is asserted. Every behaviour test below uses
    the synthetic `short_chain` fixture, so editing MODEL_CHAIN breaks exactly this
    class, deliberately and legibly.
    """

    def test_chain_is_exactly_as_documented(self) -> None:
        from research_digest.summarization.gemini import MODEL_CHAIN
        assert MODEL_CHAIN == [
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemma-4-31b-it",
        ]

    def test_chain_excludes_retired_models(self) -> None:
        from research_digest.summarization.gemini import MODEL_CHAIN
        retired = {
            "gemini-2.5-flash", "gemini-2.5-flash-lite",
            "gemini-3-flash-preview", "gemini-3.1-flash-lite-preview",
        }
        assert not (set(MODEL_CHAIN) & retired)

    def test_chain_entries_unique(self) -> None:
        from research_digest.summarization.gemini import MODEL_CHAIN
        assert len(MODEL_CHAIN) == len(set(MODEL_CHAIN))

    def test_status_table_documents_every_chain_model(self) -> None:
        """The comment table above MODEL_CHAIN is documentation that rots silently.
        Pin it both ways so a chain edit without a table edit fails here.
        """
        import inspect
        from research_digest.summarization import gemini
        header, _, _ = inspect.getsource(gemini).partition("MODEL_CHAIN = [")
        documented = {
            line[2:].split()[0]
            for line in header.splitlines()
            if line.startswith("# gemini-") or line.startswith("# gemma-")
        }
        assert documented == set(gemini.MODEL_CHAIN)


class TestGeminiProvider:
    def test_summarize_paper_calls_api(self, gemini_provider, short_chain) -> None:
        cap = _Capture([_ok_response()])
        with patch.object(gemini_provider._client, "post", side_effect=cap):
            result = gemini_provider.summarize_paper(_paper())

        assert result.text == "A concise summary of the paper."
        assert result.source == short_chain[0]
        assert len(cap.calls) == 1

    def test_fallback_on_failure(self, gemini_provider) -> None:
        with patch.object(gemini_provider._client, "post", side_effect=Exception("API down")):
            results = gemini_provider.summarize_papers([_paper()])

        # Should fall back to extractive
        assert "2401.00001" in results
        assert "First sentence" in results["2401.00001"].text
        assert results["2401.00001"].source == "extractive"


class TestGeminiFallbackChain:
    """Chain-walk behaviour, asserted against `short_chain` so these tests survive
    any edit to the real MODEL_CHAIN.
    """

    def test_timeout_falls_through_to_next_model(
        self, gemini_provider, short_chain, no_sleep
    ) -> None:
        """Timeout on one model should try the next, not skip to extractive."""
        cap = _Capture([
            httpx.ReadTimeout("timed out"),
            httpx.ReadTimeout("timed out"),
            _ok_response("Summary from later model."),
        ])
        with patch.object(gemini_provider._client, "post", side_effect=cap):
            result = gemini_provider.summarize_paper(_paper())

        assert result.text == "Summary from later model."
        assert result.source == short_chain[2]
        # Visited every model, in order, exactly once: timeouts are not retried.
        assert cap.models == short_chain
        assert len(cap.calls) == 3

    def test_non_retryable_status_advances_immediately(
        self, gemini_provider, short_chain, no_sleep
    ) -> None:
        cap = _Capture([
            _status_response(400),
            _status_response(400),
            _ok_response("third model ok"),
        ])
        with patch.object(gemini_provider._client, "post", side_effect=cap):
            result = gemini_provider.summarize_paper(_paper())

        assert result.source == short_chain[2]
        # 400 is not in (429, 503), so one attempt per model.
        assert cap.models == short_chain
        assert len(cap.calls) == 3

    def test_retryable_status_retries_same_model_then_advances(
        self, gemini_provider, short_chain, no_sleep
    ) -> None:
        cap = _Capture([
            _status_response(429),
            _status_response(429),
            _ok_response("second model ok"),
        ])
        with patch.object(gemini_provider._client, "post", side_effect=cap):
            result = gemini_provider.summarize_paper(_paper())

        assert result.source == short_chain[1]
        # RETRIES_PER_MODEL == 2, so model-a is attempted twice before advancing.
        assert cap.models == ["model-a", "model-a", "model-b"]

    def test_exhausted_chain_falls_back_to_extractive(
        self, gemini_provider, short_chain, no_sleep
    ) -> None:
        cap = _Capture([_status_response(503)])
        with patch.object(gemini_provider._client, "post", side_effect=cap):
            results = gemini_provider.summarize_papers([_paper()])

        assert results["2401.00001"].source == "extractive"
        assert len(cap.calls) == len(short_chain) * 2


class TestExtractiveFallbackVisibility:
    """A Gemini outage still produces a digest and exit 0, so the only signal is the
    log. These pin that signal.
    """

    @staticmethod
    def _two_papers() -> list[Paper]:
        return [_paper(external_id="p1"), _paper(external_id="p2")]

    def test_total_failure_logs_error(
        self, gemini_provider, short_chain, no_sleep, caplog
    ) -> None:
        cap = _Capture([_status_response(503)])
        with caplog.at_level(logging.WARNING):
            with patch.object(gemini_provider._client, "post", side_effect=cap):
                results = gemini_provider.summarize_papers(self._two_papers())

        assert all(r.source == "extractive" for r in results.values())
        errors = [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR]
        assert any("ZERO LLM summaries" in m and "all 2 papers" in m for m in errors)

    def test_partial_failure_logs_warning(
        self, gemini_provider, short_chain, no_sleep, caplog
    ) -> None:
        # First call succeeds (paper 1); every later call 503s, exhausting the chain
        # for paper 2, since _Capture repeats its last scripted response.
        cap = _Capture([_ok_response(), _status_response(503)])
        with caplog.at_level(logging.WARNING):
            with patch.object(gemini_provider._client, "post", side_effect=cap):
                results = gemini_provider.summarize_papers(self._two_papers())

        assert results["p1"].source == short_chain[0]
        assert results["p2"].source == "extractive"
        warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
        assert any("fell back to extractive for 1/2 papers" in m for m in warnings)
        assert not [r for r in caplog.records if r.levelno == logging.ERROR
                    and "ZERO LLM summaries" in r.getMessage()]

    def test_full_success_logs_no_fallback_message(
        self, gemini_provider, short_chain, no_sleep, caplog
    ) -> None:
        cap = _Capture([_ok_response()])
        with caplog.at_level(logging.WARNING):
            with patch.object(gemini_provider._client, "post", side_effect=cap):
                results = gemini_provider.summarize_papers(self._two_papers())

        assert all(r.source == short_chain[0] for r in results.values())
        assert not [r for r in caplog.records if "fell back to extractive" in r.getMessage()]
        assert not [r for r in caplog.records if "ZERO LLM summaries" in r.getMessage()]

    def test_empty_paper_list_logs_nothing(self, gemini_provider, caplog) -> None:
        """`papers and ...` guards against an empty list reporting a total failure."""
        with caplog.at_level(logging.WARNING):
            assert gemini_provider.summarize_papers([]) == {}
        assert not [r for r in caplog.records if "ZERO LLM summaries" in r.getMessage()]
