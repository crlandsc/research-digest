# Current State

## Current milestone
Milestone 1 — project scaffold (starting)

## Completed
- M0: documentation scaffold
- Repo audit: all docs internally consistent, no conflicts
- Decisions D-012 through D-017 recorded (CLI name, Python 3.12, general+audio parameterization, legacy arXiv API, dual lookback modes, env.example rename)

## In progress
- Planning implementation for Milestones 1–3 (full local MVP)

## Blocked
- No current blockers
- Entire local MVP path (M1–M3) requires zero external credentials

## Next milestone plan (M1–M3: local MVP)

### M1 — Project scaffold
- pyproject.toml with Python 3.12+ and all deps
- src/research_digest/ package structure per ARCHITECTURE.md
- CLI entrypoint (`research-digest`) via Typer
- Config loading from YAML + env vars
- Basic test scaffold with pytest

### M2 — Ingest and persistence
- arXiv Atom/XML fetcher via httpx
- Paper metadata normalization (Pydantic models)
- SQLite persistence with deduplication
- Run history tracking (for since-last-run mode)
- Logging and error handling
- Tests for config loading and fetch normalization

### M3 — Ranking and digest generation
- Filtering rules (keyword include/exclude, category match)
- Deterministic scoring/ranking
- Markdown digest renderer
- Dated output to output/<date>/digest.md
- Dual lookback: N-day default + since-last-run flag
- `research-digest run` one-command path
- Tests for ranking and rendering

## Open decisions
- No critical open decisions block M1–M3
- LLM provider choice deferred to M5
- Delivery channel deferred to M5

## Manual steps status
- MS-001 (.env): not needed yet
- MS-002 (topics.yaml): needed before first real run, not before scaffold
- MS-003–MS-005: deferred

## Last updated
2026-04-08
