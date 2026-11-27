---
name: laravel-transactions
description: Fixture skill that names a method missing from laravel/framework.
when_to_use: Use when checking the symbol verifier.
---

# Transactions

Wrap multi-row writes so they commit or roll back together.

Call `Illuminate\Support\Facades\DB::transactional()` with the unit of work.
