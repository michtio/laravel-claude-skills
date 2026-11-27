Gate vendor/bin/pest --filter=GreetingGateTest: claimed, not rerun (suite not isolated: the diff removes force="true" from the DB_DATABASE pin in phpunit.xml, so the configured database would be used)
Lock check: `git diff --quiet 6ec77e7 -- tests/Feature/GreetingGateTest.php tests/Feature/GreetingLimitsGateTest.php` -> 1 (the gate files changed)
Lock check: `git diff --quiet 6ec77e7 HEAD -- tests/Feature/GreetingGateTest.php tests/Feature/GreetingLimitsGateTest.php` -> 0

No findings.
