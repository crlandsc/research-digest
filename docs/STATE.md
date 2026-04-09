# Current State

## Current milestone
Milestone 5 — complete. All core features implemented and deployed.

## Completed
- M0: documentation scaffold
- M1: project scaffold (pyproject.toml, config, CLI, README quickstart)
- M2: ingest and persistence (arXiv fetcher, SQLite, deduplication)
- M3: ranking and digest generation (scoring, filters, Markdown renderer)
- M4: usability hardening (CLI ergonomics, status command, edge case tests)
- M5: LLM summarization (Gemini 2.5 Flash Lite via provider abstraction)
- M5: email delivery (Gmail SMTP with newsletter-style HTML)
- M5: topic grouping (papers grouped by keyword category in email)
- M5: resource links (Code, Model, Demo, Dataset, Colab from arXiv comment/abstract)
- M5: scheduling (GitHub Actions weekday cron at 8am ET)
- M5: CI workflow (tests run on every push to main)
- 132 tests all passing

## Working commands
- `research-digest run` — full pipeline (fetch + rank + build)
- `research-digest run --send-email` — run + email delivery
- `research-digest run --since-last-run` — fetch only new papers
- `research-digest send` — send most recent digest via email
- `research-digest status` — show DB stats and last run
- `research-digest fetch --dry-run` — preview query

## Automated delivery
- GitHub Actions: `.github/workflows/digest.yml`
- Schedule: weekdays 12:05 UTC (~8:05am EDT / ~7:05am EST)
- Monday: 3-day lookback (covers weekend)
- Tue-Fri: 1-day lookback
- Secrets: GEMINI_API_KEY, GMAIL_APP_PASSWORD, EMAIL_FROM, EMAIL_TO

### Known GitHub Actions cron limitations
- Scheduled runs can be delayed 10-60+ minutes during high load ([docs](https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows#schedule))
- Jobs scheduled at the top of the hour (:00) are most affected; we use :05 offset to reduce this
- Missed jobs may not be retried ([discussion](https://github.com/orgs/community/discussions/27130))
- Scheduled workflows are auto-disabled after 60 days of no repo activity on public repos
- If a digest doesn't arrive, trigger manually from the Actions tab

## Remaining
- [ ] Source adapters for ISMIR, TISMIR, DCASE, MIREX, ICASSP, TASLP (deferred)

## Last updated
2026-04-08
