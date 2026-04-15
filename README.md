# research-digest

A local-first tool that fetches recent arXiv papers, ranks them by relevance to your configured interests, and delivers a concise email digest with LLM-generated summaries. Papers are grouped by topic for easy scanning.

Built for personal use but designed to be forked. The default configuration targets music/audio AI/ML research, but it works for any arXiv domain — just edit the config file. A [generic template](#2-configure-your-interests) is included to get started quickly with any field.

## What you get

- A weekday morning email digest with the most relevant papers in your field
- Concise, newsletter-style summaries via Google Gemini (free tier, no billing required)
- Papers grouped by topic and ranked by relevance
- Resource links (Code, Model, Demo, Dataset, Colab) extracted automatically
- LaTeX math notation rendered as clean Unicode in emails (e.g., `$\beta$` becomes `β`)
- Works locally as a CLI with no API keys required (LLM and email are optional)

## Quickstart

### 1. Install

```bash
git clone https://github.com/crlandsc/research-digest.git
cd research-digest

# Create a virtual environment (pick one)
python3 -m venv .venv && source .venv/bin/activate  # standard venv
# OR: pyenv virtualenv 3.12 research-digest && pyenv local research-digest

pip install -e ".[dev]"
```

Requires Python 3.12+.

### 2. Configure your interests

```bash
cp config/topics.example.yaml config/topics.yaml
```

Edit `config/topics.yaml` to match your field:

```yaml
sources:
  arxiv:
    # arXiv categories — find yours at https://arxiv.org/category_taxonomy
    categories:
      - cs.CV       # Computer Vision
      - cs.LG       # Machine Learning

    # Search phrases (AND-ed with categories)
    # Leave empty to get ALL papers in your categories
    keyword_queries:
      - "object detection"
      - "image segmentation"

# How papers are grouped in the digest email
keyword_groups:
  "Detection":
    - "object detection"
  "Segmentation":
    - "image segmentation"
```

### 3. Run locally

```bash
# Fetch, rank, and generate a Markdown digest
research-digest run

# Preview the arXiv query without fetching
research-digest fetch --dry-run

# Override lookback window
research-digest run --lookback-days 14

# Check database stats
research-digest status
```

Output is written to `output/<YYYY-MM-DD>/digest.md`.

### 4. Add LLM summaries (optional, free)

By default, the digest uses the first few sentences of each abstract. For concise, newsletter-style summaries:

1. Get a free API key at [Google AI Studio](https://aistudio.google.com/apikey) (no billing required)
2. Create `.env` from the template: `cp env.example .env`
3. Add your key: `GEMINI_API_KEY=your_key_here`
4. In `config/topics.yaml`, set:
   ```yaml
   summarization:
     mode: llm
     provider: gemini
   ```

The summarizer uses a 5-model fallback chain (Gemini 3 Flash → Gemini 3.1 Flash Lite → Gemma 4 → Gemini 2.5 Flash → Gemini 2.5 Flash Lite) so it stays reliable even when individual models have outages.

### 5. Add email delivery (optional)

1. Create a [Gmail App Password](https://myaccount.google.com/apppasswords) (requires 2FA enabled on your Google account)
2. Add to `.env`:
   ```
   EMAIL_FROM=you@gmail.com
   EMAIL_TO=you@gmail.com
   GMAIL_APP_PASSWORD=your_16_char_password
   ```
3. Run with email: `research-digest run --send-email`

### 6. Automate with GitHub Actions (optional)

The included workflow delivers the digest every weekday morning automatically:

1. Fork or push this repo to GitHub
2. Go to Settings > Secrets and variables > Actions
3. Add these repository secrets:
   - `GEMINI_API_KEY` — your Google AI Studio key
   - `GMAIL_APP_PASSWORD` — your Gmail app password
   - `EMAIL_FROM` — sender email address
   - `EMAIL_TO` — recipient email address
4. That's it. The workflow runs at ~7 AM ET on weekdays.
   - Monday covers the weekend (3-day lookback)
   - Tuesday-Friday covers the previous day

You can also trigger manually from the Actions tab at any time.

**Note:** GitHub Actions scheduled runs can be delayed 10-60+ minutes during high load ([details](https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows#schedule)). If a digest doesn't arrive, trigger it manually.

## How it works

1. **Fetch** — queries the arXiv API with your configured categories + keywords
2. **Store** — persists paper metadata in local SQLite for deduplication
3. **Rank** — scores each paper: +10 per category match, +15 per keyword in title, +5 in abstract, +10 for recency
4. **Summarize** — extractive (first 3 sentences) or LLM-generated via Gemini (free tier)
5. **Render** — generates Markdown digest with topic grouping; LaTeX math converted to Unicode for email
6. **Deliver** — optional HTML email via Gmail SMTP

## Tests

```bash
pytest    # 180 tests, all offline (no API keys or network needed)
```

CI runs on every push to main.

## Repository layout

```
src/research_digest/
  cli.py                — Typer CLI (run, fetch, send, status)
  config.py             — YAML + env var config loading
  models.py             — Pydantic data models
  fetchers/arxiv.py     — arXiv API client
  storage/              — SQLite persistence and deduplication
  pipeline/             — fetch, rank, summarize, build orchestration
  summarization/        — LLM provider abstraction (Gemini fallback chain)
  rendering/            — Markdown, HTML email, LaTeX-to-Unicode conversion
  delivery/             — email delivery (Gmail SMTP)
config/
  topics.example.yaml   — annotated template (generic ML/AI, easy to customize)
tests/                  — 180 pytest tests
.github/workflows/      — GitHub Actions: daily digest + CI
```

## License

MIT License. See [LICENSE](LICENSE).
