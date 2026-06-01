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

## D-022
- Date: 2026-04-08
- Status: Deferred
- Decision: Non-arXiv source adapters (ISMIR, TISMIR, DCASE, MIREX, ICASSP, TASLP) deferred indefinitely.
- Rationale: Most papers from these venues are posted to arXiv (cs.SD, eess.AS) before or around publication. Adding scrapers for conference websites would require significant maintenance for marginal coverage gain. Revisit only if specific papers are consistently being missed.

## D-023
- Date: 2026-04-14
- Status: Accepted
- Decision: Summarization uses a 5-model fallback chain ordered by quality benchmarks, not a single model.
- Rationale: Preview models (gemini-3.1-flash-lite-preview) experience frequent 503 outages. Cascading through multiple free-tier models (gemini-3-flash-preview → gemini-3.1-flash-lite-preview → gemma-4-31b-it → gemini-2.5-flash → gemini-2.5-flash-lite) maximizes reliability at zero cost. Each model gets 2 retries before fallback. Extractive summary is the final fallback.

## D-024
- Date: 2026-04-14
- Status: Accepted
- Decision: Each digest entry shows which model produced its summary (or notes it was not summarized).
- Rationale: Makes it immediately clear at a glance whether LLM summarization succeeded or fell back to extractive. Displayed as fine print below each summary in markdown, HTML email, and plaintext.

## D-025
- Date: 2026-04-15
- Status: Accepted
- Decision: Convert LaTeX notation to Unicode in email rendering using pylatexenc 2.x. Markdown output retains raw LaTeX (renders natively in GitHub/VS Code). Bare `%` is pre-escaped to prevent pylatexenc from treating it as a LaTeX comment.
- Rationale: arXiv titles and abstracts contain LaTeX math ($\beta$, $\frac{1}{2}$, etc.) that email clients cannot render. pylatexenc is pure Python, zero runtime deps, ~137 KB, and handles the 90%+ case for arXiv metadata. Conversion applied at render time via _EntryProxy so raw data is preserved in the database.

## D-026
- Date: 2026-04-29
- Status: Superseded by D-031 (exit-75 path broadened beyond 429; the "30 min once / timeout 75" figures are historical — the workflow later moved to two retries / 150 min)
- Decision: Two-layer arXiv 429 handling: (a) in-process exponential backoff with jitter (30s→480s cap, 7 attempts, honors Retry-After) plus 0–10s startup jitter; (b) workflow-level retry — a persistent 429 makes the CLI exit 75 (EX_TEMPFAIL), the workflow sleeps 30 min and re-runs once. Workflow `timeout-minutes` bumped to 75.
- Rationale: arXiv is fronted by Fastly, which throttles shared GH Actions egress IPs and the rate-limit decision can persist longer than any in-process backoff can practically absorb (observed 5+ min sticky throttle). A second attempt 30 min later usually lands on a different runner or after the throttle clears; the typed exit code keeps non-rate-limit failures from triggering long sleeps.

## D-027
- Date: 2026-05-11
- Status: Accepted
- Decision: Migrated position 2 of the fallback chain from `gemini-3.1-flash-lite-preview` to GA `gemini-3.1-flash-lite`.
- Rationale: Per the Gemini API changelog, `gemini-3.1-flash-lite-preview` is deprecating on 2026-05-11 and shutting down on 2026-05-25. The GA `gemini-3.1-flash-lite` (released 2026-05-07) is the drop-in successor — same `generateContent` API, same family, expected to be more reliable than the preview (D-023 noted frequent 503s on the preview). Supersedes the preview reference in D-023.

## D-028
- Date: 2026-05-11
- Status: Accepted
- Decision: Maintain both `CHANGELOG.md` (what changed, per-version, user-facing) and `docs/DECISIONS.md` (why, by topic, contributor-facing). Each new version bump adds a terse `CHANGELOG.md` entry cross-referencing the relevant D-NNN where applicable.
- Rationale: They answer different questions and serve different audiences. Forkers want a quick "what's new in 0.1.7"; contributors want the rationale and trade-offs. Conflating them either bloats the changelog or hides version history inside ADRs.

## D-029
- Date: 2026-05-20
- Status: Accepted
- Decision: Add GA `gemini-3.5-flash` (released 2026-05-19) at position 1 of the fallback chain. Keep `gemini-2.5-flash` and `gemini-2.5-flash-lite` in the chain even though both have a 2026-10-16 shutdown date; the drift checker (D-030) will surface the cutover. Final order: `gemini-3.5-flash → gemini-3-flash-preview → gemini-3.1-flash-lite → gemma-4-31b-it → gemini-2.5-flash → gemini-2.5-flash-lite`. Supersedes the chain documented in D-023 and D-027.
- Rationale: Per Google's I/O 2026 announcement, 3.5-flash outperforms Gemini 3.1 Pro on coding/agentic benchmarks at 4× the speed and is free-tier eligible. Putting it first maximizes summary quality without affecting the existing fallback behavior. The deprecating 2.5 models still work today; removing them now would shorten the chain unnecessarily.

