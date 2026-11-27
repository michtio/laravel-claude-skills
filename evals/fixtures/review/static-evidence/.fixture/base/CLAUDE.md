# Orders

Laravel 13 app (namespace `App`). There is no DDEV project in this fixture. The static checks run from the project root:

- Larastan: `vendor/bin/phpstan analyse --no-progress --error-format=raw`
- Pint: `vendor/bin/pint --test`

Both are sh stand-ins (no PHP, no Composer install). `vendor/bin/phpstan` prints the raw error lines a real run would print for this tree: it reports `$order->customer->email` in `app/Http/Controllers/OrderController.php` as an access on a nullable relation, and one old error in `app/Legacy/Report.php` that was already there before the change under review. `vendor/bin/pint --test` is clean.
