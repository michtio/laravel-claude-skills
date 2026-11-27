Mode: team (conventions, security) · agents: 3 · static checks: phpstan 1 in changed files (1 old line in an unchanged file left out), pint clean

### Critical (must fix before merge)
None.

### Important (should fix)

[Important] app/Http/Controllers/OrderController.php:29 [larastan]
What: `$order->customer->email` reads a property on a nullable relation; `orders.customer_id` is nullable, so an order without a customer returns a 500.
Fix: Handle the null case: `$order->customer?->email`, or return 404 when the order has no customer.
Why: A guest order breaks the endpoint.
Evidence: Larastan: `app/Http/Controllers/OrderController.php:29:Cannot access property $email on App\Models\Customer|null.`; database/migrations/2026_11_01_000000_create_orders_table.php:12 makes customer_id nullable.

### Suggestions (worth discussing)

[Suggestion] app/Support/OrderFormatter.php:9
What: The temporary `$res` can be returned directly.
Fix: `return number_format(...)`.
Why: Style only; no check or guideline states it.
Evidence: app/Support/OrderFormatter.php:9.

### Dropped after challenge
- Missing authorization on `show`: refuted, `$this->authorize('view', $order)` is called at app/Http/Controllers/OrderController.php:26.

Challenge: 1 fresh checker, 2 findings upheld, 1 dropped.
