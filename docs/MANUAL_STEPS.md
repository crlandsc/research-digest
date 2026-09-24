# Manual Steps

This file tracks tasks that require human action and cannot be completed solely inside the repository.

The goal is to let Claude build continuously until it reaches a genuine human-only blocker.

## Rules for Claude

When a human-only task is required, Claude must:

1. add or update the relevant entry in this file
2. update `docs/STATE.md` to show the blocker
3. stop and present the task using the required `ACTION REQUIRED` format from `CLAUDE.md`

Claude should avoid asking for human action early if an unblocked local-first path still exists.

## Rules for the human

Whenever possible:
- perform the requested action outside the repo
- place secrets in local `.env`, not in version control
- reply with confirmation like `done`
- avoid pasting raw secrets into chat unless absolutely necessary

---

## MS-001 — Create a local `.env` file
- Status: Complete (2026-04-08)
- Contains: GEMINI_API_KEY, EMAIL_FROM, EMAIL_TO, GMAIL_APP_PASSWORD

### Why human action is required
This is a local-machine step and may contain secrets.

### Exact steps
1. Duplicate `.env.example` to `.env`
2. Fill only the variables that are actually needed for the current feature
3. Save the file locally
4. Do not commit `.env`

### What to send back to Claude
- Confirmation that `.env` exists locally
- Confirmation of which variable names were filled in
- Do **not** paste secret values unless explicitly necessary

### Verification
Claude should verify by checking that required env vars are present or that the app loads configuration successfully.

---

## MS-002 — Create a local topic config
- Status: Complete (2026-04-08)
- Needed for: Running the digest against real interests
- Trigger: When the implementation is ready to read a user-specific config file

### Why human action is required
Only the user knows which topics and filters matter most.

### Exact steps
1. Copy `config/topics.example.yaml` to `config/topics.yaml`
2. Edit categories, keyword queries, and filters to match your interests
3. Save the file locally
4. Optionally commit it only if you want that config tracked in git; otherwise keep it local

### What to send back to Claude
- Confirmation that `config/topics.yaml` exists
- Any special preferences Claude should know about

### Verification
Claude should verify by loading the config successfully.

---

## MS-003 — Add an optional LLM provider API key
- Status: Deferred
- Needed for: Optional provider-backed summarization or ranking
- Trigger: Only after the local non-LLM digest works and the docs allow LLM enhancement

### Why human action is required
Provider accounts, billing, and key creation happen outside the repository.

### Exact steps
Claude must replace this placeholder section with the **current provider-specific steps** before asking the user to do this.

At minimum, the final instructions must include:
1. which provider was chosen
2. where the user needs to go
3. which key or credential to create
4. which env var name to place it under
5. whether billing or permissions are required
6. how Claude will verify the setup locally

### What to send back to Claude
- Confirmation that the required env var has been added locally
- Any non-secret identifier needed by the integration
- Prefer `done` over sharing the secret itself

### Verification
Claude should verify by running the relevant local command or health check.

---

## MS-004 — Configure delivery provider
- Status: Deferred
- Needed for: Optional email or messaging delivery
- Trigger: Only after local digest generation works and delivery is intentionally prioritized

### Why human action is required
Provider setup, verification, and dashboard configuration happen outside the repository.

### Exact steps
Claude must replace this placeholder section with the current provider-specific steps before asking for this task.

### What to send back to Claude
- Confirmation that the provider setup is complete
- Confirmation of which env vars or identifiers were added locally

### Verification
Claude should verify with a non-destructive local test if possible.

---

