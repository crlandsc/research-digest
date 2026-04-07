# PROJECT_BRIEF.md

## Project Name
Working title: `research-digest`

## Project Summary
Build a small, bespoke, low-maintenance system that produces a personalized digest of newly published arXiv papers.

This is a single-user or very small-scale personal project, not a product platform.

The system should:
- fetch recent arXiv papers from configured categories,
- apply deterministic topic filters,
- use an LLM only after prefiltering,
- rank papers for relevance,
- generate a clean digest,
- optionally enrich entries with code repository metadata when explicit links exist,
- deliver the result as files and by email,
- run automatically on GitHub Actions,
- remain easy to modify later without significant refactoring.

## Why this exists
The goal is to get a high-signal, low-noise research digest with minimal ongoing maintenance and minimal vendor lock-in.

The project should be:
- cheap to run,
- easy to tune through config,
- easy to extend later,
- robust when APIs fail,
- understandable by a human maintainer.

## Primary Design Principles
1. **Low upkeep beats cleverness**
2. **Configuration beats hard-coded business logic**
3. **Deterministic filtering before LLM scoring**
4. **Swappable provider interfaces**
5. **Graceful degradation when optional services fail**
6. **No always-on infrastructure**
7. **No inheritance from a large prebuilt digest codebase**
8. **Clean module boundaries**
9. **Reproducible outputs and good run artifacts**
10. **Single-user simplicity over platform generality**

## Important Non-Goal
This should **not** be built as a long-term fork of `ArxivDigest-extra`.

It is acceptable to consult that project for inspiration, but this repository should be a clean bespoke implementation with modular boundaries.

## V1 Scope
V1 should support:

### Sources
- arXiv only

### Ingestion
- Fetch recent papers from configured arXiv categories
- Support configurable lookback window
- Dedupe cross-listed papers by canonical arXiv ID
- Normalize paper metadata into internal models

### Filtering
- Config-driven topic definitions
- Include keywords / phrases
- Exclude keywords / phrases
- Category preferences
- Optional author boost / suppress lists
- Deterministic prefiltering before any LLM use

### LLM Assessment
- Default runtime provider: direct Gemini API
- Model should be configured in YAML, not hard-coded
- LLM should score only the narrowed candidate set
- Use structured outputs validated against a schema
- LLM should operate only on paper metadata available in the pipeline
- Do not fetch or analyze PDFs in v1
- Do not hallucinate facts not present in title/abstract/metadata

### Ranking
Generate a final ranked list based on:
- deterministic rules score
- LLM relevance score
- LLM novelty score
- LLM practical usefulness score
- configurable weights

### Enrichment
Best-effort repository enrichment only.

V1 enrichment should:
- extract explicit URLs from available paper metadata,
- keep GitHub links when present,
- fetch public GitHub metadata for discovered repos,
- show repo URL, stars, license, and last-updated date when available.

V1 should **not** do fuzzy GitHub searching or complicated repo discovery that risks false positives and maintenance overhead.

If no explicit repo is found, leave repo fields empty.

### Output
Generate:
- `digest.html`
- `digest.md`
- `digest.txt`
- machine-readable run artifacts (JSON)

Digest should include:
- run date
- short executive summary
- top picks section
- watchlist section
- per-paper short summary / takeaway
- topic tags or matched topics
- repository info when available
- links to arXiv / PDF / repo when available
- footer with basic run metadata

### Delivery
V1 delivery channels:
- file output
- SMTP email

Email should send multipart output if practical:
- HTML body
- plain-text fallback

### Automation
- GitHub Actions scheduled workflow
- GitHub Actions manual workflow dispatch for dry run / backfill / rerun
- CI workflow for tests and linting
- Scheduled run should upload artifacts

### State
Persist enough state to support:
- avoiding duplicate sends,
- remembering last successful run,
- caching LLM assessments where appropriate,
- optionally caching repo metadata,
- cost/budget tracking,
- idempotent reruns.

Use a simple local state backend such as SQLite persisted via repository workflow strategy. No external database server.

### Docs / Usability
Need:
- README
- `.env.example`
- `config/user.yaml.example`
- `docs/configuration.md`
- `docs/operations.md`
- `docs/architecture.md`
- `docs/implementation_plan.md`

Also provide a CLI with at least:
- `doctor`
- `run`
- `backfill`
- `render` (optional if `run` already handles rendering)
- `send` (optional if `run` already handles sending)

## V1 Explicit Non-Goals
Do **not** build any of the following in v1:
- web UI
- dashboard
- login/auth
- user accounts
- team/multi-tenant support
- vector database
- embeddings-based semantic retrieval
- PDF full-text parsing
- citation graph analysis
- Slack/Notion/Zotero integrations
- a long list of LLM providers
- advanced repo discovery beyond explicit links
- heavy cloud infrastructure
- Docker-only workflows

## Recommended Default Stack
Use Python.

