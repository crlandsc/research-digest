# Current State

## Current milestone
Milestone 5 — mostly complete. LLM summarization, email, and scheduling done.

## Completed
- M0: documentation scaffold
- M1: project scaffold (pyproject.toml, config, CLI, README quickstart)
- M2: ingest and persistence (arXiv fetcher, SQLite, deduplication)
- M3: ranking and digest generation (scoring, filters, Markdown renderer)
- M4: usability hardening (CLI ergonomics, status command, 17 edge case tests)
- M5: LLM summarization (Gemini Flash provider with abstraction)
- M5: email delivery (Gmail SMTP with HTML renderer)
- M5: scheduling (GitHub Actions weekday cron, smart lookback)
- 110 tests all passing

## Working commands
- `research-digest run` — full pipeline (fetch + rank + build)
- `research-digest run --send-email` — run + email delivery
- `research-digest run --since-last-run` — fetch only new papers
- `research-digest send` — send most recent digest via email
- `research-digest status` — show DB stats and last run
- `research-digest fetch --dry-run` — preview query

## Automated delivery
- GitHub Actions: `.github/workflows/digest.yml`
- Schedule: weekdays 12:00 UTC (8am EDT)
- Monday: 3-day lookback (covers weekend)
- Tue-Fri: 1-day lookback
- Secrets required: GEMINI_API_KEY, GMAIL_APP_PASSWORD, EMAIL_FROM, EMAIL_TO

## Remaining
- [ ] Source adapters for ISMIR, TISMIR, DCASE, MIREX, ICASSP, TASLP (deferred)

## Last updated
2026-04-08
