# Current State

## Current milestone
Milestone 5 — complete. All core features implemented and deployed.

## Completed
- M0: documentation scaffold
- M1: project scaffold (pyproject.toml, config, CLI, README quickstart)
- M2: ingest and persistence (arXiv fetcher, SQLite, deduplication)
- M3: ranking and digest generation (scoring, filters, Markdown renderer)
- M4: usability hardening (CLI ergonomics, status command, edge case tests)
- M5: LLM summarization (6-model fallback chain: Gemini 3.5 Flash → 3 Flash → 3.1 Flash Lite → Gemma 4 31B → 2.5 Flash → 2.5 Flash Lite)
- M5: model-drift checker (weekly cron diffs MODEL_CHAIN against live ListModels API)
- M5: email delivery (Gmail SMTP with newsletter-style HTML)
- M5: topic grouping (papers grouped by keyword category in email)
- M5: resource links (Code, Model, Demo, Dataset, Colab from arXiv comment/abstract)
- M5: summary attribution (model name shown per entry in digest)
- M5: thinking model support (filters thought parts from Gemini 3 / Gemma 4 responses)
- M5: scheduling (GitHub Actions weekday cron at ~5:37am ET)
- M5: CI workflow (tests run on every push to main)
- M5: LaTeX-to-Unicode conversion (pylatexenc converts math notation in email titles/summaries)
- M5: timeout fallback fix (timeouts continue chain instead of skipping to extractive)
- 180 tests all passing

## Working commands
- `research-digest run` — full pipeline (fetch + rank + build)
- `research-digest run --send-email` — run + email delivery
- `research-digest run --since-last-run` — fetch only new papers
- `research-digest send` — send most recent digest via email
- `research-digest status` — show DB stats and last run
- `research-digest fetch --dry-run` — preview query

## Automated delivery
- GitHub Actions: `.github/workflows/digest.yml`
- Schedule: weekdays 9:37 UTC (~5:37am EDT / ~4:37am EST)
- Monday: 3-day lookback (covers weekend)
- Tue-Fri: 1-day lookback
- Secrets: GEMINI_API_KEY, GMAIL_APP_PASSWORD, EMAIL_FROM, EMAIL_TO
- Runner: both scheduled workflows (digest + check-models) selectable via the `AUTOMATION_RUNNER` repo var — default GitHub-hosted `ubuntu-latest`; set to a self-hosted label to run on an always-on box with an un-throttled IP. Toggle with `scripts/runner.sh {local|github|status}`. CI `tests.yml` always stays GitHub-hosted (fork-PR safety). See `docs/RUNNER.md` + D-032 (escapes the shared-CI-IP throttling that D-031 only softens)

### Known GitHub Actions cron limitations
- Scheduled runs can be delayed 10-60+ minutes during high load ([docs](https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows#schedule))
- Jobs scheduled at the top of the hour (:00) are most affected; we use :37/:47 offsets to reduce this
- Missed jobs may not be retried ([discussion](https://github.com/orgs/community/discussions/27130))
- Scheduled workflows are auto-disabled after 60 days of no repo activity on public repos
- If a digest doesn't arrive, trigger manually from the Actions tab

### arXiv transient-failure handling (rate-limit / 5xx / network)
- arXiv's Fastly/Varnish CDN throttles (429) and overloads (503) shared CI egress IPs; the window can persist many minutes
- In-process: exponential backoff with jitter (~30s, 60s, 120s, 240s, 480s cap), 7 attempts; honors Retry-After. Retryable set: any 5xx, 406, 408, 429, plus ConnectError/ReadTimeout
- Initial 0-10s startup jitter to desync from other Actions cron jobs at :05
- Persistent transient failure (any retryable status — incl. 503 — or exhausted network error) → typed `ArxivTransientError` → CLI exits 75 (EX_TEMPFAIL) → workflow retries up to 2 more times with 30 min then 60 min sleeps (fresh runner / cleared throttle) (D-031)
- A single `_is_retryable_status()` predicate drives both the in-loop retry and the exit-75 classification so they cannot drift (the 2026-06-01 failure was a final-attempt 503 mis-routed to exit 1)
- Workflow timeout 150 min to accommodate three attempts

## Remaining
- [ ] Source adapters for ISMIR, TISMIR, DCASE, MIREX, ICASSP, TASLP (deferred)

## Last updated
2026-06-01 — added a selectable runner for all scheduled automation (`AUTOMATION_RUNNER` repo var + `scripts/runner.sh`) covering digest + check-models, so they can run on a self-hosted runner with an un-throttled IP; default stays GitHub-hosted and CI tests always do. Bumped `actions/upload-artifact@v5 → @v6` (Node 24). (see D-032)
2026-06-01 — fixed transient-failure exit-code routing: a final-attempt arXiv 503 (and exhausted network errors) now raise typed `ArxivTransientError` → exit 75 → workflow retry, instead of exit 1 / give-up. Renamed `ArxivRateLimitError` → `ArxivTransientError` (see D-031)
2026-05-20 — added GA `gemini-3.5-flash` (released 2026-05-19) at position 1 of chain; added drift-checker CLI + weekly cron (see D-029, D-030)
