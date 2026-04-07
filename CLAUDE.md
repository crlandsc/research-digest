# CLAUDE.md

## Operating Mode
You are working on a small bespoke Python project.

### Phase Rule
1. **Plan first**
2. **Wait for approval**
3. **Implement in phases**
4. **Keep each phase testable**
5. **Document manual steps clearly**

Do not jump straight into coding unless the human explicitly asks you to.

## Core Priorities
In priority order:

1. Low maintenance
2. Clear architecture
3. Easy future changes
4. Cheap runtime cost
5. Good docs
6. Minimal dependencies
7. Good testability
8. Nice output formatting

## Project Philosophy
This is a personal/small-scale automation project, not a SaaS platform.

That means:
- no overengineering,
- no microservices,
- no database server,
- no web UI,
- no auth system,
- no background queue,
- no premature abstractions beyond clear provider boundaries.

## Hard Constraints
- Use Python
- Use a plain `pyproject.toml`
- Keep dependencies minimal
- Use config-driven topic logic
- Use deterministic filtering before LLM calls
- Keep the LLM interface swappable
- Implement direct Gemini runtime provider first
- Implement file + SMTP delivery first
- Use GitHub Actions for automation
- Use simple local state (e.g. SQLite), not an external DB
- arXiv only for v1
- No PDF parsing in v1
- No complicated repo discovery in v1

## Architecture Guidance
Keep boundaries explicit.

Preferred boundaries:
- domain models
- config loading/validation
- arXiv collector
- deterministic filtering
- LLM provider(s)
- enrichment
- ranking
- rendering
- delivery
- state persistence
- CLI / orchestration

Avoid mixing all logic in one file.

## Dependency Guidance
Prefer stdlib where reasonable.

Acceptable core dependencies include:
- `pydantic`
- `PyYAML`
- `httpx`
- `jinja2`
- `typer`
- `tenacity`
- `pytest`
- `ruff`
- `mypy`

Only add more dependencies if they materially reduce complexity. If you add one, explain why in the plan or implementation summary.

## Code Style
- Use type hints for public functions/classes
- Prefer small functions
- Prefer explicit models over loose dicts
- Avoid hidden globals
- Avoid deep inheritance
- Prefer composition and simple interfaces
- Keep side effects at the edges
- Keep business rules readable and centralized
- Add docstrings where they help
- Use descriptive names
- Avoid “magic” behavior

## Config Principles
Human-tunable behavior should live in config whenever reasonable.

That includes:
- topics
- keywords
- ranking weights
- candidate caps
- model name
- budget guardrails
- schedule-related settings
- delivery settings

Do not hard-code user-specific interests into Python files.

## Prompt Principles
Prompts should be:
- centralized,
- versioned in one obvious place,
- concise,
- structured-output oriented,
- designed to avoid hallucination.

Do not ask the model for hidden chain-of-thought.
Ask for short structured justifications instead.

## Testing Rules
Tests matter because this is a low-upkeep automation project.

Minimum expectations:
- unit tests for config, filters, ranking, rendering
- fixture-based tests for arXiv parsing
- mock/fake tests for LLM provider
- mock/fake tests for SMTP/email sending
- at least one end-to-end dry-run test
- no live external API calls in unit tests

If an integration test would require real credentials, guard it or omit it from default CI.

## Reliability Rules
Build graceful degradation.

Required:
- rules-only fallback if configured
- idempotent reruns by default
- safe handling of missing optional enrichment
- clear logs
- preserved outputs on send failure
- no duplicate email sends on rerun unless forced

## Cost Rules
Keep token use down.

Required behaviors:
- deterministic filtering first
- cap LLM candidate count
- track cost/tokens approximately
- support budget guardrail
- do not run expensive enrichment or broad search unnecessarily

## Email / Rendering Rules
Email HTML should be simple and robust.

Preferred:
- single-column responsive layout
- limited CSS complexity
- good readability on mobile
- plain-text fallback
- no JavaScript
- no external assets unless truly necessary

## State Rules
State should be simple and inspectable.

The project must persist enough state to:
- avoid duplicate sends,
- remember recent runs,
- cache LLM results where useful,
- support reruns/backfills.

Do not design a heavy persistence layer.

## Documentation Requirements
The repository should end up with:
- clear README
- local setup instructions
- config documentation
- operations/runbook documentation
- examples where useful
- explicit manual steps that the human must perform

## GitHub Actions Rules
Workflows should be straightforward.

Need:
- CI workflow for tests/lint
- scheduled digest workflow
- manual workflow dispatch for dry run/backfill
- artifact upload
- clear environment/secret documentation

Do not create a complicated CI/CD system.

## When to Ask the Human Before Proceeding
Pause and ask if you are about to:
- introduce a new paid service
- introduce a new major dependency
- change the persistence approach significantly
- implement a feature outside v1 scope
- make a tradeoff that increases maintenance
- send real emails
- use real paid API calls unnecessarily

## Manual-Step Awareness
Anything involving the following must be documented for the human:
- API keys
- SMTP credentials
- GitHub secrets
- repo visibility choice
- topic configuration
- email recipients
- schedule/timezone choice
- state-branch permissions if used
- provider billing/quotas

## Output Discipline
When planning:
- be explicit
- list assumptions
- recommend defaults
- keep scope tight

When implementing:
- work phase by phase
- summarize what changed
- list tests run
- identify any remaining blockers