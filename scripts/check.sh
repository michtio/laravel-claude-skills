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
#   gap lines      scripts/check_pitfalls.py (every laravel-pitfalls reference carries
#                  "Gap: not covered by Boost" or "Gap: covered partly by Boost (<rule>)")
#   deny list      scripts/check_deny_list.py (no git-tracked file names a term from the
#                  git-ignored internal-docs/deny-list.txt; skipped when it is absent)
#   symbols        scripts/laravel_source.py check (every Illuminate class, facade, method,
#                  artisan command and config key the skills and agents name exists in the
#                  pinned laravel/framework; index in scripts/data/, refreshed with network
#                  by scripts/refresh-laravel-data.sh, read here without it)
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

# The package itself.
gate      "frontmatter (resources/boost/skills)" bash scripts/validate-skills.sh
gate      "agent startup budget (48 KB; checker 16 KB; caps <= 5; read-only tool rules)" python3 scripts/agent_budget.py
gate      "symbols (resources/boost/skills, agents) exist in laravel/framework $(cat scripts/data/laravel-source-tag.txt 2>/dev/null)" python3 scripts/laravel_source.py check resources/boost/skills agents
gate      "gap lines (every laravel-pitfalls reference names its Boost gap)" python3 scripts/check_pitfalls.py
gate      "deny list (published tree names no client, app, company or person; skipped without internal-docs/deny-list.txt)" python3 scripts/check_deny_list.py

# Self-tests: each check fails on its bad fixture, and passes on the valid one.
must_fail "agent self-test (Agent tool, no cap line)" "Agent tool without an 'At most N agents per run|review' line" python3 scripts/agent_budget.py --root evals/fixtures/agent-no-cap
must_fail "agent self-test (checker with Agent)" "must not have the Agent tool" python3 scripts/agent_budget.py --root evals/fixtures/agent-checker-with-agent
must_fail "agent self-test (gate writer with Agent)" "must not have the Agent tool" python3 scripts/agent_budget.py --root evals/fixtures/agent-gate-writer-with-agent
must_fail "agent self-test (cap 6)" "cap above 5" python3 scripts/agent_budget.py --root evals/fixtures/agent-cap-6
must_fail "agent self-test (read-only agent without tinker disallowed)" "must disallow mcp__laravel-boost__tinker" python3 scripts/agent_budget.py --root evals/fixtures/agent-readonly-tinker
must_fail "agent self-test (read-only agent without record-rule disallowed)" "must disallow mcp__laravel-boost__record-rule" python3 scripts/agent_budget.py --root evals/fixtures/agent-readonly-record-rule
must_fail "agent self-test (restricted Agent(...), no cap line)" "Agent tool without an 'At most N agents per run|review' line" python3 scripts/agent_budget.py --root evals/fixtures/agent-restricted-agent-no-cap
must_fail "agent self-test (Task(...) alias, no cap line)" "Agent tool without an 'At most N agents per run|review' line" python3 scripts/agent_budget.py --root evals/fixtures/agent-task-alias-no-cap
must_fail "agent self-test (column-0 block list, no cap line)" "Agent tool without an 'At most N agents per run|review' line" python3 scripts/agent_budget.py --root evals/fixtures/agent-column0-list-no-cap
must_fail "agent self-test (no tools line inherits Agent, no cap line)" "Agent tool without an 'At most N agents per run|review' line" python3 scripts/agent_budget.py --root evals/fixtures/agent-no-tools-no-cap
must_fail "agent self-test (checker inherits Agent)" "must not have the Agent tool" python3 scripts/agent_budget.py --root evals/fixtures/checker-inherits-agent
must_fail "agent self-test (planner inherits Agent)" "must disallow Agent" python3 scripts/agent_budget.py --root evals/fixtures/planner-inherits-agent
must_fail "agent self-test (no frontmatter)" "no frontmatter" python3 scripts/agent_budget.py --root evals/fixtures/agent-no-frontmatter
must_fail "agent self-test (checker by name: field)" "must not have the Agent tool" python3 scripts/agent_budget.py --root evals/fixtures/agent-name-field-checker
must_fail "agent self-test (quoted effort xhigh on a reviewer)" "reviewer agents use effort high, not xhigh" python3 scripts/agent_budget.py --root evals/fixtures/reviewer-effort-xhigh-quoted
must_fail "skill self-test (body over 12 KB)" "max 12288" bash scripts/validate-skills.sh --root evals/fixtures/skill-body-over-12kb
must_fail "skill self-test (listing over 1300)" "max 1300" bash scripts/validate-skills.sh --root evals/fixtures/skill-listing-over-1300
must_fail "symbol self-test (missing facade method)" "Illuminate\\Support\\Facades\\DB::transactional() not found" python3 scripts/laravel_source.py check evals/fixtures/symbol-missing-method
must_fail "symbol self-test (missing class)" "Illuminate\\Support\\Facades\\Transactor not found" python3 scripts/laravel_source.py check evals/fixtures/symbol-missing-class
must_fail "symbol self-test (missing artisan command)" "artisan queue:explode not found" python3 scripts/laravel_source.py check evals/fixtures/symbol-missing-command
gate      "symbols pass on evals/fixtures/symbol-valid" python3 scripts/laravel_source.py check evals/fixtures/symbol-valid
must_fail "pitfall self-test (reference without a gap line)" "no gap line" python3 scripts/check_pitfalls.py --root evals/fixtures/pitfall-no-gap
must_fail "pitfall self-test (covered partly, no Boost rule named)" "names no Boost rule" python3 scripts/check_pitfalls.py --root evals/fixtures/pitfall-partly-no-rule
gate      "pitfall rules pass on evals/fixtures/pitfall-valid" python3 scripts/check_pitfalls.py --root evals/fixtures/pitfall-valid
# Deny-list self-test: a throwaway tree whose one file names its one term.
deny_fixture=$(mktemp -d)
trap 'rm -f "$log"; rm -rf "$deny_fixture"' EXIT
printf 'placeholder-client-name\n' > "$deny_fixture/deny-list.txt"
printf 'Built for Placeholder-Client-Name.\n' > "$deny_fixture/README.md"
must_fail "deny-list self-test (published file names a deny-listed term)" "names a deny-listed term" python3 scripts/check_deny_list.py --root "$deny_fixture" --list "$deny_fixture/deny-list.txt"
gate      "agent rules pass on evals/fixtures/valid" python3 scripts/agent_budget.py --root evals/fixtures/valid
gate      "skill rules pass on evals/fixtures/valid" bash scripts/validate-skills.sh --root evals/fixtures/valid

if [ "$failed" -ne 0 ]; then
    echo "check.sh: FAILED"
    exit 1
fi
echo "check.sh: all gates passed"
