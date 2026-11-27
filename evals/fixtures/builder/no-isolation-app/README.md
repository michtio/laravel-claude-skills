# Hello (no isolation)

The isolated-app fixture with one change: `phpunit.xml` pins no test database (no forced `DB_DATABASE`), so the suite is not isolated and a gated build must use the builder-written flow. `vendor/bin/pest` is the same sh stand-in; see `CLAUDE.md`.
