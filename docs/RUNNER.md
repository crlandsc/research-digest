# Where the scheduled automation runs: GitHub-hosted vs. self-hosted

By default every workflow runs on a **GitHub-hosted** runner (`ubuntu-latest`).
You can optionally run your **scheduled automation** on your own always-on machine
(a self-hosted runner) instead, and flip between the two with one command. Forks and
other users are unaffected — they keep the GitHub-hosted default with zero config.

## What the switch covers

A single repo variable, `AUTOMATION_RUNNER`, drives **both scheduled workflows together**:

| Workflow | Trigger | On the switch? |
| --- | --- | --- |
| `digest.yml` (daily digest) | external trigger + manual (no GitHub cron) | ✅ yes |
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

The variable only changes *where* a job runs, not *when* it's triggered. The weekly
model-check still uses GitHub's cron; the daily digest is triggered externally (see
[Scheduling](#scheduling-on-time-without-github-cron-delays) below). Each run has exactly
one trigger, so there are no double-sends.

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
   > **macOS:** install the runner **outside** TCC-protected folders (`~/Desktop`, `~/Documents`, `~/Downloads`) — e.g. `~/actions-runner`. A background launchd agent can be silently denied access there (`Operation not permitted`), so `svc.sh` reports "started" but the runner never connects. The agent also only runs inside an active GUI login session, so enable auto-login (or log in after a reboot) for unattended use.

3. Point the scheduled jobs at it: `scripts/runner.sh local`.

### Runner prerequisites

Jobs run `pip install -e .` and need **Python 3.12** plus `git`.

- **Linux self-hosted or GitHub-hosted:** `actions/setup-python` fetches 3.12 automatically.
- **macOS self-hosted:** `actions/setup-python` is **skipped** — its installer runs
  `sudo installer` for the python.org `.pkg`, which needs passwordless sudo a self-hosted
  user usually lacks. Instead the workflows build a venv from a **Python 3.12 already on the
  runner user's `PATH`**, so install one first (e.g. `pyenv install 3.12` or
  `brew install python@3.12`) and confirm `python3.12` resolves for that user (D-033).

Secrets (`GEMINI_API_KEY`, `GMAIL_APP_PASSWORD`, `EMAIL_FROM`, `EMAIL_TO`) come from the
repo's Actions secrets — you do **not** need a local `.env` for the workflows. A single
runner processes one job at a time, so the daily digest and the weekly model-check simply
queue if they ever coincide.

## Scheduling: on-time, without GitHub cron delays

GitHub's `schedule:` cron is queued globally and routinely fires **late** — often many
minutes to hours under load — which is bad for a "morning" digest. `digest.yml` therefore
ships with **no `schedule:` trigger**; it runs on `workflow_dispatch`, which dispatches
within seconds. Trigger it on time from any always-on machine (ideally the same box as your
self-hosted runner) with an OS timer running:

```bash
gh workflow run digest.yml --repo <your-username>/research-digest
```

- **macOS** — a launchd LaunchAgent with a `StartCalendarInterval` (uses local time, so it's
  DST-aware). It runs in your logged-in session, so keep the box awake and logged in.
- **Linux** — a user `crontab` entry or a `systemd` user timer calling the same command.

`gh` must be authenticated as the user the timer runs as (`gh auth login`). Prefer GitHub's
built-in cron instead? Uncomment the `schedule:` block at the top of `digest.yml` and skip
the external timer. (`check-models.yml` keeps its weekly GitHub cron — a drift check
tolerates the delay.)

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
