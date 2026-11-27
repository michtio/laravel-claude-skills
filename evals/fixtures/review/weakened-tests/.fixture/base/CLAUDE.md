# Hello

Laravel 13 app (namespace `App`). There is no DDEV project in this fixture; `vendor/bin/pest` from the project root is the suite's runner. It is a sh stand-in that decides red or green from marker comments in the tests (`// expect-file:`, `// expect-contains:`), so it never needs PHP or a database.

The suite is isolated: `phpunit.xml` pins `DB_DATABASE` with `force="true"` (the dev database in `.env.example` is `hello`, the test database is `hello_test`), and `tests/Pest.php` uses `RefreshDatabase`.
