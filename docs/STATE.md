# Current State

## Current milestone
Milestone 3 — complete. Local MVP is functional.

## Completed
- M0: documentation scaffold
- M1: project scaffold (pyproject.toml, config loading, CLI entrypoint, tests)
- M2: ingest and persistence (arXiv fetcher, SQLite storage, pipeline fetch, tests)
- M3: ranking and digest generation (scoring, filters, Markdown renderer, full pipeline, tests)
- 78 tests all passing
- Decisions D-012 through D-021 recorded

## Working commands
- `research-digest fetch` — fetch papers from arXiv into SQLite
- `research-digest rank` — score and rank stored papers
- `research-digest build` — generate Markdown digest from ranked papers
- `research-digest run` — full pipeline (fetch + rank + build)
- `research-digest fetch --dry-run` — preview query without fetching
- `research-digest run --since-last-run` — fetch only new papers since last run

## Next steps
1. Create `config/topics.yaml` with user — tailor to specific music/audio AI/ML interests (MS-002)
2. First live run with real arXiv data to validate end-to-end
3. Begin M4 (usability hardening) if desired
4. Optional: LLM summarization, scheduling, delivery (M5)

## Manual steps status
- MS-001 (.env): not needed yet
- MS-002 (topics.yaml): **ready to do** — create collaboratively with user before first real run
- MS-003–MS-005: deferred

## Open decisions
- No critical open decisions
- LLM provider choice deferred to M5
- Delivery channel deferred to M5

## Last updated
2026-04-08
