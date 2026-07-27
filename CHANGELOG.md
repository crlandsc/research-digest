# Changelog

Notable changes per release. Rationale lives in [docs/DECISIONS.md](docs/DECISIONS.md).

## 0.1.11 — 2026-07-27
- Changed: refreshed the Gemini fallback chain to five GA models (`gemini-3.6-flash` → `gemini-3.5-flash` → `gemini-3.5-flash-lite` → `gemini-3.1-flash-lite` → `gemma-4-31b-it`), dropping `gemini-3-flash-preview` and both 2.5 models (shutdown 2026-10-16). Chain length 6 → 5, but durable depth improves: the old chain would have fallen to 4 entries in October, this one holds until 2027-05-07. Production logs show the chain buys availability rather than quota (three positions used on 2026-07-24, all failures 503s or timeouts, zero 429s ever), so the ordering now deliberately spans two serving tiers plus one non-Gemini family (D-035)
- Fixed: dropped the `temperature` sampling param, deprecated by Google on 2026-07-21 alongside `top_p`/`top_k`. Verified against the live API that `gemini-3.6-flash` ignores it outright, so this is a no-op rather than a change in summary style (D-035)
- Fixed: the Gemini API key now travels in an `x-goog-api-key` header instead of a `?key=` query param, matching `model_check.py`. httpx logs full request URLs at INFO and the digest runs `--verbose`, so the key was previously written to a log line on every call: masked as `***` in Actions, unmasked anywhere else. The init log line now prints a SHA-256 fingerprint instead of `api_key[:8]`, since `AIza` is a constant prefix on Gemini keys (D-035)
- Added: a summary log line when summaries fall back to extractive, at ERROR if every paper fell back and WARNING if only some did. Three layers of fallback meant a total Gemini outage previously produced a normal-looking digest and exit 0 with no signal at all (D-035)
- Changed: `check-models.yml` no longer uses GitHub's `schedule:` cron (left commented for forks). A new Mondays-only `dispatch-model-check` job in `digest.yml` dispatches it instead, reusing the external trigger already proven to fire within seconds daily. GitHub auto-disables scheduled workflows after 60 days of repo inactivity on public repos and had warned this one would be disabled ~2026-07-31; the cron was also firing 2-3.5 hours late every week. Needs no new timer and no work on the self-hosted box (D-036)
- Added: test coverage for the outgoing Gemini request, which was previously unobservable. The `post` mock only ever receives `json=`, so the URL, headers and payload could all regress while the suite stayed green. Includes a real-httpx wire-format test using `MockTransport`, and secret-hygiene tests asserting the key never reaches a log record. Behaviour tests moved to a synthetic chain fixture so they no longer break on every chain edit, and the status-table comment above `MODEL_CHAIN` is now enforced by a test. 209 → 226 tests
- Docs: corrected the test count (132 in ARCHITECTURE, 180 in STATE), added the missing `check-models.yml` entry to ARCHITECTURE, backfilled the D-033/D-034 entries STATE never recorded, replaced the stale MS-005 scheduling placeholder, and removed `DIGEST_OUTPUT_DIR` and `SUMMARY_MODE` from `env.example` since no code has ever read them (adding the live-but-undocumented `DATABASE_URL`)

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
