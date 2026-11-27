Gate flow: builder-written (no isolated suite)

No gate writer started: phpunit.xml pins no test database with forced env, so the suite is not isolated.

Tests written first, each failing first:
| test | red reason |
| it greets Ada | missing app/Services/GreetingService.php |
| it greets the world for an empty name | missing app/Services/GreetingService.php |

Built: app/Services/GreetingService.php. Pest: green, 2 passed.
Revert-to-prove: both tests red with the service removed, green with it.
Checker: skipped (small diff, nothing sensitive)
