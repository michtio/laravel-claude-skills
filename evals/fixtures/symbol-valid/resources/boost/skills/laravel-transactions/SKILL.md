---
name: laravel-transactions
description: Fixture skill that names only real laravel/framework symbols.
when_to_use: Use when checking the symbol verifier.
---

# Transactions

Wrap multi-row writes with `Illuminate\Support\Facades\DB::transaction()`.

Lock the row first with `Illuminate\Database\Query\Builder::lockForUpdate()`.

Run `php artisan migrate`, then start workers with `php artisan queue:work`.
