# Tasks

This file is the prioritized build backlog.

## Milestone 0 — documentation scaffold
- [x] Create base repo documentation
- [x] Define MVP scope
- [x] Define architecture direction
- [x] Define manual-step escalation protocol

## Milestone 1 — project scaffold
- [ ] Create Python project scaffold
- [ ] Add `pyproject.toml`
- [ ] Add initial package structure under `src/`
- [ ] Add testing scaffold
- [ ] Add basic CLI entrypoint
- [ ] Add config loading from YAML and env vars
- [ ] Add README quickstart for local runs

## Milestone 2 — ingest and persistence
- [ ] Implement arXiv fetcher
- [ ] Normalize paper metadata
- [ ] Add local SQLite persistence
- [ ] Add deduplication logic
- [ ] Add basic logging and error handling
- [ ] Add tests for config and fetch normalization

## Milestone 3 — ranking and digest generation
- [ ] Implement filtering rules
- [ ] Implement deterministic ranking
- [ ] Generate Markdown digest
- [ ] Write output to dated local folder
- [ ] Add tests for ranking and rendering
- [ ] Add one-command local run path

## Milestone 4 — usability hardening
- [ ] Improve CLI ergonomics
- [ ] Improve failure messages
- [ ] Add fixture-based tests
- [ ] Add sample local workflow docs

## Milestone 5 — optional enhancements
- [ ] Add optional LLM summarization abstraction
- [ ] Add provider-backed summarization implementation
- [ ] Add optional email/slack delivery
- [ ] Add optional scheduling
- [ ] Add optional deployment path
- [ ] Design source adapters for future music/audio venues (ISMIR, TISMIR, DCASE, MIREX, ICASSP, TASLP)

## Prioritization rule

Claude should always choose the highest-priority unblocked task unless `docs/STATE.md` gives a more specific immediate plan.