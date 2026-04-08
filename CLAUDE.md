# Claude Instructions

## Mission

Build this repository incrementally into a useful local-first research digest tool.

Use the repository documentation as the source of truth. Prefer progress that does not require human intervention.

## Required read order

Read these files before making implementation decisions:

1. `README.md`
2. `docs/PRODUCT_SPEC.md`
3. `docs/ARCHITECTURE.md`
4. `docs/DECISIONS.md`
5. `docs/TASKS.md`
6. `docs/MANUAL_STEPS.md`
7. `docs/STATE.md`
8. `env.example`
9. `config/topics.example.yaml`

If these documents conflict, do not guess silently. Propose a minimal correction and then continue once the direction is clear.

## Non-negotiable working rules

- Work autonomously on any task that can be completed entirely inside the repository.
- Prefer the highest-value unblocked work.
- Prefer the local-first path over hosted or paid integrations.
- Do not invent or hardcode credentials, API keys, account IDs, or secrets.
- Do not commit secrets or ask the user to paste secrets into the repo.
- Keep changes incremental and testable.
- Keep docs synchronized with reality as implementation becomes concrete.
- Do not repeatedly ask for decisions that are already captured in the docs.
- Avoid premature deployment, auth, notifications, or UI work unless the docs explicitly prioritize them.
- Do not make external paid services a hard dependency for the first useful version unless `docs/DECISIONS.md` is updated to allow that.

## Default implementation priority

Unless the docs are updated to say otherwise, build in this order:

1. basic project scaffold
2. configuration loading
3. arXiv fetch/injest flow
4. local persistence
5. filtering and ranking
6. Markdown digest rendering
7. tests for critical paths
8. optional LLM summarization
9. optional scheduling
10. optional delivery channels
11. optional deployment

## Preferred behavior under uncertainty

When details are missing but the decision is low-risk:
- choose the simplest reasonable option
- record it in `docs/DECISIONS.md`
- continue

When a decision has meaningful product, cost, or architecture consequences:
- pause and ask the user only if it truly blocks progress
- otherwise choose the smallest reversible option and record it

## When you must ask the user for help

Stop and ask the user only when a task requires human action such as:

- creating an account
- logging into a dashboard
- generating an API key or secret
- enabling billing
- accepting terms or permissions
- setting DNS or domain records
- configuring a third-party dashboard
- approving OAuth scopes or app permissions
- making a major product decision not covered by the docs

## Required format when blocked

When blocked by a human-only task, you must:

1. update `docs/MANUAL_STEPS.md` with the specific task
2. update `docs/STATE.md` to reflect the blocker
3. respond using this exact structure

```md
## ACTION REQUIRED

### What I need you to do
[one short, specific action]

### Why I need this
[why this cannot be completed inside the repo]

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

## Session workflow

At the beginning of a work session:
1. read the docs listed above
2. inspect the current repository state
3. update `docs/STATE.md` with a short current plan if needed
4. execute the highest-priority unblocked task

At the end of a meaningful work session:
1. update `docs/STATE.md`
2. update `docs/TASKS.md`
3. update `docs/DECISIONS.md` if any decisions changed
4. keep setup or usage instructions current

## Documentation ownership

If the implementation makes any documented statement outdated, update the docs in the same workstream.

The docs should remain accurate enough that a future Claude session can resume from them without needing prior chat context.

## First-run expectation

On the first run in this repo, you should:
1. audit the repo
2. confirm the docs are internally consistent
3. update `docs/STATE.md` with the concrete next milestone
4. begin implementation on the highest-priority unblocked path
5. avoid external credentials until they are genuinely needed