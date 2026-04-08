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
- Status: Not required yet
- Needed for: Any feature that reads runtime config or secrets from a local env file
- Trigger: Only when the implementation actually needs a `.env`

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

## MS-005 — Configure scheduling or deployment
- Status: Deferred
- Needed for: Automated recurring runs or hosted execution
- Trigger: Only after the local CLI workflow is working end-to-end

### Why human action is required
Cloud accounts, cron dashboards, and deployment settings typically require human access and approval.

### Exact steps
Claude must replace this placeholder section with the current platform-specific steps before asking for this task.

### What to send back to Claude
- Confirmation that the platform setup is complete
- Any non-secret identifiers needed by the app

### Verification
Claude should verify by checking the scheduled job, deployment status, or a successful dry run.

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