Suggested stack:
- Python 3.12+
- `pyproject.toml`
- `pydantic` for structured models/config validation
- `PyYAML` for config
- `httpx` for HTTP calls
- `jinja2` for rendering
- `typer` for CLI
- `tenacity` for retries
- `feedparser` or a simple XML parser for arXiv Atom feed parsing
- stdlib `sqlite3` for state
- stdlib `smtplib` / `email` for SMTP delivery
- `pytest` for tests
- `ruff` and `mypy` for code quality

Keep dependencies minimal. Prefer stdlib when reasonable.

## Recommended Module Boundaries
Use clear module boundaries similar to:

- `collectors/`
- `filters/`
- `providers/`
- `enrichment/`
- `ranking/`
- `renderers/`
- `delivery/`
- `state/`
- `services/`
- `utils/`

The exact names can vary, but the boundaries should remain clear.

## Desired Data Flow
1. Load config
2. Determine run window
3. Fetch arXiv entries
4. Normalize + dedupe
5. Apply deterministic filters
6. Limit candidate set
7. Score candidates with LLM
8. Enrich top included papers with explicit repo metadata
9. Rank and bucket into digest sections
10. Generate HTML/Markdown/Text outputs
11. Save artifacts
12. Send email if enabled
13. Update state
14. Emit run manifest

## Functional Requirements in More Detail

### Paper Normalization
Each normalized paper model should include fields like:
- arxiv_id
- version
- title
- authors
- abstract
- primary_category
- all_categories
- published_at
- updated_at
- abs_url
- pdf_url
- comment
- journal_ref
- doi
- links
- raw source metadata (optional for debugging)

### Topic Configuration
Topics must be config-driven and human-editable without code changes.

Each topic should be able to define:
- `id`
- `name`
- `description`
- `weight`
- `include_keywords`
- `exclude_keywords`
- `preferred_categories`
- optional `author_boost`
- optional `author_suppress`

### Deterministic Rules Scoring
Rules scoring should be transparent and explainable.

Minimum expected behavior:
- title matches count more than abstract matches
- excluded phrases penalize heavily or eliminate
- category preference contributes positively
- author boost/suppress is optional
- rules produce a normalized score and an explanation object

### LLM Scoring
LLM scoring should produce validated structured output with fields like:
- include / skip recommendation
- matched topics
- relevance score
- novelty score
- practical usefulness score
- confidence score
- one-sentence takeaway
- short reasons it matters
- short limitations / caution notes

The model should be instructed to:
- use only supplied metadata,
- avoid invented claims,
- be concise,
- be conservative if evidence is weak.

### Ranking
Use a configurable final weighted score.

Suggested concept:
- rules score
- LLM relevance
- LLM novelty
- LLM practicality
- optional confidence threshold

Allow the exact formula to live in config or a single obvious code location.

### Digest Format
Digest should contain:
- a short title/header
- summary stats
- executive summary
- top picks
- watchlist
- footer with run metadata

Per paper, show:
- title
- authors
- categories
- one-line takeaway
- why it matters
- notable limitation/caution
- arXiv link
- PDF link
- repo info if present

Tone should be practical, concise, and non-hypey.

### Run Artifacts
Each run should output artifacts such as:
- `manifest.json`
- `papers_raw.json`
- `papers_filtered.json`
- `papers_scored.json`
- `digest.html`
- `digest.md`
- `digest.txt`

These are important for debugging and future adjustments.

## Reliability / Failure Handling Requirements
The system should degrade gracefully.

Required behaviors:
- If LLM fails and rules-only fallback is enabled, still produce a digest with a clear note.
- If GitHub enrichment fails, continue without repo metadata.
- If email fails, preserve generated outputs and fail clearly.
- If no papers match, either send a short “no strong matches” digest or skip sending based on config.
- If the same run is triggered twice, it should not send duplicates by default.
- If last run was missed, support catch-up logic within a capped lookback.

## Cost / Budget Requirements
This project should stay cheap.

Required controls:
- configurable max number of LLM-scored candidates per run
- configurable monthly budget cap or token/cost limit
- cost logging or cost estimation per run
- option to fall back to rules-only mode if budget is exceeded

Do not build an elaborate billing system. Keep it simple.

## Scheduling Requirements
Use GitHub Actions schedule plus manual workflow dispatch.

Note:
GitHub Actions cron is UTC, so exact local-time delivery may drift by one hour around DST unless a more advanced gating strategy is used. Simplicity is preferred unless the human requests fixed local-time behavior.

## Expected Outputs from Planning Phase
Before implementation begins, produce:

1. `docs/implementation_plan.md`
2. a proposed file tree
3. chosen dependencies and rationale
4. a state strategy
5. a testing strategy
6. a manual setup checklist
7. open questions / assumptions
8. recommended defaults to reduce maintenance

Then stop and wait for approval.

## Quality Bar
The final repository should be:
- easy to read
- easy to run locally
- easy to deploy with GitHub Actions
- easy to tune through config
- easy to extend later without rewriting the core