## MS-005 — Set up the recurring trigger
- Status: Done (external OS timer on the maintainer's always-on machine)
- Needed for: Automated recurring digests
- Trigger: Once, after the local CLI workflow is working end-to-end

### Why human action is required
The timer lives on your own always-on machine, outside the repo, and `gh` must be
authenticated as the user it runs as. Claude cannot install or verify it.

### Exact steps
Neither workflow uses a GitHub `schedule:` cron (D-034, D-036), so **one** timer drives
everything. On an always-on machine, ideally the same box as your self-hosted runner:

1. Authenticate `gh` as the user the timer will run as: `gh auth login`, then `gh auth status`.
2. Create an OS timer that runs, once per weekday morning:
   ```bash
   gh workflow run digest.yml --repo <your-username>/research-digest
   ```
   - **macOS** — a launchd LaunchAgent with a `StartCalendarInterval` (local time, so
     DST-aware). Use the **absolute** path to `gh`: LaunchAgents get a minimal `PATH` and
     will not find a Homebrew `gh` at `/opt/homebrew/bin/gh`. Set `StandardOutPath` and
     `StandardErrorPath` so failures leave a trace.
   - **Linux** — a user `crontab` entry or a `systemd` user timer calling the same command.
3. Nothing extra is needed for the weekly model-drift check. `digest.yml` dispatches
   `check-models.yml` itself when the UTC day-of-week is Monday (D-036).

Prefer GitHub's built-in cron instead? Uncomment the `schedule:` block at the top of
`digest.yml` and skip the timer, but note GitHub auto-disables scheduled workflows after
60 days of repo inactivity on public repos, and fires them late under load.

### What to send back to Claude
- Confirmation that the timer is installed and `gh auth status` is clean
- The schedule you chose (day-of-week and local time)

### Verification
Fire the timer manually rather than waiting a day. On macOS:
`launchctl kickstart -k "gui/$(id -u)/<LABEL>"`. Then confirm a run appears:
`gh run list --workflow=digest.yml --limit 3` should show `event=workflow_dispatch`.
On the following Monday, confirm `gh run list --workflow=check-models.yml --limit 3`
shows a `workflow_dispatch` run shortly after the digest.

---

## MS-006 — Register a self-hosted runner (optional)
- Status: Optional — implemented in repo (`digest.yml` + `check-models.yml` + `scripts/runner.sh`); registration not done
- Needed for: Running the scheduled automation from an un-throttled IP instead of GitHub's shared, increasingly rate-limited runners
- Trigger: Only if you want the scheduled workflows to run on your own always-on machine

### Why human action is required
Registering a self-hosted runner requires a one-time token from your fork's GitHub
settings and installing the runner agent on a physical machine — both outside the repo.

### Exact steps
See **`docs/RUNNER.md`** for the full walkthrough. In brief:
1. Fork → Settings → Actions → Runners → New self-hosted runner.
2. Run the shown `./config.sh …` (the auto-assigned `self-hosted` label is enough), then `./svc.sh install && ./svc.sh start`.
3. From a clone: `scripts/runner.sh local` (switch back any time with `scripts/runner.sh github`).

### What to send back to Claude
- Confirmation the runner shows **Idle** under Settings → Actions → Runners
- Confirmation of which label it carries (default `self-hosted`)

### Verification
Trigger a manual run and confirm the scheduled job executed on the self-hosted runner
and the arXiv fetch succeeded without 429/503 retries.

## MS-007 - Diagnose the Mac Mini's arXiv 406 block
- Status: Open (2026-09-24)
- Needed for: moving scheduled automation back to the self-hosted Mac Mini (`scripts/runner.sh local`)
- Trigger: next time you have access to the Mac Mini (or can run an agent there)

### Why human action is required
The block is specific to the Mac Mini, so it can only be probed from that machine. See D-037 for the evidence.

### Exact steps
Keep the total under ~10 requests, 5+ s apart. Test URL: `https://export.arxiv.org/api/query?search_query=cat:cs.SD&max_results=1`
1. curl GET with the default User-Agent, then with `-A "research-digest/0.1.0 (local CLI tool)"`.
2. The same GET with the runner's `python3.12`, via httpx (throwaway venv) and via `urllib.request`.
3. Record: public IP, `python3.12 -c "import ssl; print(ssl.OPENSSL_VERSION)"`, `curl --version`, `scutil --proxy`, proxy env vars, any VPN, content filter or network extension.

### What to send back to Claude
- A table of client, User-Agent and status code (plus the `via` header) for each request
- The environment details from step 3, and whether the MacBook was on the same network during the 2026-09-24 tests

### Verification
If every GET gets 406, the block is on the IP (wait it out, get a new IP from the ISP, or ask arXiv to lift it). If only Python gets 406, it's at the client/TLS level (try a different Python/OpenSSL build). Once a GET gets a 200, run `scripts/runner.sh local` and trigger a manual run.

---

## Required response template

Whenever Claude is blocked by a human-only step, it must respond using exactly this structure:

```md
## ACTION REQUIRED

### What I need you to do
[one short, specific action]

### Why I need this
[why the task cannot be completed inside the repository]

### Exact steps
1. ...
2. ...
3. ...

### What to send back to me
- ...
- ...
- ...

### How I will continue once you do that
[brief description of the next implementation step]
```