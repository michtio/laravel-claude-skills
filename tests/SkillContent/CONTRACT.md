# Gate contract: skill content (pitfalls, testing notes, verdicts, agent rules, Spatie learnings)

Slice S9d-2 of the laravel-layer spec. Requirements: R1, R2, R5, R6, R7, R13, R15, R16, R17 (decisions log 2026-11-27: "S9c and S9d", the S9d split, "Learnings from spatie/guidelines-skills", "Human-readable tests", R7 amended, the team rules in the agents). Source: `internal-docs/skills-gaps.md`, rows 1 to 177 (owner ruling: S9d covers every later field-test row up to this gate; row 174 is unused after a numbering collision; rows that arrive later go to the next slice). The owner's rulings on the gate writer's hand-backs are written into the sections below. Plan: slice S9d in `internal-docs/specs/2026-11-26-laravel-layer/plan.md`, split as the decisions log records.

The gate is written before the builder starts. The builder implements to this contract and never edits the gate files below or the test configuration; under G3 it may add its own tests, each failing first. A change to a gate file goes back to the gate writer. The builder closes each row in `skills-gaps.md` with the commit that fixed it. Everything earlier slices pinned stays, in particular the S9d-1 docs tests (`ReadmesNeverCiteTests` keeps R7 over every shipped `resources/boost/**/*.md`, the new references included) and `scripts/check.sh`.

Run, from the repo root:

```
python3 -m unittest discover -s tests/gate -p 'test_pitfalls_*.py'
python3 -m unittest discover -s tests/gate -p 'test_package_authoring.py'
python3 -m unittest discover -s tests/gate -p 'test_testing_notes.py'
python3 -m unittest discover -s tests/gate -p 'test_readable_test_names.py'
python3 -m unittest discover -s tests/gate -p 'test_agent_field_learnings.py'
python3 -m unittest discover -s tests/gate -p 'test_spatie_learnings.py'
python3 -m unittest discover -s tests/gate -p 'test_skill_content_hygiene.py'
ddev exec vendor/bin/pest tests/Profile/S9d1GitleaksTest.php
ddev exec vendor/bin/pest --group=R23 tests/Profile/CiServicesTest.php
ddev exec vendor/bin/pest tests/Profile/CiServicesTest.php tests/Profile/HouseStyleNamingHintsTest.php
sh scripts/check.sh
python3 -m unittest discover -s tests/gate
ddev exec vendor/bin/pest
```

Gate files: `tests/gate/skill_content.py` (shared helpers), `tests/gate/test_pitfalls_cache_and_concurrency.py`, `tests/gate/test_pitfalls_auth_and_sessions.py`, `tests/gate/test_pitfalls_data_and_validation.py`, `tests/gate/test_pitfalls_privacy_and_queues.py`, `tests/gate/test_package_authoring.py`, `tests/gate/test_testing_notes.py`, `tests/gate/test_readable_test_names.py`, `tests/gate/test_agent_field_learnings.py`, `tests/gate/test_spatie_learnings.py`, `tests/gate/test_skill_content_hygiene.py`, `tests/Profile/CiServicesTest.php`, `tests/Profile/HouseStyleNamingHintsTest.php`, and the amended `tests/Profile/S9d1GitleaksTest.php`.

## 1. How content is read

A rule counts only when one paragraph or bullet (one line of the file) carries all of its operative words, as in the earlier agent and docs gates. Patterns are case-insensitive, except all-caps tokens (`MUST`, `FAIL`, `SELECT`, `ESCAPE`, `CI`, `TTL`, `UPDATE`, `REPEATABLE READ`, `RESULT:`, `Important`), which match case-sensitively. The exact patterns are in the test files; the sections below name what each one requires.

