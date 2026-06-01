# Where the scheduled automation runs: GitHub-hosted vs. self-hosted

By default every workflow runs on a **GitHub-hosted** runner (`ubuntu-latest`).
You can optionally run your **scheduled automation** on your own always-on machine
(a self-hosted runner) instead, and flip between the two with one command. Forks and
other users are unaffected — they keep the GitHub-hosted default with zero config.

## What the switch covers

A single repo variable, `AUTOMATION_RUNNER`, drives **both scheduled workflows together**:

| Workflow | Trigger | On the switch? |
| --- | --- | --- |
| `digest.yml` (daily digest) | schedule + manual | ✅ yes |
| `check-models.yml` (weekly model-drift) | schedule + manual | ✅ yes |
| `tests.yml` (CI) | push + pull_request | ❌ **never** — always GitHub-hosted |

Keeping all *scheduled* automation in one place (rather than some on GitHub, some
local) is simpler to operate and reason about. `tests.yml` is deliberately excluded —
see [Security & fork-safety](#security--fork-safety).

## Why this option exists

arXiv is fronted by a Fastly/Varnish CDN that rate-limits **per IP address**.
GitHub-hosted runners egress through a *shared* pool of cloud IPs that thousands of
other CI jobs also use to scrape arXiv, so a single polite request from this workflow
can still hit `429 Rate exceeded` / `503` because the shared IP's budget was already
spent by strangers. This trends worse over time as more projects automate arXiv pulls.
The in-workflow retries (backoff, jitter, fresh-runner re-runs — see `docs/DECISIONS.md`
D-031) soften it but cannot eliminate it.

The categorical fix is to make the request from an IP that *isn't* shared with the CI
swarm. A self-hosted runner on an always-on box (residential/dedicated IP) makes one
polite request and essentially never gets throttled — while reusing the **exact**
workflows: same secrets, same retry logic, same email, same Actions logs.

## How the switch works

Both scheduled workflows select their runner from the variable:

```yaml
runs-on: ${{ vars.AUTOMATION_RUNNER || 'ubuntu-latest' }}
```

| `AUTOMATION_RUNNER` value | Where scheduled jobs run |
| --- | --- |
| unset (default) | GitHub-hosted `ubuntu-latest` |
| `ubuntu-latest` | GitHub-hosted `ubuntu-latest` |
| `self-hosted` (or your runner's label) | your self-hosted runner |

Only **one** scheduler is ever in charge (GitHub's cron). Flipping the variable changes
*where* the single scheduled run executes — so there's exactly one run and one email
regardless of the setting. No double-sends, ever.

### Flip it with one command

```bash
scripts/runner.sh local     # route scheduled automation to your runner
scripts/runner.sh github    # route it back to GitHub-hosted (the default)
scripts/runner.sh status    # show the current selection
```

(That wraps `gh variable set/delete AUTOMATION_RUNNER` — run those directly if you
prefer. The label defaults to `self-hosted`; override with
`AUTOMATION_RUNNER_LABEL=… scripts/runner.sh local` if you run several runners.)

> **Important:** when set to `local`, your runner must be **online**. GitHub does *not*
> auto-fall-back from a self-hosted label to a hosted runner — if the label is selected
> and no matching runner is online, scheduled runs **queue until they time out**. So run
> `scripts/runner.sh github` *before* taking the box offline for maintenance.

## One-time setup: register a self-hosted runner

Do this on the always-on machine (e.g. your Mac Mini). It takes a few minutes.

1. In your fork on GitHub: **Settings → Actions → Runners → New self-hosted runner**.
   Pick the OS/arch; GitHub shows copy-paste `download` + `./config.sh` commands with a
   one-time registration token. The runner automatically gets the `self-hosted` label,
   which is all the default switch needs (no custom `--labels` required).
2. **Keep it running across reboots** (recommended for an always-on box) by installing it
   as a service instead of `./run.sh`:
   ```bash
   ./svc.sh install
   ./svc.sh start      # ./svc.sh status to check
   ```
3. Point the scheduled jobs at it: `scripts/runner.sh local`.

### Runner prerequisites

Jobs run `pip install -e .` and need **Python 3.12** plus `git`. `actions/setup-python`
will fetch 3.12 if it isn't present; if you use `pyenv`, having 3.12 installed satisfies
it. Secrets (`GEMINI_API_KEY`, `GMAIL_APP_PASSWORD`, `EMAIL_FROM`, `EMAIL_TO`) come from
the repo's Actions secrets — you do **not** need a local `.env` for the workflows. A
single runner processes one job at a time, so the daily digest and the weekly model-check
simply queue if they ever coincide.

## Security & fork-safety

- **Forks/other users are unaffected.** `vars.AUTOMATION_RUNNER` is unset in any other
  copy of the repo, so `runs-on` resolves to `ubuntu-latest` exactly as before.
- **CI tests never touch your runner.** `tests.yml` runs on `push`/`pull_request`
  (including PRs from forks of this public repo). GitHub warns that self-hosted runners on
  public repos can execute untrusted fork code, so `tests.yml` is hardcoded to
  `ubuntu-latest` and is **not** on the switch. The two scheduled workflows trigger only
  on `schedule`/`workflow_dispatch`, which forks cannot fire, so they're safe to self-host.
  Do not add a `pull_request` trigger to the scheduled workflows, and do not route
  `tests.yml` to a self-hosted runner.

## Verifying

After `scripts/runner.sh local`, trigger a manual run (`gh workflow run "Daily Research
Digest"` or the Actions tab) and confirm in the run's logs that the job ran on your
self-hosted runner and the arXiv fetch succeeded without `429`/`503` retries.
