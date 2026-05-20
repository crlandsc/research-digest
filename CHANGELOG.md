# Changelog

Notable changes per release. Rationale lives in [docs/DECISIONS.md](docs/DECISIONS.md).

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
