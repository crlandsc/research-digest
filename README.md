# research-digest

A docs-first repository for building a local-first research digest generator.

Version 1 focuses on:
- pulling recent papers from arXiv
- filtering and ranking them against configured interests
- generating a clean Markdown digest
- working locally before any deployment or paid integrations

This repo is intentionally structured so Claude Code can build incrementally with minimal human coordination.

## Operating model

The repository documentation is the source of truth.

Claude Code should:
1. read the repo docs first
2. choose the highest-priority unblocked next step
3. build incrementally
4. keep documentation updated as implementation becomes concrete
5. stop only when a human-only action is required

When Claude gets blocked on something only a human can do, it should use the `ACTION REQUIRED` format defined in `CLAUDE.md` and `docs/MANUAL_STEPS.md`.

## Quickstart

### Prerequisites

- Python 3.12+
- [pyenv](https://github.com/pyenv/pyenv) recommended (with pyenv-virtualenv)

### Setup

```bash
# Clone and enter the repo
cd research-digest

# Create a virtualenv (pyenv example)
pyenv virtualenv 3.12.12 research-digest
pyenv local research-digest

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### Configure topics

```bash
# Copy the example and edit to your interests
cp config/topics.example.yaml config/topics.yaml
# Edit config/topics.yaml — set categories, keywords, filters
```

Or just run with the example config (music/audio AI/ML defaults).

### Run

```bash
# Full pipeline: fetch from arXiv, rank, generate digest
research-digest run

# Preview the query without fetching
research-digest fetch --dry-run

# Fetch only new papers since the last successful run
research-digest run --since-last-run

# Override lookback window
research-digest run --lookback-days 14

# Run individual steps
research-digest fetch
research-digest rank
research-digest build
```

Output is written to `output/<YYYY-MM-DD>/digest.md`.

### Run tests

```bash
pytest
```

## How it works

1. **Fetch** — queries arXiv's Atom/XML API with your configured categories and keywords
2. **Store** — persists paper metadata in a local SQLite database (`data/research_digest.db`)
3. **Rank** — scores papers using a deterministic point system (category match, keyword match, recency)
4. **Build** — generates a Markdown digest with ranked papers, excerpts, and selection reasons

No LLM or external API keys required for the base pipeline.

## Repository layout

```
src/research_digest/
  cli.py              — Typer CLI (fetch, rank, build, run)
  config.py           — YAML + env var config loading
  models.py           — Pydantic data models (Paper, ScoredPaper, etc.)
  fetchers/arxiv.py   — arXiv API client and XML parser
  storage/db.py       — SQLite schema and connection management
  storage/repository.py — data access layer
  pipeline/fetch.py   — fetch orchestration
  pipeline/rank.py    — filtering and scoring
  pipeline/build_digest.py — digest assembly
  pipeline/summarize.py — extractive summarization
  rendering/markdown.py — Jinja2 Markdown renderer
tests/                — pytest suite (78 tests)
config/               — topic configuration (YAML)
output/               — generated digests
data/                 — SQLite database (gitignored)
docs/                 — project documentation
```

## Configuration

Edit `config/topics.yaml` to set:
- **categories** — arXiv category codes (e.g., `cs.SD`, `eess.AS`)
- **keyword_queries** — search phrases combined with categories via AND
- **excluded_keywords** — papers matching these are filtered out
- **lookback_days** — how far back to fetch (default: 7)
- **max_candidates_for_digest** — max papers in the digest (default: 20)

See `config/topics.example.yaml` for a full annotated example.

## Future source expansion

The tool is currently arXiv-only. Planned future sources for music/audio AI/ML:
- ISMIR, TISMIR, DCASE, MIREX, ICASSP, IEEE/ACM TASLP
- Semantic Scholar metadata enrichment