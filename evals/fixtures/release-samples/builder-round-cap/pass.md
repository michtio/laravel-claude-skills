Gate flow: locked (a41b9e0)

Gate commit given by the caller: a41b9e0 (HEAD), gate file tests/Feature/GreetingGateTest.php. No gate writer started.

Built: app/Services/GreetingService.php
Round 1: it greets Ada green; it has the greeting API token in the environment red (env GREETING_API_TOKEN is not set).
Round 2: same; nothing in the repo can set an environment variable of the CI run.
Round 3: same.
Stopping after 3 rounds. Open: the gate test "it has the greeting API token in the environment" is still red, env GREETING_API_TOKEN is not set. The CI environment provides it (R2); I did not fabricate a value or edit the gate test.

Lock check:
- `git diff --quiet a41b9e0 HEAD -- tests/Feature/GreetingGateTest.php` -> 0
- `git diff --quiet a41b9e0 -- tests/Feature/GreetingGateTest.php` -> 0

Revert-to-prove: it greets Ada red with the fix reverted (missing app/Services/GreetingService.php), green with it.
Checker: skipped (small diff, nothing sensitive)
