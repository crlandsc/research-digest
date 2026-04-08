"""Tests for config loading and validation."""

import os
from pathlib import Path

import pytest
import yaml

from research_digest.config import AppConfig, load_config, resolve_config_path


def test_load_valid_config(tmp_config_file: Path) -> None:
    cfg = load_config(tmp_config_file)
    assert cfg.version == 1
    assert cfg.sources.arxiv.enabled is True
    assert cfg.sources.arxiv.categories == ["cs.SD"]
    assert cfg.sources.arxiv.keyword_queries == ["audio"]
    assert cfg.sources.arxiv.lookback_days == 3
    assert cfg.sources.arxiv.max_results_per_run == 50


def test_load_config_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "nonexistent.yaml"
    with pytest.raises(SystemExit):
        load_config(missing)


def test_load_config_malformed_yaml(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("{{invalid yaml content::")
    with pytest.raises(SystemExit):
        load_config(bad)


def test_load_config_uses_defaults(tmp_path: Path) -> None:
    minimal = tmp_path / "minimal.yaml"
    minimal.write_text(yaml.dump({"version": 1}))
    cfg = load_config(minimal)
    assert cfg.sources.arxiv.lookback_days == 7
    assert cfg.ranking.max_candidates_for_digest == 20
    assert cfg.digest.title == "Research Digest"
    assert cfg.summarization.mode == "extractive"


def test_env_var_override(tmp_config_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DIGEST_MAX_ITEMS", "5")
    cfg = load_config(tmp_config_file)
    assert cfg.ranking.max_candidates_for_digest == 5


def test_resolve_config_path_explicit(tmp_config_file: Path) -> None:
    resolved = resolve_config_path(tmp_config_file)
    assert resolved == tmp_config_file


def test_resolve_config_path_env_var(
    tmp_config_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TOPICS_CONFIG_PATH", str(tmp_config_file))
    resolved = resolve_config_path()
    assert resolved == tmp_config_file


def test_resolve_config_path_fallback_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TOPICS_CONFIG_PATH", raising=False)
    # Relies on running from repo root where config/ exists
    topics = Path("config/topics.yaml")
    example = Path("config/topics.example.yaml")
    if topics.exists():
        resolved = resolve_config_path()
        assert resolved == topics  # topics.yaml takes priority over example
    elif example.exists():
        resolved = resolve_config_path()
        assert resolved == example
    else:
        pytest.skip("no config files found (not running from repo root)")


def test_resolve_config_path_missing_explicit(tmp_path: Path) -> None:
    missing = tmp_path / "nope.yaml"
    with pytest.raises(SystemExit):
        resolve_config_path(missing)


def test_resolve_config_path_missing_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TOPICS_CONFIG_PATH", str(tmp_path / "nope.yaml"))
    with pytest.raises(SystemExit):
        resolve_config_path()
