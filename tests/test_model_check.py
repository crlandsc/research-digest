"""Tests for the Gemini model-drift checker."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from research_digest.summarization.model_check import (
    ModelCheckReport,
    RemoteModel,
    check_drift,
    format_report,
    list_remote_models,
    run_check,
)


# Helpers ---------------------------------------------------------------------


def _remote(name: str, *, methods: list[str] | None = None, display: str = "") -> RemoteModel:
    return RemoteModel(
        name=name,
        display_name=display or name,
        supported_methods=methods if methods is not None else ["generateContent"],
    )


# check_drift -----------------------------------------------------------------


class TestCheckDrift:
    def test_clean_chain_no_drift(self) -> None:
        chain = ["gemini-3.5-flash", "gemini-3.1-flash-lite"]
        remote = {m: _remote(m) for m in chain}
        report = check_drift(chain, remote)
        assert report.missing_from_remote == []
        assert report.newer_in_family == []
        assert not report.has_drift

    def test_detects_retired_model(self) -> None:
        chain = ["gemini-3.5-flash", "gemini-2.5-flash"]
        remote = {"gemini-3.5-flash": _remote("gemini-3.5-flash")}
        report = check_drift(chain, remote)
        assert report.missing_from_remote == ["gemini-2.5-flash"]
        assert report.has_drift

    def test_detects_newer_flash_sibling(self) -> None:
        chain = ["gemini-3.5-flash"]
        remote = {
            "gemini-3.5-flash": _remote("gemini-3.5-flash"),
            "gemini-3.6-flash": _remote("gemini-3.6-flash", display="Gemini 3.6 Flash"),
        }
        report = check_drift(chain, remote)
        assert "gemini-3.6-flash" in report.newer_in_family
        assert report.has_drift

    def test_ignores_dated_variants_of_chain_models(self) -> None:
        chain = ["gemini-3.5-flash"]
        remote = {
            "gemini-3.5-flash": _remote("gemini-3.5-flash"),
            "gemini-3.5-flash-001": _remote("gemini-3.5-flash-001"),
            "gemini-3.5-flash-preview-05-2026": _remote("gemini-3.5-flash-preview-05-2026"),
        }
        report = check_drift(chain, remote)
        assert report.newer_in_family == []

    def test_ignores_non_generate_models(self) -> None:
        chain = ["gemini-3.5-flash"]
        remote = {
            "gemini-3.5-flash": _remote("gemini-3.5-flash"),
            "gemini-3.6-flash-tts": _remote("gemini-3.6-flash-tts", methods=["streamGenerateContent"]),
            "gemini-embedding-2": _remote("gemini-embedding-2", methods=["embedContent"]),
        }
        report = check_drift(chain, remote)
        # tts/embed must not show up as a chain candidate
        assert "gemini-embedding-2" not in report.newer_in_family
        assert "gemini-3.6-flash-tts" not in report.newer_in_family

    def test_does_not_flag_family_with_no_chain_members(self) -> None:
        # we don't use gemini-pro in the chain; a new pro shouldn't trigger drift
        chain = ["gemini-3.5-flash"]
        remote = {
            "gemini-3.5-flash": _remote("gemini-3.5-flash"),
            "gemini-3.5-pro": _remote("gemini-3.5-pro"),
        }
        report = check_drift(chain, remote)
        assert "gemini-3.5-pro" not in report.newer_in_family

    def test_distinguishes_flash_from_flash_lite(self) -> None:
        chain = ["gemini-3.5-flash", "gemini-3.1-flash-lite"]
        remote = {
            "gemini-3.5-flash": _remote("gemini-3.5-flash"),
            "gemini-3.1-flash-lite": _remote("gemini-3.1-flash-lite"),
            "gemini-3.6-flash": _remote("gemini-3.6-flash"),
            "gemini-3.2-flash-lite": _remote("gemini-3.2-flash-lite"),
        }
        report = check_drift(chain, remote)
        assert "gemini-3.6-flash" in report.newer_in_family
        assert "gemini-3.2-flash-lite" in report.newer_in_family

    def test_detects_new_gemma_in_family(self) -> None:
        chain = ["gemma-4-31b-it"]
        remote = {
            "gemma-4-31b-it": _remote("gemma-4-31b-it"),
            "gemma-5-30b-it": _remote("gemma-5-30b-it"),
        }
        report = check_drift(chain, remote)
        assert "gemma-5-30b-it" in report.newer_in_family

    def test_ignores_older_version_than_chain(self) -> None:
        # chain has 2.5-flash; ListModels still exposes 2.0-flash → don't flag
        chain = ["gemini-2.5-flash"]
        remote = {
            "gemini-2.5-flash": _remote("gemini-2.5-flash"),
            "gemini-2.0-flash": _remote("gemini-2.0-flash"),
            "gemini-2.0-flash-001": _remote("gemini-2.0-flash-001"),
        }
        report = check_drift(chain, remote)
        assert report.newer_in_family == []

    def test_ignores_specialty_variants(self) -> None:
        # tts / image / audio models share generateContent but aren't text models
        chain = ["gemini-3.5-flash"]
        remote = {
            "gemini-3.5-flash": _remote("gemini-3.5-flash"),
            "gemini-3.6-flash-tts-preview": _remote("gemini-3.6-flash-tts-preview"),
            "gemini-3.6-flash-image-preview": _remote("gemini-3.6-flash-image-preview"),
            "gemini-3.6-flash-audio-preview": _remote("gemini-3.6-flash-audio-preview"),
            "gemini-3.6-flash-live-preview": _remote("gemini-3.6-flash-live-preview"),
            "imagen-5": _remote("imagen-5"),
            "veo-4": _remote("veo-4"),
        }
        report = check_drift(chain, remote)
        assert report.newer_in_family == []

    def test_uses_highest_chain_version_as_floor(self) -> None:
        # chain has 3.5 + 3 (older) — 3.4 between them shouldn't flag
        chain = ["gemini-3.5-flash", "gemini-3-flash-preview"]
        remote = {
            "gemini-3.5-flash": _remote("gemini-3.5-flash"),
            "gemini-3-flash-preview": _remote("gemini-3-flash-preview"),
            "gemini-3.4-flash": _remote("gemini-3.4-flash"),
            "gemini-3.6-flash": _remote("gemini-3.6-flash"),
        }
        report = check_drift(chain, remote)
        assert "gemini-3.4-flash" not in report.newer_in_family
        assert "gemini-3.6-flash" in report.newer_in_family


# list_remote_models ----------------------------------------------------------


class TestListRemoteModels:
    def test_strips_models_prefix(self) -> None:
        resp = MagicMock()
        resp.json.return_value = {
            "models": [
                {
                    "name": "models/gemini-3.5-flash",
                    "displayName": "Gemini 3.5 Flash",
                    "supportedGenerationMethods": ["generateContent"],
                }
            ]
        }
        resp.raise_for_status = MagicMock()
        with patch("httpx.Client") as ClientCls:
            client_instance = ClientCls.return_value.__enter__.return_value
            client_instance.get.return_value = resp
            result = list_remote_models("fake-key")
        assert "gemini-3.5-flash" in result
        assert result["gemini-3.5-flash"].display_name == "Gemini 3.5 Flash"
        assert result["gemini-3.5-flash"].supports_generate_content

    def test_paginates(self) -> None:
        page1 = MagicMock()
        page1.json.return_value = {
            "models": [{"name": "models/a", "supportedGenerationMethods": ["generateContent"]}],
            "nextPageToken": "tok",
        }
        page1.raise_for_status = MagicMock()
        page2 = MagicMock()
        page2.json.return_value = {
            "models": [{"name": "models/b", "supportedGenerationMethods": ["generateContent"]}]
        }
        page2.raise_for_status = MagicMock()
        with patch("httpx.Client") as ClientCls:
            client_instance = ClientCls.return_value.__enter__.return_value
            client_instance.get.side_effect = [page1, page2]
            result = list_remote_models("fake-key")
        assert set(result.keys()) == {"a", "b"}


# run_check -------------------------------------------------------------------


class TestRunCheck:
    def test_missing_key_returns_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        report = run_check()
        assert report.error is not None
        assert "GEMINI_API_KEY" in report.error
        assert report.has_drift  # error counts as drift so workflow exits nonzero

    def test_http_error_captured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GEMINI_API_KEY", "fake")
        with patch("research_digest.summarization.model_check.list_remote_models",
                   side_effect=httpx.ConnectError("network down")):
            report = run_check()
        assert report.error is not None
        assert "HTTP error" in report.error
        assert report.has_drift


# format_report ---------------------------------------------------------------


class TestFormatReport:
    def test_clean_report(self) -> None:
        report = ModelCheckReport(
            chain=["gemini-3.5-flash"],
            remote_models={"gemini-3.5-flash": _remote("gemini-3.5-flash")},
        )
        text = format_report(report)
        assert "All chain models present" in text
        assert "No newer family members" in text

    def test_report_with_drift(self) -> None:
        report = ModelCheckReport(
            chain=["gemini-3.5-flash", "gemini-2.5-flash"],
            remote_models={"gemini-3.5-flash": _remote("gemini-3.5-flash")},
            missing_from_remote=["gemini-2.5-flash"],
            newer_in_family=["gemini-3.6-flash"],
        )
        text = format_report(report)
        assert "MISSING FROM REMOTE" in text
        assert "gemini-2.5-flash" in text
        assert "NEWER FAMILY MEMBERS" in text
        assert "gemini-3.6-flash" in text
        assert "ACTION" in text

    def test_error_report(self) -> None:
        report = ModelCheckReport(chain=[], error="boom")
        text = format_report(report)
        assert "ERROR: boom" in text