- **Pitfalls** (`pitfall()`): the line is in a `resources/boost/skills/laravel-pitfalls/references/*.md` file. That file has a valid `Gap:` line (R1), and its section `## <file stem>` in the git-ignored `internal-docs/pitfall-sources.md` has a line citing the row as `skills-gaps row 101` or `skills-gaps rows 119, 120 and 151` (R2). The source half runs where `internal-docs/` exists (the builder's and the reviewer's checkout); a public clone and CI have none, as in the S4 gate. The Spatie config pitfall cites `spatie/guidelines-skills` instead of a row. Which reference (an existing one or a new file) is the builder's choice; a new file gets its `## <stem>` section in the sources file and a link in the SKILL.md index.
- **Testing notes** (`note()`, owner ruling: no new skill, one place): the line is in `resources/boost/skills/laravel-pitfalls/references/testing.md`, which has a valid `Gap:` line, a `## testing` section in `internal-docs/pitfall-sources.md` citing each row, and a link from the SKILL.md index. The agent-rule halves stay in the agent files. Boost's own skills are never edited (R4).
- **Verdicts** (`assert_verdict()`): a five-cell row in `laravel-package-verdicts/references/register.md`, a Use from the allowed set, the stated needles in Reason or Conditions, Checked on or after 2026-11-27.
- **Agent rules** (`line_in()` on the agent's own file).

## 2. Cache and concurrency (`test_pitfalls_cache_and_concurrency.py`)

Rows 111 (interleave at every store step; the double's add must be atomic; a blocking `block()` waits in-process), 112 (`Cache::pull()` is get then forget, not atomic; `Cache::add` or `Cache::lock()->get()`; `DatabaseStore::forget` returns true), 115 (remove the issued record so eviction of the marker cannot reopen it; a TTL, never forever; refuse the array store outside tests), 119 and 120 (the atomic-add drivers by class: RedisStore, MemcachedStore, DatabaseStore, DynamoDbStore, FileStore; unwrap FailoverStore through `cache.stores.<name>.stores`; never trust `method_exists`; StorageStore is get then put; `MemcachedStore::put` returns false; prune write-once keys; rate limit guest key writes; the file store on several servers), 121 (prune scheduled with `callAfterResolving(Schedule::class)`; a dedicated file store path), 131 (RateLimiter is not an exact counter under concurrency; add plus increment, Lua or a guarded UPDATE), 141 (changed rows, not matched rows, on MySQL; interleave between the read and the update with different values), 151 (throttles fail open on NullStore, ArrayStore, `FileStore::increment`; `DatabaseStore::increment` ignores expiry; the gap-lock deadlock under REPEATABLE READ; `attempts` default 1; `ON UPDATE CURRENT_TIMESTAMP`, use `dateTime`), 154 (an index alone does not stop the deadlock; 1213; plain read then update by primary key), 159 (several buckets: fixed order, stop at the first).

## 3. Auth and sessions (`test_pitfalls_auth_and_sessions.py`)

Rows 38 (HMAC over APP_KEY with a fixed label; length-prefix or JSON-encode against collisions; `APP_PREVIOUS_KEYS` rotation; morph map), 102 (`Login` fires for remember-me cookies; skip `viaRemember()`), 105 (`password.confirm` honors `password_timeout`, 3 hours; `password_confirmed_at`), 106 (pitfall half: `PasskeyUser`, `Passkeys::userModel()` and the migration FK, counter 0 on synced passkeys, no challenge storage, management routes with `password.confirm`, and `PasskeyVerified` and `PasskeyRegistered` carrying the user model with `SerializesModels`, so a queued listener holds only its class and key; no pitfall may say they carry the full user), 145 (guard the write of a framework session key by who is signed in; the Login timing), 148 (collation is case- and accent-insensitive; mail the stored address; `hash_equals` or a binary collation; the review checker's security lens names the stored address and collation), 150 (a remembered sign-in keeps the guest session; clear on every Login; test with a second member's remember cookie). Row 170 (revoking one device's remember-me): `logout()` cycles the single `remember_token` on every device, `logoutCurrentDevice()` does not; per-device revocation uses a companion cookie named after `getRecallerName()`; refuse a revoked device in the `Login` listener on `viaRemember()` with `logoutCurrentDevice()` (the guard sets its user before firing Login and returns it after, SessionGuard.php:195-205 and :702-721; skills-gaps row 178), and keep a middleware as the second line, since an opt-in middleware leaves uncovered routes open; no pitfall may say a listener cannot refuse; tell the remember path apart with `viaRemember() && getUser() === $event->user`, since `viaRemember` stays true after a failed recaller.

## 4. Data and validation (`test_pitfalls_data_and_validation.py`)

Rows 101 (`whereKey` with a raw string on Postgres and MySQL; normalize ids; a UUID-shaped id in tests), 103 (`filter_var(true, FILTER_VALIDATE_INT)`; `is_int` or `is_numeric` first), 107 (trailing newline, `\z` or `D`), 109 (DDEV's MariaDB 10.11 default against a MySQL CI; `web_environment` in a `config.*.yaml` override), 125 (explicit `ESCAPE`, sqlite; `str_starts_with` or a range), 128 pitfall half (DDL not rolled back on MySQL; per-test apps leak connections), 143 (`model:prune` without `--model` never finds a package model; the package schedules it), 164 skill half (Redis on DDEV's shared network, `ddev_default`; check `.ddev/` for the add-on; `ddev-<project>-redis`; a resolving name or a connect is no proof).

## 5. Privacy and queues (`test_pitfalls_privacy_and_queues.py`)

Rows 37 (a tripwire, never the guarantee; every field, ints included; tested false positives such as user agents and `::`; throw in development, drop or redact in production), 57 (paired must-still-be-caught cases; a dotted domain after `@`), 58 (every string the object carries, name and emitter; log only the position or key of a dropped value), 104 (a queued listener serializes the user's password hash and remember token; never queue, or a non-serializable adapter), 134 (a queued notification without `->locale()` renders in the worker's locale; read the fake's recorded locale), 149 (`ShouldBeEncrypted`; `failed_jobs`; `#[\SensitiveParameter]`).

## 6. Package authoring (`test_package_authoring.py`)

Pitfall rows: 39 (`tagged()` stops at the first throwing abstract; a registry with `register()`; a lazy closure), 50 and 59 (reflection with `hasProperty`, a public-API fallback and a canary; never `?? []`; an unexpected shape falls back and logs once), 132 (a Testbench script that throws exits 0; require a result marker), and 36 in any pitfall reference with its source line (every `illuminate/*` component in `require`; no `composer.lock` in a library; register versus boot; config validated at boot; `final` providers; publish tags).

Verdict rows: `laravel/passkeys` with Use exactly `depends` (rows 89, 106: pre-1.0, pin the minor), `spatie/laravel-package-tools` and `orchestra/testbench` (row 40, Use `use` or `depends`; `larastan/larastan` is already there with `use`), plus a line in the laravel-package-verdicts skill on `illuminate/*` versus `laravel/framework` in `require`.

## 7. Testing notes (`test_testing_notes.py`)

Every note is a line of `laravel-pitfalls/references/testing.md` (section 1), cited by its row in the `## testing` source section. Rows 33 (`@anonymous`; assert on the address, never a bare `@`), 42 (a write rule covers `save(`, `increment(`, `DB::table`; or a query-log listener; a grep test is advisory), 60 (`getPackageProviders` in the base TestCase; the false "not a singleton"), 108 (`TestCaseAlreadyInUse`), 130 (the racer: `Application::create`, a shared start time, a shared store not the array cache, exact counts, `RESULT:`), 135 (`mergeConfigFrom` merges the first level; set nested keys after registering), 144 (`@phpstan-impure` rather than suppressing; in testing.md or the builder), 153 (`withCredentials()` for cookies on JSON requests), 155 (a `_bin` collation for case-sensitive fixtures), 156 (`app()['env'] = 'production'`; `register(..., true)` reruns boot), 167 (the four resets on one line: `forgetGuards()`, `forgetDrivers()`, `session.store`, `flushQueuedCookies()`; `CookieValuePrefix`; a cookie jar per device), 168 (a single-file run loads no other file's helpers; namespaced classes under `tests/Support`), 171 (`travel()` moves Carbon, not file mtimes, so file sessions read back empty; prefer the database session driver), 175 (an in-suite `queue:work` passes `--memory`, because the worker's check reads the whole Pest process; `--stop-when-empty`), 177 (rendering a Boost guideline in a test: `Blade::render()` after hiding backticks and `<?php` behind Boost's placeholders; `setBasePath()` at a root holding the profile).

## 8. Readable test names (`test_readable_test_names.py`)

Rows 158, 162 and 163, for the gate writer, the builder and the testing notes (decisions log 2026-11-27):
- files named by feature; descriptions as sentences; R and AC ids in `->group(...)`; one line saying never a slice or round id in a file, helper, class, constant or comment name; gates run as `--group=`; global helpers with a prefix unique to their file (gate writer and testing notes);
- the gate writer no longer says `<Slice>GateTest`, "criterion id in the test name" or "prefix each with the slice id";
- a rename-only gate commit (`git diff -M`) moves the lock (gate writer or builder);
- the planner writes gates as `--group=` rather than a word filter, and its example drops `--filter=StaffLoginGateTest`;
- the testing notes: `--list-tests --group`; `->group()` chains anywhere (before `->with()` or `->throws()`); a rename script touches only the description and closing lines; split a gate file only with its helpers.

## 9. Agent rules (`test_agent_field_learnings.py`)

Gate writer: rows 130 (parallel or concurrent points to the racer), 141 (single-use gates interleave between the read and the update), 152 (a concurrency gate races every write path; "same cost" gets a test or a ruling), 160 (each fix red on its own; model each store semantic, increment creating a key or not), 164 (Redis preflight checks `.ddev/` for the add-on), 168 (shared helpers are `tests/Support` classes; probe the harness with framework-only code), 175 (a gate running `queue:work` passes `--memory`), 176 (in a test with several assertions, the new-content ones come first, and each printed red reason names new content, not an already-shipped part). Builder: rows 142 (a second guard, each with a test that disables the other), 161 (environment setup in an existing test, no assertion changed, named in the hand-back), 173 (the Revert-to-prove section describes the mutate script in one line: copy, substitute, assert it applied, run the tests, restore, `cmp`). Planner: row 164 (a development service comes with a slice that installs it). Deep reviewer: rows 146 (a constant, table-free `SELECT` for engine behavior; the database manual with its URL), 147 (partly is FAIL; `Test configuration: changed in <commit>, isolation kept or strengthened`; "checker type not registered" as a single-pass reason with the lenses named), 152 (a MUST no test pins is Important).

## 10. Spatie learnings (`test_spatie_learnings.py`, `HouseStyleNamingHintsTest.php`)

Source: spatie/guidelines-skills 1.1.0 (https://github.com/spatie/guidelines-skills/tree/1.1.0), `spatie-laravel-php` and `spatie-security` references, quoted in the test's docstring. Already shipped by S9d-1 and not gated here: the README skills.sh section and the coexistence section. Gated:
- the builder's Artisan command rule (progress and a summary);
- the core guideline's "never mix single-line and multi-line chaining";
- event (tense) and listener naming hints inside the core guideline's `@if ($houseStyle)` block and nowhere outside it; `HouseStyleNamingHintsTest` renders the guideline with Blade (backticks and `<?php` hidden as Boost 2.10's `RendersBladeGuidelines::renderContent()` does) against a project root: present with no profile, absent with `"house_style": false`;
- a pitfall line with `config/services.php` and `config()`, sourced to `spatie/guidelines-skills`, in a reference whose `Gap: covered partly by Boost (...)` line names `rules/config` (Boost's laravel-best-practices config rule) and Larastan's `noEnvCallsOutsideOfConfig`;
- the reviewer's Checks section requires an authorization test for every restricted route;
- a register row for `spatie/guidelines-skills` (`use` or `depends`, naming `house_style`).

## 11. Hygiene (`test_skill_content_hygiene.py`), green by design

`scripts/check_pitfalls.py` exits 0 (every pitfall reference names its gap), and no shipped skill, agent or the core guideline names a field-test project ("Auth Kit", "AuthKit", "auth-kit", "CouchGag"; R2 generalization, not on the deny list). Every pitfall reference is linked from the laravel-pitfalls SKILL.md index.

## 12. Amendment: S9d1GitleaksTest (row 169)

`plans no gitleaks Dockerfile for a project on the host runner` asserted `not->toContain('Dockerfile.gitleaks')` over the whole setup output, which also prints the diffs of the scripts the setup writes. It now asserts on the diff headers: `$this->diffPaths($output)` does not contain `.ddev/web-build/Dockerfile.gitleaks` (the `+++ b/` header). Green by design (S9d-1 is built); a reverted probe showed a DDEV project's diff headers do list the Dockerfile, so the host negative is not vacuous.

## 13. Row map

| Rows | Where |
|---|---|
| 33, 42, 60, 108, 130, 135, 144, 153, 155, 156, 167, 168, 171, 175, 177 | testing notes (130, 168, 175 also gate writer) |
| 37, 57, 58, 104, 134, 149 | privacy and queues |
| 38, 102, 105, 106, 145, 148, 150, 170 | auth and sessions (148 also review checker) |
| 36, 39, 40, 50 (pitfall recipe), 59, 89 (register row), 106 (verdict), 132 | package authoring |
| 101, 103, 107, 109, 125, 128 (pitfall half), 143, 164 | data and validation (164 also gate writer and planner) |
| 111 (pitfall recipe), 112, 115, 119, 120, 121, 131, 141, 151, 154, 159 | cache and concurrency (141 also gate writer) |
| 142, 146, 147, 152, 160, 161, 173, 176 | agent rules |
| 158, 162, 163 | readable test names |
| 157 | not gated: the rule shipped in S9c; the builder closes the row citing the S9c commit (owner ruling) |
| 1, 4, 5, 10, 12, 14, 15, 16, 32, 41, 51, 124, 127, 129, 133, 136, 140, 165, 166, 169 | closed by S9d-1 |
| 17, 25, 53, 65, 81, 82 | closed: "rest fixed in S9c" per their status |
| every other row up to 156 | closed by S9b or S9c |
| 172 | extra CI services (section 16) |
| 174 | unused (numbering collision) |

## 14. Constraints for the builder

- Budgets stay: a SKILL.md body at most 12 KB (the pitfalls index grows with new references), a listing at most 1,300 characters, an agent with its preloads at most 48 KB (the builder is at 39.1 KB, the checker at most 16 KB).
- `scripts/check.sh` stays green: the symbol check verifies every `Illuminate` class, facade, method and artisan command the new content names against the pinned `laravel/framework`; the deny-list check covers the published tree.
- R7 as amended: the new skill content never cites the pack's own tests (`ReadmesNeverCiteTests`, S9d-1).
- No gate test name contains "PHPStan" in any case (S9d-1 constraint, kept).

## 15. Pinned names

Names and placements this gate pins, accepted by the owner: pitfall content in `laravel-pitfalls/references/` (any file); testing notes in `laravel-pitfalls/references/testing.md`; package-author items in any pitfall reference; the source-line format `skills-gaps row N`; Artisan output in the builder; chaining in the core guideline; naming hints inside the core guideline's house-style block; `laravel.ci_services`, `REDIS_HOST` and a service key `redis` in the gate job; the authorization test in `laravel-reviewer.md` Checks.

## 16. Extra CI services (`CiServicesTest.php`)

Row 172: `"laravel": {"ci": true, "ci_services": ["redis"]}` gives the gate job a `redis` service whose image starts with `redis` and a `REDIS_HOST` env key; no "Ignoring unknown profile key: laravel.ci_services" line; a rerun says No changes; on `test_database: ddev` the `database` service stays beside it; without the key no redis service and no `REDIS_HOST` (green by design, paired with the red tests); a docs/profile.md line names `ci_services` and Redis. The image tag and env values are the builder's.

## 17. Reviewer gate reruns (`test_reviewer_gate_reruns.py`)

R17, G5. Gates are now written as `--group=<id>` or a test file path, so `laravel-reviewer.md` and `laravel-reviewer-deep.md` each carry, in one paragraph or bullet, the rerun allowance: `vendor/bin/pest` (or `ddev exec vendor/bin/pest`) narrowed by `--filter`, `--group` or a test file path, never an unfiltered run. They also carry the `Gates:` fallback (the plan's gate, else the CI test step) saying a gate in those forms is rerun too. The old "`ddev exec vendor/bin/pest` with `--filter`" allowance is gone. The reason string `claimed, not rerun (command not a filtered pest run)` stays, because the S9 round 2 gate pins it exactly; the S9 gates (`test_only_a_filtered_pest_run_is_rerun`, the `--filter ... runner` pattern) stay green with the new wording.
