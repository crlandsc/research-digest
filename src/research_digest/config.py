"""Configuration loading from YAML + environment variable overrides."""

import logging
import os
import sys
from pathlib import Path

import yaml
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Default config search paths (in priority order)
_CONFIG_CANDIDATES = [
    Path("config/topics.yaml"),
    Path("config/topics.example.yaml"),
]


class ArxivSourceConfig(BaseModel):
    enabled: bool = True
    categories: list[str] = []
    keyword_queries: list[str] = []
    lookback_days: int = 7
    max_results_per_run: int = 200


class FiltersConfig(BaseModel):
    required_keywords: list[str] = []
    excluded_keywords: list[str] = []
    max_authors: int | None = None


class RankingConfig(BaseModel):
    prioritize_recency: bool = True
    prioritize_keyword_matches: bool = True
    max_candidates_for_digest: int = 20


class DigestConfig(BaseModel):
    title: str = "Research Digest"
    formats: list[str] = ["markdown"]
    include_abstract_excerpt: bool = True
    include_reason_selected: bool = True
    include_links: bool = True


class SummarizationConfig(BaseModel):
    mode: str = "extractive"
    provider: str = "none"


class SourcesConfig(BaseModel):
    arxiv: ArxivSourceConfig = ArxivSourceConfig()


class AppConfig(BaseModel):
    version: int = 1
    sources: SourcesConfig = SourcesConfig()
    filters: FiltersConfig = FiltersConfig()
    ranking: RankingConfig = RankingConfig()
    digest: DigestConfig = DigestConfig()
    summarization: SummarizationConfig = SummarizationConfig()


def resolve_config_path(explicit: Path | None = None) -> Path:
    """Resolve config file path via fallback chain.

    Priority: explicit arg > TOPICS_CONFIG_PATH env > config/topics.yaml > config/topics.example.yaml.
    """
    if explicit is not None:
        if explicit.exists():
            return explicit
        print(f"Error: config file not found: {explicit}", file=sys.stderr)
        raise SystemExit(1)

    env_path = os.environ.get("TOPICS_CONFIG_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p
        print(f"Error: TOPICS_CONFIG_PATH does not exist: {env_path}", file=sys.stderr)
        raise SystemExit(1)

    for candidate in _CONFIG_CANDIDATES:
        if candidate.exists():
            return candidate

    print(
        "Error: no config file found. Expected one of:\n"
        "  - config/topics.yaml\n"
        "  - config/topics.example.yaml\n"
        "  Set TOPICS_CONFIG_PATH or pass --config.",
        file=sys.stderr,
    )
    raise SystemExit(1)


def load_config(path: Path | None = None) -> AppConfig:
    """Load and validate config from YAML, with env var overrides."""
    resolved = resolve_config_path(path)
    logger.info("Loading config from %s", resolved)

    try:
        raw = yaml.safe_load(resolved.read_text())
    except yaml.YAMLError as e:
        print(f"Error: malformed YAML in {resolved}: {e}", file=sys.stderr)
        raise SystemExit(1)

    if not isinstance(raw, dict):
        print(f"Error: config file must be a YAML mapping, got {type(raw).__name__}", file=sys.stderr)
        raise SystemExit(1)

    config = AppConfig.model_validate(raw)

    # Apply env var overrides
    if env_max := os.environ.get("DIGEST_MAX_ITEMS"):
        config.ranking.max_candidates_for_digest = int(env_max)

    return config