## D-030
- Date: 2026-05-20
- Status: Accepted
- Decision: Add `research-digest check-models` CLI command and a weekly GitHub Actions cron (`.github/workflows/check-models.yml`) that calls Google's ListModels endpoint and diffs the response against `MODEL_CHAIN`. The check reports (a) chain models missing from the live API (retired), (b) newer family-mates not yet in the chain (e.g., `gemini-3.6-flash` or `gemini-3.5-flash-002`), and (c) the full remote inventory. Drift causes the workflow to exit non-zero so GitHub auto-emails the repo owner.
- Rationale: The Gemini API ships new models at high cadence (3 new GA models in the last 6 weeks alone) and deprecates older ones on rolling dates. Manual monitoring is unreliable. A weekly automated diff catches both arrivals and departures with zero ongoing cost — the ListModels endpoint is free and unauthenticated beyond the existing `GEMINI_API_KEY`. We do not auto-update the chain because model promotion is a quality-sensitive decision that should stay human-in-the-loop.

## D-031
- Date: 2026-06-01
- Status: Accepted
- Decision: Broaden the retry-worthy exit-75 path to cover *all* exhausted transient arXiv failures, not just persistent 429. The fetcher raises a typed `ArxivTransientError` (renamed from `ArxivRateLimitError`) when any retryable condition persists after all in-process attempts: any 5xx (incl. 503), 406, 408, 429, or an exhausted network error (`ConnectError`/`ReadTimeout`). A single `_is_retryable_status()` predicate is now shared by the in-loop retry decision and the post-exhaustion classification so the two cannot drift. The CLI maps `ArxivTransientError` → exit 75; the workflow's existing sleep-and-retry (30 min, then 60 min; up to 3 attempts; `timeout-minutes: 150`) then engages. Supersedes the 429-only scoping in D-026.
- Rationale: The 2026-06-01 manual digest run failed because arXiv's Fastly/Varnish CDN returned **503** on the final in-process attempt (after a run of 429s). The old code escalated only a final-status 429 to exit 75; a final 503 fell through to a generic exit 1, so the workflow's `if [ "$rc" -ne 75 ]` gave up after a single ~27-min in-process cycle instead of retrying on a fresh runner. 429 and 5xx from the shared CI egress IP are the same transient throttle/overload class and warrant identical handling — and the in-loop retry set already treated them identically, so the narrower final classification was simply an inconsistency that defeated the workflow safety net. The rename keeps the typed exception honest now that it no longer means "rate limit" specifically.

## D-032
- Date: 2026-06-01
- Status: Accepted
- Decision: Make the **scheduled** workflows' runner selectable via one repository variable — `runs-on: ${{ vars.AUTOMATION_RUNNER || 'ubuntu-latest' }}` in both `.github/workflows/digest.yml` and `.github/workflows/check-models.yml`, so they move together. Unset (the default, and what every fork sees) → GitHub-hosted `ubuntu-latest`; set to a self-hosted runner's label (default `self-hosted`) → the owner's always-on self-hosted runner. `scripts/runner.sh {local|github|status}` wraps the `gh variable set/delete` toggle. CI `tests.yml` is deliberately **excluded** (stays `ubuntu-latest`). Full how-to + security notes in `docs/RUNNER.md`. Also bumped `actions/upload-artifact@v5 → @v6` (first major tag on Node 24; the Node-20 runtime is being forced off on 2026-06-16).
- Rationale: D-031's in-workflow retries only *soften* arXiv throttling because the root cause is the **shared** GitHub-hosted egress IP (contended by the whole CI swarm); the throttle trends worse over time. Running the same workflow on a self-hosted runner with an un-throttled IP sidesteps it entirely while reusing all existing machinery (secrets, retry logic, email, logs). The variable indirection gives a one-command switch and keeps a single scheduler (GitHub cron) in charge, so there is exactly one run → one email regardless of setting — no double-send. Default-to-hosted preserves the public repo's out-of-the-box behavior for forks. Chosen over: (a) a second local scheduler (launchd) — would need GitHub's cron disabled and risks double-sends; (b) hardcoding a self-hosted label — scheduled jobs would hang when the box is offline and would break forks (no matching runner). Accepted trade-off: when the variable points at the self-hosted label and the runner is offline, scheduled runs queue rather than auto-falling-back, so the owner flips back to `github` before downtime. Safe on a public repo because the scheduled workflows have no `pull_request` trigger, so a forked PR can never execute on the self-hosted runner; `tests.yml` (which *does* run on fork PRs) is kept off the switch and always GitHub-hosted for exactly that reason.

---

## Instructions for future updates

When Claude makes or changes an architectural or product decision, it should:
1. add a new decision entry or update the relevant one
2. avoid silently changing an accepted decision
3. update related docs if the decision affects them