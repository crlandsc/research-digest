# Architecture

## Architectural intent

Build the smallest maintainable local-first system that can produce a useful research digest from arXiv without requiring paid services.

## Preferred stack

- Language: Python 3.12+
- Packaging: `pyproject.toml`
- Environment management: standard `venv` + `pip`
- CLI: Typer or Click
- HTTP: `httpx`
- Parsing: standard library XML or a lightweight feed parser (arXiv legacy Atom/XML API preferred over experimental REST API)
- Data validation: Pydantic if useful, but keep it lightweight
- Persistence: SQLite
- Testing: `pytest`
- Templates/rendering: plain string templates or Jinja2 if helpful

If Claude decides a different library is materially better, it may change the choice only if:
1. the change is documented in `docs/DECISIONS.md`
2. the architecture doc is updated to match

## Core design principles

1. local-first by default
2. reversible decisions where possible
3. modular pipeline
4. no external credentials required for the first useful version
5. deterministic ranking before optional LLM enhancement
6. documentation must remain accurate as the build evolves

## Preferred pipeline

```text
config -> fetch -> normalize -> store -> filter -> rank -> summarize -> render
```

Notes:
- `summarize` can initially be extractive and based on the abstract
- `render` should initially target Markdown
- later enhancements should fit into this pipeline without breaking the local-first path

## Suggested target repository structure

This is the preferred structure Claude should move toward when implementation begins:

```text
src/
  research_digest/
    __init__.py
    cli.py
    config.py
    models.py
    categories.py
    logging_config.py
    fetchers/
      __init__.py
      arxiv.py
    storage/
      __init__.py
      db.py
      repository.py
    pipeline/
      __init__.py
      fetch.py
      rank.py
      summarize.py
      build_digest.py
    summarization/
      __init__.py
      base.py
      extractive.py
      gemini.py
      providers.py
    delivery/
      __init__.py
      base.py
      gmail.py
    rendering/
      __init__.py
      markdown.py
      html_email.py

tests/
  conftest.py
  test_config.py
  test_arxiv_fetcher.py
  test_ranking.py
  test_storage.py
  test_digest_rendering.py
  test_summarization.py
  test_delivery.py
  test_pipeline_integration.py
  test_edge_cases.py
```

## Data model expectations

At minimum, the implementation should have a normalized concept of a paper containing:

- source
- external ID
- title
- authors
- abstract
- categories
- published_at
- updated_at
- canonical URL
- PDF URL if available
- ingest timestamp

The persistence layer should also support enough metadata to answer:
- when was this paper first seen?
- has it already been included in a digest?
- what score did it receive?
- what run generated this digest?

## Local storage

Preferred default:
- SQLite file under `data/`

Expected uses:
- deduplication
- caching fetched metadata
- tracking run history
- enabling reproducible digest generation

## CLI expectations

Preferred initial commands:

- `research-digest fetch`
- `research-digest rank`
- `research-digest build`
- `research-digest run`

A minimal alternative is acceptable if it is simpler, such as:
- `research-digest run`

If the command names change, update the docs.

## Output expectations

Preferred default output location:
- `output/<date>/digest.md`

Optional future outputs:
- JSON export
- HTML export
- email body generation

## Lookback modes

The tool supports two lookback strategies:

1. **N-day lookback** (default for manual runs): fetch papers from the last N days, configurable via `lookback_days` in the topic config.
2. **Since-last-run** (for automated/scheduled runs): fetch papers published since the last successful fetch, tracked via run history in the database.

Deduplication at the storage layer prevents overlap regardless of mode. The CLI should accept a flag to select the mode (default: N-day).

Note: arXiv's experimental REST API may offer better query capabilities in the future. The current implementation uses the stable legacy Atom/XML API. If the REST API matures, evaluate switching — document the decision.

## Ranking strategy

Initial ranking should be deterministic and simple, for example:
- keyword matches
- category matches
- recency
- duplicate suppression
- inclusion/exclusion filters

LLM-based ranking may be layered on later, but should not be required to get a working digest.

## Summarization strategy

Phase 1:
- extractive summary from title + abstract
- short rationale for why the paper was selected

Phase 2:
- optional provider-backed LLM summary
- controlled through env vars and configuration
- must remain optional

## Configuration strategy

Use:
- a local YAML file for topic and digest preferences
- environment variables for runtime or provider configuration

Expected config pattern:
- `config/topics.example.yaml` is committed
- `config/topics.yaml` is local and user-specific
- the app should fail clearly if the config file is missing, or optionally bootstrap from the example

## Error handling expectations

The system should fail clearly and helpfully when:
- config is missing or malformed
- arXiv fetch fails
- the database is unavailable
- no papers match the configured filters
- optional provider credentials are missing when an optional provider-backed feature is requested

## Testing expectations

Every code change must include corresponding tests. Tests are the primary safeguard against regressions.

**Test categories:**
- **Unit tests** — config loading, XML parsing, scoring, rendering (per-function)
- **Edge case tests** — unicode, missing fields, empty inputs, special characters
- **Integration tests** — full pipeline data flow (fetch → rank → build), verifying data survives DB roundtrips and pipeline stage boundaries
- **Summarization/delivery tests** — provider abstraction, mocked API calls, email rendering

**Rules:**
- All tests must be offline — no network, no API keys, no external services
- Use in-memory SQLite (`:memory:`), hardcoded XML fixtures, mocked HTTP calls
- Integration tests are the most critical — unit tests can pass while data is silently lost between stages
- Bug fixes must include a regression test that would have caught the bug
- CI runs all tests on every push to main (`.github/workflows/tests.yml`)

**Current coverage:**
- 132 tests across 8 test files
- `pytest` runs in <1 second

## Deployment

GitHub Actions handles deployment:
- `.github/workflows/digest.yml` — daily digest delivery (weekday cron)
- `.github/workflows/tests.yml` — CI tests on every push/PR to main

## External service posture

For current scope:
- arXiv is the only required external data source for the MVP
- no LLM provider should be required for first usefulness
- no email provider should be required for first usefulness

Planned source expansion, especially for music/audio AI/ML, may later include:
- ISMIR conference proceedings
- TISMIR
- DCASE workshop and challenge outputs
- MIREX evaluation results
- ICASSP proceedings
- IEEE/ACM TASLP

These sources should be added only after the arXiv-only local pipeline works end-to-end.

If a later implementation step requires consulting current provider docs or APIs, Claude should verify those at implementation time and then document the exact manual step in `docs/MANUAL_STEPS.md`.