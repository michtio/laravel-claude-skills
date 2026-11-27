Mode: single pass (small diff) · agents: 0 · static checks: phpstan 1 in changed files (1 old line in an unchanged file left out), pint clean

### Critical (must fix before merge)
None.

### Important (should fix)

[Important] app/Http/Controllers/OrderController.php:29 [larastan]
What: `$order->customer->email` reads a property on a nullable relation; `orders.customer_id` is nullable, so an order without a customer returns a 500.
Fix: Handle the null case: `$order->customer?->email`, or return 404 when the order has no customer.
Why: A guest order breaks the endpoint.
Evidence: Larastan: `app/Http/Controllers/OrderController.php:29:Cannot access property $email on App\Models\Customer|null.`; database/migrations/2026_11_01_000000_create_orders_table.php:12 makes customer_id nullable.

[Important] composer.json:8
What: `laravel/ui: avoid (Legacy Bootstrap authentication scaffolding; its own README calls it legacy)`. The diff adds it to `require`.
Fix: Use a current starter kit, or ask the owner for a ruling to keep `laravel/ui` on purpose.
Why: New code starts on a scaffold the register marks avoid.
Evidence: laravel-package-verdicts register, row `laravel/ui`; composer.json:8 in the diff.

### Suggestions (worth discussing)

[Suggestion] app/Support/OrderFormatter.php:9
What: The temporary `$res` can be returned directly.
Fix: `return number_format(...)`.
Why: Style only; no check or guideline states it.
Evidence: app/Support/OrderFormatter.php:9.

### Dropped after challenge
- Missing authorization on `show`: refuted, `$this->authorize('view', $order)` is called at app/Http/Controllers/OrderController.php:26.

Challenge: 1 fresh checker, 2 findings upheld, 1 dropped.
