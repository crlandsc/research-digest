# Current State

## Current milestone
Milestone 5 — complete. All core features implemented and deployed.

## Completed
- M0: documentation scaffold
- M1: project scaffold (pyproject.toml, config, CLI, README quickstart)
- M2: ingest and persistence (arXiv fetcher, SQLite, deduplication)
- M3: ranking and digest generation (scoring, filters, Markdown renderer)
- M4: usability hardening (CLI ergonomics, status command, edge case tests)
- M5: LLM summarization (5-model fallback chain: Gemini 3 Flash → 3.1 Flash Lite → Gemma 4 31B → 2.5 Flash → 2.5 Flash Lite)
- M5: email delivery (Gmail SMTP with newsletter-style HTML)
- M5: topic grouping (papers grouped by keyword category in email)
- M5: resource links (Code, Model, Demo, Dataset, Colab from arXiv comment/abstract)
- M5: summary attribution (model name shown per entry in digest)
- M5: thinking model support (filters thought parts from Gemini 3 / Gemma 4 responses)
- M5: scheduling (GitHub Actions weekday cron at 7am ET)
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
- Schedule: weekdays 11:07 UTC (~7:07am EDT / ~6:07am EST)
- Monday: 3-day lookback (covers weekend)
- Tue-Fri: 1-day lookback
- Secrets: GEMINI_API_KEY, GMAIL_APP_PASSWORD, EMAIL_FROM, EMAIL_TO

### Known GitHub Actions cron limitations
- Scheduled runs can be delayed 10-60+ minutes during high load ([docs](https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows#schedule))
- Jobs scheduled at the top of the hour (:00) are most affected; we use :05 offset to reduce this
- Missed jobs may not be retried ([discussion](https://github.com/orgs/community/discussions/27130))
- Scheduled workflows are auto-disabled after 60 days of no repo activity on public repos
- If a digest doesn't arrive, trigger manually from the Actions tab

### arXiv rate-limit (HTTP 429) handling
- arXiv's Fastly CDN throttles shared CI egress IPs; the rate-limit window can persist many minutes
- In-process: exponential backoff with jitter (~30s, 60s, 120s, 240s, 480s cap), 7 attempts; honors Retry-After
- Initial 0-10s startup jitter to desync from other Actions cron jobs at :05
- Persistent 429 → CLI exits 75 (EX_TEMPFAIL) → workflow retries up to 2 more times with 30 min then 60 min sleeps (fresh runner / cleared throttle)
- Workflow timeout 150 min to accommodate three attempts

## Remaining
- [ ] Source adapters for ISMIR, TISMIR, DCASE, MIREX, ICASSP, TASLP (deferred)

## Last updated
2026-04-29
