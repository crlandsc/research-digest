# Decisions

This file records decisions that should survive across sessions.

## Status legend

- Accepted — current default
- Deferred — intentionally postponed
- Open — not yet decided
- Replaced — no longer current

---

## D-001
- Date: 2026-04-07
- Status: Accepted
- Decision: The repo is documentation-first, and the docs are the source of truth for Claude Code.
- Rationale: This makes the project resumable across sessions and reduces dependence on long prompt context.

## D-002
- Date: 2026-04-07
- Status: Accepted
- Decision: Version 1 is local-first.
- Rationale: This minimizes setup burden, reduces cost, and allows Claude to make meaningful progress without deployment blockers.

## D-003
- Date: 2026-04-07
- Status: Accepted
- Decision: arXiv is the only required source for the MVP.
- Rationale: It keeps the first implementation focused and avoids premature multi-source complexity.

## D-004
- Date: 2026-04-07
- Status: Accepted
- Decision: The first required output format is Markdown written to the local filesystem.
- Rationale: Markdown is simple, portable, and sufficient for proving usefulness.

## D-005
- Date: 2026-04-07
- Status: Accepted
- Decision: SQLite is the default persistence layer for the MVP.
- Rationale: It supports deduplication and resumability without requiring external infrastructure.

## D-006
- Date: 2026-04-07
- Status: Accepted
- Decision: Deterministic ranking is required before optional LLM enhancement.
- Rationale: A useful baseline should exist without needing external credentials or paid APIs.

## D-007
- Date: 2026-04-07
- Status: Accepted
- Decision: Python 3.12+ is the preferred implementation language.
- Rationale: It is well-suited to CLI workflows, feed processing, and fast iteration.

## D-008
- Date: 2026-04-07
- Status: Deferred
- Decision: Email, Slack, or other delivery channels are not part of the initial critical path.
- Rationale: Delivery can be layered on after the local digest exists.

## D-009
- Date: 2026-04-07
- Status: Deferred
- Decision: LLM-backed summarization is optional and not required for the first useful version.
- Rationale: The first version should work without provider setup.

## D-010
- Date: 2026-04-07
- Status: Deferred
- Decision: Deployment and scheduled automation are postponed until after the local workflow works end-to-end.
- Rationale: The current priority is correctness and usefulness, not hosting.

## D-011
- Date: 2026-04-08
- Status: Accepted
- Decision: The MVP remains arXiv-only, but if the project is focused on music/audio AI/ML, the preferred expansion order is ISMIR/TISMIR first, then DCASE and MIREX, then broader audio venues such as ICASSP and IEEE/ACM TASLP.
- Rationale: This keeps the first implementation simple while aligning future source expansion with the most relevant domain venues and evaluation ecosystems.

## D-012
- Date: 2026-04-08
- Status: Accepted
- Decision: CLI command name is `research-digest` (not `rdigest`).
- Rationale: More descriptive. User plans automated usage so brevity is less important than clarity.

## D-013
- Date: 2026-04-08
- Status: Accepted
- Decision: Target Python 3.12 as minimum. Prefer stability over latest version.
- Rationale: User preference for proven, stable tooling over bleeding-edge.

## D-014
- Date: 2026-04-08
- Status: Accepted
- Decision: Build the tool as general-purpose, but parameterize default config toward music/audio AI/ML interests.
- Rationale: Architecture should support any research domain; example config and defaults should reflect the primary user's focus.

## D-015
- Date: 2026-04-08
- Status: Accepted
- Decision: Use the legacy arXiv Atom/XML API (not the newer experimental REST API).
- Rationale: Stable, well-documented, sufficient for MVP. Document the REST API in architecture for future consideration.

## D-016
- Date: 2026-04-08
- Status: Accepted
- Decision: Support two lookback modes: (1) N-day lookback (default for manual runs), (2) since-last-run (for automated/scheduled runs). Deduplication prevents overlap.
- Rationale: N-day is simpler for ad-hoc usage. Since-last-run enables complete coverage in automated pipelines without sending duplicates.

## D-017
- Date: 2026-04-08
- Status: Accepted
- Decision: Renamed `.env.example` to `env.example` so Claude Code can read it through the sandbox.
- Rationale: Sandbox denies read access to `.env.*` patterns. The actual `.env` retains the dotfile convention.

## D-018
- Date: 2026-04-08
- Status: Accepted
- Decision: Summarization subpackage deferred; extractive summary in pipeline/summarize.py for MVP.
- Rationale: Full summarization/ package with LLM providers not needed until optional LLM work begins.

## D-019
- Date: 2026-04-08
- Status: Accepted
- Decision: arXiv query uses AND between categories and keywords when both present.
- Rationale: Simple, predictable. Users wanting all papers in a category should leave keyword_queries empty.

## D-020
- Date: 2026-04-08
- Status: Accepted
- Decision: Hatchling build backend for pyproject.toml with src layout.
- Rationale: Lightweight, modern, native src layout support.

## D-021
- Date: 2026-04-08
- Status: Accepted
- Decision: Sync httpx only (no async). Jinja2 template inline in rendering/markdown.py.
- Rationale: CLI tool with 3s API delays doesn't benefit from async. Inline template is simpler than separate file.

---

## Instructions for future updates

When Claude makes or changes an architectural or product decision, it should:
1. add a new decision entry or update the relevant one
2. avoid silently changing an accepted decision
3. update related docs if the decision affects them