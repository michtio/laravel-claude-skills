# Testing notes: names, package suites, concurrency gates and HTTP tests

Gap: covered partly by Boost (testing-best-practices, rules/naming.blade.php: "Naming tests"; rules/isolation.blade.php: "Framework fakes")

Boost's testing skill covers how to name, structure and isolate a test. These notes cover what it leaves out: naming tests so they stay readable and runnable as gates, package suites under Testbench, tests that need real parallel processes, HTTP tests that simulate several devices, and framework behaviors that make a correct test fail or a wrong one pass.

## Names and groups

- Test files are named by feature (`TokenRulesTest.php`, `SignInThrottleTest.php`), never by the slice, round or ticket that wrote them.
- Test descriptions read as sentences about behavior (`it('refuses a code that was already used')`), so a failure line explains itself.
- R and AC ids go in Pest groups: `->group('R8', 'AC8')`, so traceability survives a rename and `--group=AC8` runs exactly that criterion.
- Never put a slice or round id in a file, helper, class, constant or comment name: those ids mean nothing a month later.
- Run gates as `--group=<id>` (or a file path), not a word filter that depends on description prefixes: a plain `--filter` is a case-insensitive match on the generated test name, so it only works while every description happens to hold the word.
- `vendor/bin/pest --list-tests --group=AC8` lists exactly the tests in that group: check the selector before you rely on it.
- `->group()` chains anywhere on a test, before `->with()` or `->throws()` as well as after.
- A rename script changes only the description line (the `it(` or `test(` line) and the closing `})` line of each test, so the diff is two lines per test and `git diff -M` still shows each renamed file as a move.
- Split a gate file only together with its helpers: Pest loads every test file, so a global helper defined in two files is a fatal redeclare.
- Global helper functions in a test file carry a prefix unique to their file (`tokenRulesMakeCode()`), so two files never define the same name.

## Helper scope

- A single-file run (`vendor/bin/pest tests/Feature/OneTest.php`) loads only that file, so a helper function defined in another test file is an undefined function there, while a `--filter` run over the directory passes.
- Shared helpers are autoloaded, namespaced classes under `tests/Support` (`Tests\Support\Devices`), never functions in another test file.

## Assertions

- Assert on the specific address (`someone@example.test`), never on a bare `@`: an anonymous class name contains `@anonymous`, so "no `@` in the log" fails as soon as a class name is logged.
- A "writes only in services" architecture rule must cover every way to write: `save(`, `update(`, `create(`, `increment(`, `delete(` and fluent `DB::table(...)` writes, not only `insert(`.
- Or check writes by behavior: run the code against a query-log listener (`DB::listen`) and assert which classes the writes come from (their call stack).
- A grep architecture test is advisory: it checks spelling, not behavior, and a new write style passes it.
- Mark a helper `@phpstan-impure` when it wraps a repeated call whose result changes (a cache add, a lock, a clock) and PHPStan reports a later call "always false"; never suppress the report with an ignore or an assert.

## Package suites under Testbench

- Register the package provider in the base TestCase's `getPackageProviders()`, once for the whole suite; register per test only when a test is about registration, and say so in the file's header.
- A probe without the provider registered gives a false result: `app(Auditor::class)` resolved twice returns two objects, which looks like "not a singleton" when the provider simply never ran.
- `uses(TestCase::class)` in test files plus a folder-level `pest()->extend(TestCase::class)` in `tests/Pest.php` throws `TestCaseAlreadyInUse` on every such file: pick one place for the base case.
- `mergeConfigFrom` merges only the first level of a package config (an `array_merge`). Setting `config(['pkg.tokens.limit' => 5])` before the provider registers makes `pkg.tokens` a one-key array and drops its other defaults.
- Set nested package config after the provider is registered, or set the whole sub-array.
- `app()['env'] = 'production'` makes `app()->environment('testing')` false for the rest of the test, so an outside-testing branch runs in-process; restore it in `afterEach` if later code needs it.
- `app()->register(Provider::class, true)` (force) registers a fresh provider and, on a booted app, runs its boot again, so a boot-time refusal can be asserted per config value in one test.

## Concurrency gates in a package

When a criterion needs real parallel requests (an exact limit, a single use), run separate processes against the real database:

- A racer script under `tests/Support` boots Testbench's `Application::create()` (with `['extra' => ['dont-discover' => ['*']]]`), takes the parent's config (app key, database connection, package config) from a JSON file the parent writes, and warms the connection before it races.
- The racers wait for a shared start time a few seconds ahead (a barrier), then work through the same items in the same order.
- Shared state lives where every process sees it: the database or Redis cache store, not the array cache the PHPUnit pins set, which lives in one process.
- Exact expected counts (5 sends for a limit of 5, one success per code), so a sequential run passes only when the rule holds, and a broken rule fails by a countable margin.
- Each racer prints a `RESULT:` line last, and the parent requires it: a Testbench script that throws still exits 0 (see [package authoring](package-authoring.md)).
- A guarded single-use update also gets an interleaving test (see [single use and counters](single-use-and-counters.md)): under MySQL's changed-rows count a racer can pass by accident.

## HTTP tests

- JSON test helpers (`getJson()`, `postJson()`, `json()`) send no cookies unless the test calls `withCredentials()`: a remember-me test that sets the recaller cookie and calls `getJson()` gets 401, which looks like a broken recaller.
- Fixtures for case-sensitive identifiers need a `_bin` collation on MySQL (`->collation('utf8mb4_bin')`): under the default `_ci` collation the fixture table refuses `aBc` after `abc` as a duplicate before the code under test runs.
- `travel()` moves Carbon, not file mtimes: the file session handler compares the session file's mtime with now minus the lifetime, so after a time travel every session written in the test reads back empty while its cookie stays.
- Prefer the database session driver for time-travel tests (it stores the timestamp in the row, which moves with Carbon), or design the code so a missing session value is handled.

## Several devices in one test

The test client shares one application, so simulating several browsers leaks state between them: the guard keeps the last user, the session store merges the previous attributes, and the cookie jar keeps queued cookies.

- Before each device's request run the four resets: `auth()->forgetGuards()`, `app('session')->forgetDrivers()`, `app()->forgetInstance('session.store')` and `app('cookie')->flushQueuedCookies()`.
- Each device holds its own cookie jar (decrypted values), encrypts its cookies per request with `CookieValuePrefix::create()` like `prepareCookiesForRequest()`, and calls `$this->call()` with them, its own `REMOTE_ADDR` and user agent; read response cookies back with `decrypt($value, false)` and `CookieValuePrefix::remove()`.

## Queue workers in the suite

- An in-suite `queue:work` passes `--memory` with a large value: the worker's memory check reads `memory_get_usage(true)` of the whole Pest process, so it exits 12 (`Worker::EXIT_MEMORY_LIMIT`) once the suite grows, and CI (where PHP starts higher) fails first.
- An in-suite `queue:work` also passes `--stop-when-empty`; or process jobs with `Queue::fake()` or the sync connection instead.

## Rendering a Boost guideline

- To render a Boost guideline (`resources/boost/guidelines/*.blade.php`) in a test, hide backticks and `<?php` behind placeholders before `Blade::render()` and restore them after, as Boost's renderer does: otherwise a PHP example in the guideline is executed and fails with a syntax error.
- Point `app()->setBasePath()` at a temporary project root holding the profile the guideline reads (`.ai/skills-profile.json`).
