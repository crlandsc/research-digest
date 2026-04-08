# Tasks

This file is the prioritized build backlog.

## Milestone 0 — documentation scaffold
- [x] Create base repo documentation
- [x] Define MVP scope
- [x] Define architecture direction
- [x] Define manual-step escalation protocol

## Milestone 1 — project scaffold
- [x] Create Python project scaffold
- [x] Add `pyproject.toml`
- [x] Add initial package structure under `src/`
- [x] Add testing scaffold
- [x] Add basic CLI entrypoint
- [x] Add config loading from YAML and env vars
- [x] Add README quickstart for local runs

## Milestone 2 — ingest and persistence
- [x] Implement arXiv fetcher
- [x] Normalize paper metadata
- [x] Add local SQLite persistence
- [x] Add deduplication logic
- [x] Add basic logging and error handling
- [x] Add tests for config and fetch normalization

## Milestone 3 — ranking and digest generation
- [x] Implement filtering rules
- [x] Implement deterministic ranking
- [x] Generate Markdown digest
- [x] Write output to dated local folder
- [x] Add tests for ranking and rendering
- [x] Add one-command local run path

## Milestone 4 — usability hardening
- [x] Improve CLI ergonomics
- [x] Improve failure messages
- [x] Add fixture-based tests
- [x] Add sample local workflow docs (covered by README quickstart)

## Milestone 5 — optional enhancements
- [ ] Add optional LLM summarization abstraction
- [ ] Add provider-backed summarization implementation
- [ ] Add optional email/slack delivery
- [ ] Add optional scheduling
- [ ] Add optional deployment path
- [ ] Design source adapters for future music/audio venues (ISMIR, TISMIR, DCASE, MIREX, ICASSP, TASLP)

## Prioritization rule

Claude should always choose the highest-priority unblocked task unless `docs/STATE.md` gives a more specific immediate plan.