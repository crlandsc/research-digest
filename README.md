# research-digest

A local-first tool that fetches recent arXiv papers, ranks them by relevance to your configured interests, and delivers a concise email digest with LLM-generated summaries. Papers are grouped by topic for easy scanning.

Built for personal use but designed to be reusable. The default configuration targets music/audio AI/ML research, but it works for any arXiv domain by changing the config file.

## Features

- Fetches papers from arXiv based on categories and keyword queries
- Scores and ranks papers using a deterministic point system
- Generates concise newsletter-style summaries via Google Gemini (free tier)
- Groups papers by topic in a clean HTML email
- Delivers automatically on weekday mornings via GitHub Actions
- Works locally as a CLI with no required API keys (LLM and email are optional)

## Quickstart

### Prerequisites

- Python 3.12+
- [pyenv](https://github.com/pyenv/pyenv) with pyenv-virtualenv (recommended) or standard `venv`

### Install

```bash
git clone https://github.com/crlandsc/research-digest.git
cd research-digest

# Option A: pyenv-virtualenv
pyenv virtualenv 3.12.12 research-digest
pyenv local research-digest

# Option B: standard venv
python3 -m venv .venv && source .venv/bin/activate

# Install
pip install -e ".[dev]"
```

### Configure

```bash
cp config/topics.example.yaml config/topics.yaml
```

Edit `config/topics.yaml` to match your interests:
- **categories** — arXiv category codes (e.g., `cs.SD`, `cs.LG`, `eess.AS`)
- **keyword_queries** — search phrases (combined with categories via AND)
- **keyword_groups** — maps keywords to named topic sections in the digest
- **excluded_keywords** — papers matching these are filtered out (e.g., "survey")
- **lookback_days** — how far back to fetch (default: 7)
- **max_candidates_for_digest** — max papers per digest (default: 20)

See `config/topics.example.yaml` for a full annotated example with comments.

### Run locally

```bash
# Full pipeline: fetch, rank, generate Markdown digest
research-digest run

# Preview the arXiv query without fetching
research-digest fetch --dry-run

# Override lookback window
research-digest run --lookback-days 14

# Check database status
research-digest status
```

Output is written to `output/<YYYY-MM-DD>/digest.md`.

### Run tests

```bash
pytest          # 112 tests
```

## Optional: LLM summaries

By default, the digest uses the first few sentences of each abstract. To get concise, newsletter-style summaries via Google Gemini (free):

1. Get a free API key at [Google AI Studio](https://aistudio.google.com/apikey)
2. Create a `.env` file from the template: `cp env.example .env`
3. Add your key to `.env`: `GEMINI_API_KEY=your_key_here`
4. Set `summarization.mode: llm` and `summarization.provider: gemini` in `config/topics.yaml`

## Optional: Email delivery

To receive the digest via email:

1. Create a [Gmail App Password](https://myaccount.google.com/apppasswords) (requires 2FA)
2. Add to `.env`:
   ```
   EMAIL_FROM=you@gmail.com
   EMAIL_TO=you@gmail.com
   GMAIL_APP_PASSWORD=your_16_char_password
   ```
3. Run with email: `research-digest run --send-email`

## Optional: Automated daily delivery

The included GitHub Actions workflow delivers the digest every weekday morning:

1. Push this repo to GitHub
2. Add repository secrets (Settings > Secrets > Actions):
   - `GEMINI_API_KEY`
   - `GMAIL_APP_PASSWORD`
   - `EMAIL_FROM`
   - `EMAIL_TO`
3. The workflow runs at 8am ET Mon-Fri automatically
   - Monday covers Saturday + Sunday (3-day lookback)
   - Tuesday-Friday covers the previous day (1-day lookback)
4. You can also trigger manually from the Actions tab

## How it works

1. **Fetch** — queries the arXiv Atom/XML API with configured categories + keywords
2. **Store** — persists paper metadata in local SQLite for deduplication
3. **Rank** — scores each paper: +10 per category match, +15 per keyword in title, +5 in abstract, +10 for recency
4. **Summarize** — extractive (first 3 sentences) or LLM-generated (Gemini)
5. **Build** — generates Markdown digest, groups papers by topic
6. **Deliver** — optional HTML email via Gmail SMTP

## Repository layout

```
src/research_digest/
  cli.py                — Typer CLI (fetch, rank, build, run, send, status)
  config.py             — YAML + env var config loading
  models.py             — Pydantic data models
  categories.py         — arXiv category code to name mapping
  logging_config.py     — logging setup
  fetchers/arxiv.py     — arXiv API client and XML parser
  storage/db.py         — SQLite schema and connection
  storage/repository.py — data access layer
  pipeline/             — fetch, rank, summarize, build orchestration
  summarization/        — LLM provider abstraction (Gemini, extractive)
  delivery/             — email provider abstraction (Gmail SMTP)
  rendering/            — Markdown and HTML email renderers
tests/                  — 112 pytest tests
config/                 — topic configuration (YAML)
.github/workflows/      — GitHub Actions cron workflow
```

## License

Personal project. Use freely.
