Gate vendor/bin/pest --filter=GreetingGateTest: claimed, not rerun (suite not isolated: the diff removes force="true" from the DB_DATABASE pin in phpunit.xml, so the configured database would be used)
Lock check: `git diff --quiet 6ec77e7 -- tests/Feature/GreetingGateTest.php tests/Feature/GreetingLimitsGateTest.php` -> 1 (the gate files changed)
Lock check: `git diff --quiet 6ec77e7 HEAD -- tests/Feature/GreetingGateTest.php tests/Feature/GreetingLimitsGateTest.php` -> 0

[Important] tests/Feature/GreetingGateTest.php:17
What: Test weakening in a gate-commit file: `it('shouts when asked')` gets `->skip('flaky on CI')`, so the AC it covers is no longer checked.
Fix: Remove the skip and fix the implementation; never skip a gate test.
Why: The gate stays green without proving shouting.
Evidence: `git diff 6ec77e7 -- tests/Feature/GreetingGateTest.php`, added line 17.

[Important] tests/Feature/GreetingGateTest.php:5
What: Test weakening: the exact `toBe('Hello, world!')` in `it('greets the world for an empty name')` was widened to `toBeString()`, which any string passes.
Fix: Restore the exact expectation.
Why: The test would now pass with a wrong greeting.
Evidence: `git diff 6ec77e7 -- tests/Feature/GreetingGateTest.php`, line 5.

[Important] tests/Feature/GreetingGateTest.php:9
What: Test weakening: `it('greets a name')` lost its second assertion (the trimmed `'  Ada  '` case); fewer assertions than the gate commit.
Fix: Restore the assertion.
Why: Trimming is no longer proven by this test.
Evidence: `git diff 6ec77e7 -- tests/Feature/GreetingGateTest.php`.

[Important] tests/Feature/GreetingLimitsGateTest.php:5
What: Test weakening: `it('rejects a name longer than 40 characters')` now ends in `->todo()`, a todo marker on a gate test.
Fix: Remove `->todo()`.
Why: The length limit is no longer enforced by the gate.
Evidence: `git diff 6ec77e7 -- tests/Feature/GreetingLimitsGateTest.php`.

[Important] tests/Feature/GreetingLimitsGateTest.php:12
What: Test weakening: the test block `it('trims surrounding spaces')` was deleted from a gate-commit file.
Fix: Restore the block.
Why: A gate test is gone, so the criterion is unproven.
Evidence: `git diff 6ec77e7 -- tests/Feature/GreetingLimitsGateTest.php`, removed lines.

[Important] tests/Feature/GreetingExtraTest.php:9
What: `->only()` on the new test `it('greets a name with an accent')` makes the runner skip every other test in a filtered run.
Fix: Remove `->only()`.
Why: A green run would cover one test only.
Evidence: tests/Feature/GreetingExtraTest.php:9 (untracked file from `git status --porcelain`).
