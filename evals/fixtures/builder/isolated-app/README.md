# Hello

A minimal Laravel 13 app, used as a fixture for the gated-build release cases. It is not a real app.

`phpunit.xml` pins a test database with forced env (`DB_DATABASE` with `force="true"`), so the suite counts as isolated. The fixture has no DDEV project and no Laravel install: `vendor/bin/pest` is a small sh stand-in that runs no PHP and decides red or green from marker comments in the tests (see `CLAUDE.md`). There is no `.ai/skills-profile.json`, so the gate flow is locked.
