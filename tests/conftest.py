"""Shared pytest fixtures."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from research_digest.config import AppConfig
from research_digest.models import Paper


@pytest.fixture
def sample_config() -> AppConfig:
    return AppConfig.model_validate(
        {
            "version": 1,
            "sources": {
                "arxiv": {
                    "enabled": True,
                    "categories": ["cs.SD", "eess.AS"],
                    "keyword_queries": ["music generation", "source separation"],
                    "lookback_days": 7,
                    "max_results_per_run": 100,
                }
            },
            "filters": {
                "required_keywords": [],
                "excluded_keywords": ["survey"],
                "max_authors": None,
            },
            "ranking": {
                "prioritize_recency": True,
                "prioritize_keyword_matches": True,
                "max_candidates_for_digest": 10,
            },
            "digest": {
                "title": "Test Digest",
                "formats": ["markdown"],
                "include_abstract_excerpt": True,
                "include_reason_selected": True,
                "include_links": True,
            },
            "summarization": {"mode": "extractive", "provider": "none"},
        }
    )


@pytest.fixture
def sample_paper() -> Paper:
    return Paper(
        source="arxiv",
        external_id="2401.12345",
        title="Music Generation with Diffusion Models",
        authors=["Alice Smith", "Bob Jones"],
        abstract=(
            "We present a novel approach to music generation using diffusion models. "
            "Our method achieves state-of-the-art results on multiple benchmarks. "
            "We evaluate on both symbolic and audio domains."
        ),
        categories=["cs.SD", "cs.AI"],
        published_at=datetime(2024, 1, 15, 18, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 16, 9, 0, 0, tzinfo=timezone.utc),
        canonical_url="http://arxiv.org/abs/2401.12345",
        pdf_url="http://arxiv.org/pdf/2401.12345",
    )


@pytest.fixture
def sample_papers(sample_paper: Paper) -> list[Paper]:
    return [
        sample_paper,
        Paper(
            source="arxiv",
            external_id="2401.67890",
            title="Audio Classification via Contrastive Learning",
            authors=["Carol Davis"],
            abstract="A study of audio classification using contrastive methods.",
            categories=["eess.AS"],
            published_at=datetime(2024, 1, 14, 12, 0, 0, tzinfo=timezone.utc),
            canonical_url="http://arxiv.org/abs/2401.67890",
        ),
        Paper(
            source="arxiv",
            external_id="2401.11111",
            title="Source Separation with Transformer Networks",
            authors=["Eve Wilson", "Frank Lee", "Grace Kim"],
            abstract="We propose a transformer-based source separation model.",
            categories=["cs.SD", "eess.AS"],
            published_at=datetime(2024, 1, 13, 6, 0, 0, tzinfo=timezone.utc),
            canonical_url="http://arxiv.org/abs/2401.11111",
            pdf_url="http://arxiv.org/pdf/2401.11111",
        ),
        Paper(
            source="arxiv",
            external_id="2401.22222",
            title="A Survey of Neural Audio Synthesis",
            authors=["Hank Brown"],
            abstract="This survey reviews recent advances in neural audio synthesis.",
            categories=["cs.SD"],
            published_at=datetime(2024, 1, 12, 0, 0, 0, tzinfo=timezone.utc),
            canonical_url="http://arxiv.org/abs/2401.22222",
        ),
        Paper(
            source="arxiv",
            external_id="2401.33333",
            title="Speech Enhancement in Noisy Environments",
            authors=["Ivy Chen", "Jack Patel"],
            abstract="We address the problem of speech enhancement in noisy conditions.",
            categories=["eess.AS", "cs.SD"],
            published_at=datetime(2024, 1, 11, 15, 0, 0, tzinfo=timezone.utc),
            canonical_url="http://arxiv.org/abs/2401.33333",
            pdf_url="http://arxiv.org/pdf/2401.33333",
        ),
    ]


@pytest.fixture
def tmp_config_file(tmp_path: Path) -> Path:
    """Write a minimal valid config YAML to a temp file."""
    config_data = {
        "version": 1,
        "sources": {
            "arxiv": {
                "enabled": True,
                "categories": ["cs.SD"],
                "keyword_queries": ["audio"],
                "lookback_days": 3,
                "max_results_per_run": 50,
            }
        },
    }
    p = tmp_path / "topics.yaml"
    p.write_text(yaml.dump(config_data))
    return p
