# Current State

## Current milestone
Milestone 5 — complete. All core features implemented and deployed.

## Completed
- M0: documentation scaffold
- M1: project scaffold (pyproject.toml, config, CLI, README quickstart)
- M2: ingest and persistence (arXiv fetcher, SQLite, deduplication)
- M3: ranking and digest generation (scoring, filters, Markdown renderer)
- M4: usability hardening (CLI ergonomics, status command, edge case tests)
- M5: LLM summarization (5-model fallback chain: Gemini 3.8 Flash → 3.7 Flash → 3.5 Flash Lite → 3.1 Flash Lite → Gemma 4 31B; D-035)
- M5: model-drift checker (weekly diff of MODEL_CHAIN against live ListModels API, dispatched by the digest; D-030/D-036)
- M5: email delivery (Gmail SMTP with newsletter-style HTML)
- M5: topic grouping (papers grouped by keyword category in email)
- M5: resource links (Code, Model, Demo, Dataset, Colab from arXiv comment/abstract)
- M5: summary attribution (model name shown per entry in digest)
- M5: thinking model support (filters thought parts from Gemini 3 / Gemma 4 responses)
- M5: scheduling (externally dispatched weekdays at 12:00 UTC; GitHub cron removed in D-034)
- M5: CI workflow (tests run on every push to main)
- M5: LaTeX-to-Unicode conversion (pylatexenc converts math notation in email titles/summaries)
- M5: timeout fallback fix (timeouts continue chain instead of skipping to extractive)
- 230 tests all passing

## Working commands
- `research-digest run` — full pipeline (fetch + rank + build)
- `research-digest run --send-email` — run + email delivery
- `research-digest run --since-last-run` — fetch only new papers
- `research-digest send` — send most recent digest via email
- `research-digest status` — show DB stats and last run
- `research-digest fetch --dry-run` — preview query

## Automated delivery
- GitHub Actions: `.github/workflows/digest.yml`
- Schedule: weekdays ~12:00 UTC, fired by an external OS timer calling `gh workflow run digest.yml` (D-034). No GitHub `schedule:` cron
- Monday: 3-day lookback (covers weekend)
- Tue-Fri: 1-day lookback
- Secrets: GEMINI_API_KEY, GMAIL_APP_PASSWORD, EMAIL_FROM, EMAIL_TO
- Runner: both scheduled workflows (digest + check-models) selectable via the `AUTOMATION_RUNNER` repo var — default GitHub-hosted `ubuntu-latest`; set to a self-hosted label to run on an always-on box with an un-throttled IP. Toggle with `scripts/runner.sh {local|github|status}`. CI `tests.yml` always stays GitHub-hosted (fork-PR safety). See `docs/RUNNER.md` + D-032 (escapes the shared-CI-IP throttling that D-031 only softens)
- **Current runner (2026-09-24): GitHub-hosted.** `AUTOMATION_RUNNER` is unset. arXiv's CDN sent the Mac Mini a 406 on every request from 2026-09-18 until the penalty expired on its own at about 13:56 EDT on 2026-09-24 (MS-007). Staying on GitHub-hosted through at least the 2026-09-25 run; the Mac Mini still triggers the digest. To move back: send one probe from the Mac Mini, then `scripts/runner.sh local` (D-037, D-038)

