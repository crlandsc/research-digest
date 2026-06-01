# Changelog

Notable changes per release. Rationale lives in [docs/DECISIONS.md](docs/DECISIONS.md).

## 0.1.10 — 2026-06-01
- Fixed: scheduled automation failed on a self-hosted **macOS** runner at "Set up Python" — `actions/setup-python`'s macOS installer runs `sudo installer` for the python.org `.pkg`, which needs passwordless sudo a self-hosted user typically lacks. `digest.yml` and `check-models.yml` now build a venv from the runner's pre-installed Python 3.12 on macOS self-hosted runners, while keeping `actions/setup-python` for GitHub-hosted and Linux self-hosted (D-033)
- Changed: the daily digest is now triggered by an external scheduler calling `gh workflow run` (workflow_dispatch) instead of GitHub's `schedule:` cron, which is heavily delayed under load; the `schedule:` block is removed from `digest.yml` (left commented for forks that prefer GitHub cron). `check-models.yml` keeps its weekly cron (D-034)

## 0.1.9 — 2026-06-01
- Fixed: a persistent arXiv 503 (or other 5xx, or an exhausted network error) on the final retry now exits 75 (EX_TEMPFAIL) so the workflow retries on a fresh runner, instead of exiting 1 and giving up after one in-process cycle. Renamed `ArxivRateLimitError` → `ArxivTransientError`; a shared `_is_retryable_status()` predicate keeps the in-loop retry decision and the post-exhaustion classification in sync (D-031)
- Added a selectable runner for all scheduled automation: set the `AUTOMATION_RUNNER` repo variable (via `scripts/runner.sh {local|github|status}`) to run the daily digest **and** the weekly model-check on a self-hosted runner with an un-throttled IP instead of GitHub's shared runners. Defaults to GitHub-hosted; CI tests always stay GitHub-hosted. See [docs/RUNNER.md](docs/RUNNER.md) (D-032)
- Bumped `actions/upload-artifact@v5 → @v6` (Node 20 runtime is forced off GitHub runners on 2026-06-16)

## 0.1.8 — 2026-05-20
- Added `gemini-3.5-flash` (GA 2026-05-19) at position 1 of the fallback chain; chain length 5 → 6 (D-029)
- New `research-digest check-models` CLI command + weekly cron that diffs `MODEL_CHAIN` against the live ListModels API and surfaces drift (D-030)

## 0.1.7 — 2026-05-11
- Migrated fallback chain from `gemini-3.1-flash-lite-preview` to GA `gemini-3.1-flash-lite` (D-027)

## 0.1.6 — 2026-04-29
- Two-layer arXiv 429 handling: in-process exponential backoff with jitter + workflow-level retry on EX_TEMPFAIL (D-026)

## 0.1.5 — 2026-04-16
- Retry on transient arXiv CDN errors; send `Accept` header

## 0.1.4 — 2026-04-15
- LaTeX-to-Unicode conversion in email rendering via pylatexenc (D-025)
- Timeout on one model now falls through to next model instead of skipping to extractive
- Public-sharing prep: MIT license, generic topics template, README rewrite

## 0.1.3 — 2026-04-14
- 5-model Gemini/Gemma fallback chain with thinking-part filtering and per-entry summary attribution (D-023, D-024)
- Cron shift to 10:05 UTC to absorb GitHub Actions scheduling delays

## 0.1.2 — 2026-04-09
- Single version source: hatch reads `__init__.py`
- Switched LLM to `gemini-3.1-flash-lite-preview` (later superseded in 0.1.7)
- Increased Gemini inter-request delay to 7s

## 0.1.1 — 2026-04-08
- Resource link extraction from arXiv comment/abstract: Code, Model, Demo, Dataset, Colab

## 0.1.0 — 2026-04-08
- Initial release: arXiv fetch, SQLite persistence + dedup, ranking, Markdown digest, Gmail SMTP delivery, extractive summaries
