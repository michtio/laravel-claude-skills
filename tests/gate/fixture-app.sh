#!/usr/bin/env bash
# Fixture-app gate for slice S1 (AC4). Needs DDEV; not a unittest. See tests/gate/CONTRACT.md section 4.
#
#   bash tests/gate/fixture-app.sh
#
# Assumes fixtures/app: a Laravel app with Boost and its own .ddev (PHP 8.4), requiring this
# package through a Composer path repository. Only ddev commands run; nothing on the host.
# BOOST_CMD overrides the install command, for example:
#   BOOST_CMD="php artisan boost:update --no-discover --no-interaction" bash tests/gate/fixture-app.sh

set -u

repo=$(cd "$(dirname "$0")/../.." && pwd)
app="$repo/fixtures/app"
skill="$app/.claude/skills/laravel-pitfalls/SKILL.md"
boost_cmd=${BOOST_CMD:-"php artisan boost:install --guidelines --skills --mcp --no-interaction"}

fail() {
    echo "FAIL: $1"
    exit 1
}

command -v ddev >/dev/null 2>&1 || fail "ddev is not installed"
[ -f "$app/.ddev/config.yaml" ] || fail "fixtures/app/.ddev/config.yaml is missing (no fixture app with its own DDEV project)"

ddev start --skip-hooks --dir "$app" >/dev/null 2>&1 || ddev start --dir "$app" || fail "ddev start failed in fixtures/app"

# Remove any earlier output so the assertion proves this run wrote it.
rm -rf "$app/.claude/skills/laravel-pitfalls"

echo "running in DDEV: $boost_cmd"
ddev exec --dir /var/www/html bash -c "$boost_cmd" || fail "Boost command failed: $boost_cmd"

[ -s "$skill" ] || fail "fixtures/app/.claude/skills/laravel-pitfalls/SKILL.md was not written (or is empty)"

echo "PASS: Boost wrote .claude/skills/laravel-pitfalls/SKILL.md"
exit 0
