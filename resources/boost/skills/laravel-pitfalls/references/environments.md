# Environments: the local engine, CI and DDEV services

Gap: not covered by Boost

A suite that is green on one machine proves the code against that machine's engine and services. Boost's skills do not cover where DDEV's defaults, a CI workflow and a test database differ, or what a DDEV project actually reaches on its network. Each item here made a suite pass locally against something other than what CI or production runs.

## Pitfall 1: local and CI test different engines

- DDEV picks MariaDB when `.ddev/config.yaml` has no database block (10.11 before DDEV 1.25, 11.8 since), while CI templates often start a mysql:8 service: local and CI then test different engines, with different JSON, collation and locking behavior. Set `database:` in `.ddev/config.yaml` to the engine and version CI and production run, and start the same image in CI.
- `web_environment` in a `config.*.yaml` override is merged key by key with `config.yaml`, and a variable with the same name replaces the person's own value silently. A team override that sets `DB_HOST` or `REDIS_HOST` wins over what a developer wrote; name such keys in the override's comment, or keep them out of the shared file.

## Pitfall 2: moving a suite from sqlite to MySQL

- DDL in a test on MySQL is not rolled back: `CREATE TABLE` and `ALTER TABLE` commit implicitly, so tables a test creates survive a `RefreshDatabase` transaction, and the next test fails with `1050 Table ... already exists`. In-memory sqlite forgot them for free. Drop what the test created in `setUp`, or create test tables once in a migration.
- A Testbench package builds a fresh application for each test, and the old PDO connections stay open: an app built per test leaks connections until MySQL refuses with `1040 Too many connections`. Disconnect every connection in `beforeApplicationDestroyed()` (`DB::disconnect()` for each name in `config('database.connections')`).
- Refuse any database whose name does not end in `_test` (or `:memory:`) in the base TestCase, so a wrong environment cannot drop real tables.

## Pitfall 3: Redis on DDEV's shared network

Every DDEV project's containers join the shared `ddev_default` network, where the hostname `redis` resolves to other projects' Redis containers (round-robin between them) when your project has none. A suite or a build that sets `REDIS_HOST=redis` then reads and writes another project's Redis, a different one on each lookup.

- Before using Redis, check `.ddev/` for the Redis add-on (`docker-compose.redis.yaml` from `ddev add-on get ddev/ddev-redis`) and `ddev describe` for a redis service.
- Address the project's own Redis as `ddev-<project>-redis`, the container name the add-on creates, and give the suite its own Redis database index.
- A resolving hostname (`getent hosts redis`) or a successful connect is never proof that the project has Redis: both succeed against another project's container.
- When CI needs Redis too, start it there (the setup's `laravel.ci_services` option adds a Redis service to its workflow) instead of skipping the tests.

## How to test it

- Engine parity: compare the image in `.ddev/config.yaml` with the CI service image; a test that depends on engine behavior (a collation, a lock) runs on the production engine in both.
- Redis: assert in the suite's bootstrap that `REDIS_HOST` is not the bare `redis` on DDEV.

## Check

Review only.
