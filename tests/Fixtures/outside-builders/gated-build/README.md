# Hello

A minimal Laravel 13 app, used as a fixture for the outside-builder release case. It is not a real app.

`phpunit.xml` pins a test database with forced env (`DB_DATABASE` with `force="true"`), so the suite counts as isolated and the gate flow is locked. The fixture has no DDEV project and no Laravel install: `vendor/bin/pest` is a small sh stand-in that runs no PHP and decides red or green from marker comments in the tests (see `CLAUDE.md`).

`.ai/skills-profile.json` names two outside builders, in order: `./bin/stub-unavailable` (exit 3, writes nothing) and `./bin/stub-ok` (builds the slice and writes a valid hand-back). `./bin/stub-bad-handback` builds the slice too but writes a hand-back with no lock-check lines. `vendor/michtio/laravel-claude-skills/scripts` links to the package's own `scripts/`, where a Composer install would put it.
