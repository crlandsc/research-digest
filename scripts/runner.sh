#!/usr/bin/env bash
#
# Switch where the *scheduled automation* runs: GitHub-hosted vs. your own runner.
#
# Governs BOTH scheduled workflows together (they read the same repo variable):
#   - .github/workflows/digest.yml        (daily research digest)
#   - .github/workflows/check-models.yml  (weekly Gemini model-drift check)
# CI tests (.github/workflows/tests.yml) are NOT affected — they always run on
# GitHub-hosted runners (untrusted fork PRs must never hit a self-hosted runner).
#
# Why: arXiv's Fastly/Varnish CDN throttles GitHub's *shared* runner egress IPs
# progressively harder (see docs/RUNNER.md and docs/DECISIONS.md D-031/D-032).
# A self-hosted runner (e.g. an always-on Mac Mini) uses an un-throttled IP. This
# flips the `AUTOMATION_RUNNER` repo variable that both workflows read in `runs-on`:
#
#   unset / 'ubuntu-latest'  ->  GitHub-hosted runner (default; what forks use)
#   '<self-hosted label>'    ->  your self-hosted runner
#
# Usage:
#   scripts/runner.sh local     # route scheduled automation to your runner
#   scripts/runner.sh github    # route it back to GitHub-hosted (the default)
#   scripts/runner.sh status    # show the current selection
#
# Requires: gh (authenticated, repo scope). When set to 'local', your self-hosted
# runner must be registered with the label below AND online — otherwise scheduled
# runs queue until they time out. Flip back to 'github' before taking it offline.
set -euo pipefail

VAR="AUTOMATION_RUNNER"
# Label your self-hosted runner carries. Every self-hosted runner automatically has
# the 'self-hosted' label, so the default needs no extra config at registration.
# Override with AUTOMATION_RUNNER_LABEL=... if you run several runners.
LABEL="${AUTOMATION_RUNNER_LABEL:-self-hosted}"

command -v gh >/dev/null 2>&1 || { echo "error: gh (GitHub CLI) not found on PATH." >&2; exit 69; }

current() {
  # Empty string if the variable is unset (404).
  gh api "repos/{owner}/{repo}/actions/variables/${VAR}" --jq '.value' 2>/dev/null || true
}

case "${1:-status}" in
  local)
    gh variable set "$VAR" --body "$LABEL"
    echo "OK: scheduled automation (digest + check-models) -> self-hosted runner '$LABEL'."
    echo "    Ensure that runner is online (see docs/RUNNER.md)."
    ;;
  github)
    gh variable delete "$VAR" >/dev/null 2>&1 || true
    echo "OK: scheduled automation -> GitHub-hosted ubuntu-latest (default)."
    ;;
  status)
    value="$(current)"
    if [ -z "$value" ] || [ "$value" = "ubuntu-latest" ]; then
      echo "${VAR} is ${value:-unset} -> GitHub-hosted ubuntu-latest (default)."
    else
      echo "${VAR}=${value} -> self-hosted runner '${value}'."
    fi
    ;;
  *)
    echo "Usage: $0 {local|github|status}" >&2
    exit 64
    ;;
esac
