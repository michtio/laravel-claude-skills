#!/usr/bin/env bash
# Create fixtures/app: a fresh Laravel app with Boost and its own DDEV project
# (PHP 8.4), requiring this package through a Composer path repository (../..,
# symlinked). tests/gate/fixture-app.sh runs against it.
#
#   bash scripts/make-fixture-app.sh           # create (refuses when fixtures/app exists)
#   bash scripts/make-fixture-app.sh --force   # stop and delete this checkout's DDEV project first
#
# Everything PHP runs inside DDEV; nothing runs php or composer on the host.
# fixtures/app/ is git-ignored: the app is generated, never committed.
#
# boost.json lists this package under "packages" and claude_code under "agents",
# the same file an interactive `boost:install` writes after the developer ticks
# the package and the agent. A non-interactive `boost:install` installs only the
# third-party packages boost.json already lists (Laravel\Boost\Console\InstallCommand
# ::selectThirdPartyPackages), so a scripted install needs them there.

set -euo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd -P)
app="$repo/fixtures/app"
# One DDEV project per checkout: the first 10 hex characters of the sha1 of the
# checkout's real path, the digest tests/gate/ddev_lock.py uses for its lock and
# FIXTURE_PROJECT, so two checkouts or worktrees never share a project.
if command -v sha1sum >/dev/null 2>&1; then
    digest=$(printf '%s' "$repo" | sha1sum | cut -c1-10)
else
    digest=$(printf '%s' "$repo" | shasum -a 1 | cut -c1-10)
fi
project="lcs-fixture-app-$digest"
package=michtio/laravel-claude-skills

force=0
case "$#:${1:-}" in
    0:) ;;
    1:--force) force=1 ;;
    *)
        echo "usage: bash scripts/make-fixture-app.sh [--force]" >&2
        exit 2
        ;;
esac

command -v ddev >/dev/null 2>&1 || { echo "ddev is not installed" >&2; exit 1; }

if [ -e "$app" ]; then
    if [ "$force" -ne 1 ]; then
        echo "fixtures/app already exists; pass --force to recreate it" >&2
        exit 1
    fi
    ddev delete --omit-snapshot --yes "$project" >/dev/null 2>&1 || true
    rm -rf "$app"
fi

# A seed .ddev/config.yaml stops `ddev config` from finding this repo's own
# project one directory up and reconfiguring that one instead.
mkdir -p "$app/.ddev"
cd "$app"
printf 'name: %s\ntype: laravel\n' "$project" > .ddev/config.yaml

ddev config --project-name="$project" --project-type=laravel --php-version=8.4 \
    --docroot=public --database=mariadb:11.8
# The repo root (the host's ../.. from the app) is mounted read-only at
# /var/www/package, next to the app at /var/www/html, so the path repository
# can reach it inside the container.
cat > .ddev/docker-compose.package.yaml <<'YAML'
services:
  web:
    volumes:
      - ../../..:/var/www/package:ro
YAML
ddev start

ddev composer create-project "laravel/laravel:^13.0" --no-interaction --prefer-dist .
ddev composer require --dev --no-interaction "laravel/boost:^2.5"

# Path repository to this package, symlinked. Inside the container the app is
# /var/www/html and the package /var/www/package; ../package is the container
# spelling of the host's ../.. and both resolve to the same tree.
ddev composer config repositories.laravel-claude-skills \
    '{"type": "path", "url": "../package", "options": {"symlink": true}}'
ddev composer require --dev --no-interaction "$package:@dev"

cat > boost.json <<JSON
{
    "agents": ["claude_code"],
    "guidelines": true,
    "mcp": true,
    "packages": ["$package"],
    "skills": []
}
JSON

ddev exec php artisan boost:install --guidelines --skills --mcp --no-interaction

# The app is its own git repository, as a consumer project is, so its
# `composer test` secret scan (gitleaks detect --source .) covers the app's
# history only, never this package's history one directory up.
git init -q
git add -A
git -c user.name=fixture -c user.email=fixture@example.com -c commit.gpgsign=false \
    commit -q -m "chore: fixture app"
echo "fixtures/app ready ($project)"