### Known GitHub Actions cron limitations
- Scheduled runs can be delayed 10-60+ minutes during high load ([docs](https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows#schedule))
- Jobs scheduled at the top of the hour (:00) are most affected; we use :37/:47 offsets to reduce this
- Missed jobs may not be retried ([discussion](https://github.com/orgs/community/discussions/27130))
- Scheduled workflows are auto-disabled after 60 days of no repo activity on public repos. **This bit us on 2026-07-27**: `check-models.yml` was the last workflow on a `schedule:` cron and GitHub warned it would be disabled ~2026-07-31. Now mitigated - neither workflow uses `schedule:` (D-034, D-036)
- If a digest doesn't arrive, trigger manually from the Actions tab

### arXiv transient-failure handling (rate-limit / 5xx / network)
- arXiv's Fastly/Varnish CDN throttles (429) and overloads (503) shared CI egress IPs; the window can persist many minutes
- In-process: exponential backoff with jitter (~30s, 60s, 120s, 240s, 480s cap), 7 attempts; honors Retry-After. Retryable set: any 5xx, 406, 408, 429, plus ConnectError/ReadTimeout. A 406 (CDN block) or 429 (rate limit) gets only 3 attempts, so a persistent penalty reaches the workflow's cool-down retry fast (D-037, D-038)
- Initial 0-10s startup jitter to desync from other Actions cron jobs at :05
- Persistent transient failure (any retryable status — incl. 503 — or exhausted network error) → typed `ArxivTransientError` → CLI exits 75 (EX_TEMPFAIL) → workflow retries up to 2 more times with 30 min then 60 min sleeps (fresh runner / cleared throttle) (D-031)
- A single `_is_retryable_status()` predicate drives both the in-loop retry and the exit-75 classification so they cannot drift (the 2026-06-01 failure was a final-attempt 503 mis-routed to exit 1)
- Workflow timeout 150 min to accommodate three attempts. Known gap: a persistent 5xx can still overrun it, and the run ends *cancelled* (no failure email) rather than *failed* (D-038)

## Remaining
- [ ] Source adapters for ISMIR, TISMIR, DCASE, MIREX, ICASSP, TASLP (deferred)

## Last updated
2026-09-24 - the Mac Mini's 406 block expired on its own at about 13:56 EDT (MS-007 resolved). A persistent 429 now also gets only 3 in-process attempts, since the 9/14-15 retry storm likely escalated into that block (D-038). Corrected D-037: the MacBook probes went through a TLS-intercepting sandbox proxy, and the workflow's curl HEAD check is not a reliable health signal
2026-09-24 - digests silently missed 9/18-9/24: arXiv's CDN sent the Mac Mini a 406 on every request, and the retry budget overran the job timeout, so runs were cancelled with no failure email. Moved scheduled automation to GitHub-hosted runners (catch-up run succeeded: https://github.com/crlandsc/research-digest/actions/runs/36021616143), limited 406 to 3 in-process attempts, fixed `runner.sh status`. Mac Mini diagnosis is open as MS-007. Separately, that run's Gemini chain returned 503/429/500 on every model, so 19 of 20 summaries fell back to extractive. Not yet investigated
2026-09-03 — refreshed the Gemini chain Flash pair to 3.8 Flash and 3.7 Flash, dropping 3.6 Flash and 3.5 Flash; Lite entries and Gemma stay. Chain shape unchanged (2 Flash + 2 Lite + Gemma; D-035)
2026-08-04 — Mac Mini self-hosted runner DNS hardened (router DHCP → 1.1.1.1/8.8.8.8 on Ethernet/Wi-Fi/USB LAN; powernap off). Checkout `Could not resolve host: github.com` was intermittent host DNS, not digest code. Verified live digest on `Mac-mini`: https://github.com/crlandsc/research-digest/actions/runs/30958408038 (CHRIS-340)
2026-07-27 — refreshed the Gemini chain to five GA models (3.6 Flash lead; dropped the 3-flash preview and both 2.5 models, which shut down 2026-10-16), dropped the deprecated `temperature` param, moved the API key from `?key=` to the `x-goog-api-key` header, and added a log line when summaries fall back to extractive (see D-035)
2026-07-27 — removed the last GitHub `schedule:` cron: `check-models.yml` is now dispatched by a Mondays-only job in `digest.yml`, because GitHub auto-disables scheduled workflows after 60 days of repo inactivity on public repos and had warned this one would be disabled ~2026-07-31 (see D-036)
2026-06-01 — moved the daily digest off GitHub's `schedule:` cron to an external OS timer calling `gh workflow run digest.yml`, since scheduled events were firing hours late (see D-034)
2026-06-01 — fixed scheduled automation on the self-hosted macOS runner: `actions/setup-python` needs passwordless sudo there, so both workflows now build a venv from the runner's pre-installed Python 3.12 on that platform only (see D-033)
2026-06-01 — added a selectable runner for all scheduled automation (`AUTOMATION_RUNNER` repo var + `scripts/runner.sh`) covering digest + check-models, so they can run on a self-hosted runner with an un-throttled IP; default stays GitHub-hosted and CI tests always do. Bumped `actions/upload-artifact@v5 → @v6` (Node 24). (see D-032)
2026-06-01 — fixed transient-failure exit-code routing: a final-attempt arXiv 503 (and exhausted network errors) now raise typed `ArxivTransientError` → exit 75 → workflow retry, instead of exit 1 / give-up. Renamed `ArxivRateLimitError` → `ArxivTransientError` (see D-031)
2026-05-20 — added GA `gemini-3.5-flash` (released 2026-05-19) at position 1 of chain; added drift-checker CLI + weekly cron (see D-029, D-030)
