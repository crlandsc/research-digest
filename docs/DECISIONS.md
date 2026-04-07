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

---

## Instructions for future updates

When Claude makes or changes an architectural or product decision, it should:
1. add a new decision entry or update the relevant one
2. avoid silently changing an accepted decision
3. update related docs if the decision affects them