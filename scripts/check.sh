#!/bin/sh
# Every deterministic quality gate of the package, in one command. No model
# calls, no network. CI runs exactly this; run it before every commit that
# touches resources/boost/, agents/, scripts/ or evals/.
#
#   sh scripts/check.sh
#
# Ported from craftcms-claude-skills (bin/check.sh, 1.31.0). Gates (each prints
# one line; the run fails if any fails):
#   frontmatter    scripts/validate-skills.sh (YAML, name, description, listing cap, 12 KB body)
#   agent-budget   scripts/agent_budget.py (48 KB startup, checker 16 KB, agent caps <= 5,
#                  no Agent on checkers or the gate writer, tinker, record-rule and
#                  write tools disallowed on read-only agents, no xhigh reviewers)
# Each check must also FAIL on its bad fixture in evals/fixtures/; those negative
# tests run here too, so a check that silently stops checking turns CI red.
# Later slices append their gates.
#
# Requires: python3 (3.9+), ruby (validate-skills.sh), bash, POSIX sh.

set -u

repo=$(cd "$(dirname "$0")/.." && pwd)
cd "$repo" || exit 2

log=$(mktemp)
trap 'rm -f "$log"' EXIT
failed=0

# gate NAME COMMAND...: run, print ok/FAIL, show output on failure.
gate() {
    name=$1
    shift
    if "$@" >"$log" 2>&1; then
        printf 'ok    %s\n' "$name"
    else
        printf 'FAIL  %s\n' "$name"
        sed 's/^/      /' "$log"
        failed=1
    fi
}

# must_fail NAME PATTERN COMMAND...: the command must exit 1 and its output must
# match PATTERN (a self-test). Checking the message, not only the exit code,
# keeps a crash from passing as a detected violation.
must_fail() {
    name=$1
    pattern=$2
    shift 2
    "$@" >"$log" 2>&1
    code=$?
    if [ "$code" -ne 1 ]; then
        printf 'FAIL  %s (expected exit 1, got %s)\n' "$name" "$code"
        sed 's/^/      /' "$log"
        failed=1
    elif ! grep -qF -- "$pattern" "$log"; then
        printf 'FAIL  %s (output did not contain: %s)\n' "$name" "$pattern"
        sed 's/^/      /' "$log"
        failed=1
    else
        printf 'ok    %s\n' "$name"
    fi
}

# grep_ok NAME PATTERN COMMAND...: the command's output must match PATTERN.
grep_ok() {
    name=$1
    pattern=$2
    shift 2
    "$@" >"$log" 2>&1
    if grep -q "$pattern" "$log"; then
        printf 'ok    %s\n' "$name"
    else
        printf 'FAIL  %s (output did not match %s)\n' "$name" "$pattern"
        sed 's/^/      /' "$log"
        failed=1
    fi
}

# The package itself.
gate      "frontmatter (resources/boost/skills)" bash scripts/validate-skills.sh
gate      "agent startup budget (48 KB; checker 16 KB; caps <= 5; read-only tool rules)" python3 scripts/agent_budget.py

# Self-tests: each check fails on its bad fixture, and passes on the valid one.
must_fail "agent self-test (Agent tool, no cap line)" "Agent tool without an 'At most N agents per run|review' line" python3 scripts/agent_budget.py --root evals/fixtures/agent-no-cap
must_fail "agent self-test (checker with Agent)" "must not have the Agent tool" python3 scripts/agent_budget.py --root evals/fixtures/agent-checker-with-agent
must_fail "agent self-test (gate writer with Agent)" "must not have the Agent tool" python3 scripts/agent_budget.py --root evals/fixtures/agent-gate-writer-with-agent
must_fail "agent self-test (cap 6)" "cap above 5" python3 scripts/agent_budget.py --root evals/fixtures/agent-cap-6
must_fail "agent self-test (read-only agent without tinker disallowed)" "must disallow mcp__laravel-boost__tinker" python3 scripts/agent_budget.py --root evals/fixtures/agent-readonly-tinker
must_fail "agent self-test (read-only agent without record-rule disallowed)" "must disallow mcp__laravel-boost__record-rule" python3 scripts/agent_budget.py --root evals/fixtures/agent-readonly-record-rule
must_fail "skill self-test (body over 12 KB)" "max 12288" bash scripts/validate-skills.sh --root evals/fixtures/skill-body-over-12kb
must_fail "skill self-test (listing over 1300)" "max 1300" bash scripts/validate-skills.sh --root evals/fixtures/skill-listing-over-1300
gate      "agent rules pass on evals/fixtures/valid" python3 scripts/agent_budget.py --root evals/fixtures/valid
gate      "skill rules pass on evals/fixtures/valid" bash scripts/validate-skills.sh --root evals/fixtures/valid

if [ "$failed" -ne 0 ]; then
    echo "check.sh: FAILED"
    exit 1
fi
echo "check.sh: all gates passed"
