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

## Current status

This is the documentation-first base repo.

The implementation scaffold and application code are expected to be created by Claude Code after reading these docs.

## Repository layout

- `README.md` — human-facing project overview
- `CLAUDE.md` — operating instructions for Claude Code
- `.env.example` — example environment variables; never commit real secrets
- `config/topics.example.yaml` — example topic/filter configuration
- `docs/PRODUCT_SPEC.md` — product goals, MVP scope, non-goals
- `docs/ARCHITECTURE.md` — preferred technical direction and target structure
- `docs/DECISIONS.md` — decision log
- `docs/TASKS.md` — prioritized implementation backlog
- `docs/STATE.md` — current status and next action
- `docs/MANUAL_STEPS.md` — human-only setup tasks and escalation protocol

## Project goals

The project should eventually let a user:
- define research interests and filters
- fetch recent papers from arXiv
- score or rank those papers
- produce a readable digest
- optionally enhance summaries with an LLM
- optionally deliver the digest through email or another channel later

## MVP boundaries

For the first useful version:
- source: arXiv only
- output: local Markdown files
- runtime: local CLI
- persistence: local SQLite
- summarization: extractive/by-abstract is acceptable
- LLM enhancement: optional, not required for the first working version

## Human quickstart

1. Paste these files into the repo.
2. Review `docs/PRODUCT_SPEC.md` and `docs/ARCHITECTURE.md`.
3. If you strongly disagree with a core choice, edit the docs now before handing off to Claude.
4. Optionally customize `config/topics.example.yaml` later; this is not required before the first Claude run.
5. Open the repo in Claude Code.
6. Give Claude the kickoff prompt included below in the handoff instructions.

## Notes

- Do not create API keys yet unless Claude specifically asks for one.
- Do not over-configure hosting, email, or automation before the local MVP exists.
- If the repo is not actually named `research-digest`, that is cosmetic; the docs still work.