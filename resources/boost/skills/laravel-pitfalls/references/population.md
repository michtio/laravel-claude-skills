# Population: which rows the code actually ran over

Gap: covered partly by Boost (laravel-best-practices, rules/eloquent.md: "Apply global scopes sparingly")

Boost warns that a global scope silently changes every query, so admin screens, reports and jobs can miss rows unless the scope is removed. It does not cover the opposite failure, where the scope or filter quietly does not apply and the code runs over far more rows than intended. Nor does it cover the cases where a list that has to be complete is missing members and no test notices.

## Pitfall 1: a missing context reads everything

A tenant or owner scope that applies "when a tenant is set" protects requests, because a request always has one. A queued job, a console command or a scheduled task has no request. The scope then applies no constraint, and the query returns every tenant's rows. Writes usually fail loudly in that situation (the `creating` hook has no tenant id to fill). Reads do not fail: they return too much, and nothing errors.

### Fix

Make every job declare its context: capture the tenant id at dispatch and restore it around `handle()`, and refuse to dispatch or run a tenant job that has none. Keep an explicit allowlist, with a reason for each entry, for the jobs that really are cross-tenant (platform administration, dispatchers that enumerate tenants), and assert it in an architecture test. Never rely on the request context inside a job. There isn't one.

## Pitfall 2: an empty list skips the filter

```php
$ids = $this->accessibleProjectIds($user); // [] for a new member

$query->when($ids, fn ($q) => $q->whereIn('project_id', $ids)); // [] is falsy: no filter, every project
```

When "no restriction" and "no access" are both expressed through one value, they get mixed up. An empty array is falsy, so `when()` and `if ($ids)` skip the constraint, and the user who should see nothing sees everything.

### Fix

Give "no restriction" its own value (`null`) and branch on that explicitly. An empty list must still filter. `whereIn()` with an empty array matches no rows, which is what you want here:

```php
$ids = $this->accessibleProjectIds($user); // null = unrestricted, [] = nothing

if ($ids !== null) {
    $query->whereIn('project_id', $ids);
}
```

## Pitfall 3: an enumeration that drops members

Code that must reach every member of a set slowly picks up filters. A dispatcher iterates "all active accounts", and the retention or erasure job it drives never runs for suspended ones, so their personal data outlives its window. A registry of handlers drifts from the catalog shown on screen: a catalog entry with no handler fails when somebody opens it, and a handler with no catalog entry is code nobody can reach.

### Fix

Decide on purpose which population each job needs, and write that decision down where the query is. An obligation (retention, erasure, notifications the law requires) runs over everyone, with no standing filter. Pin each set with a test that compares in both directions, `expect($registered)->toEqualCanonicalizing($catalogued)`, never with a one-way `toContain`.

## Pitfall 4: a total that belongs to the page

A paginated list whose footer sums the rows on the current page shows a different "total" on every page. An export built on the paginated query stops at the page boundary and is short by however much is on the later pages, and nobody notices.

### Fix

Compute totals with a separate aggregate over the same filtered query, not over the page. Build exports from the unpaginated query and stream them (`lazyById()`, `chunkById()`).

```php
$filtered = Invoice::query()->whereBetween('issued_at', [$from, $to]);

$page = (clone $filtered)->orderBy('id')->paginate(50);
$total = (clone $filtered)->sum('total_cents'); // the window, not the page
```

## How to test it

- Dispatch a tenant job, run it with no ambient context, and assert it saw only its tenant's rows (seed two tenants). Remove the context restore and the test goes red: it sees both.
- Give a user an empty access list and assert the result is empty. Change the guard back to `when($ids, ...)` and the test goes red.
- Seed a suspended account with expired data and assert the retention job removes it.
- Assert the registry and the catalog are equal, not that one contains the other.
- Seed more rows than one page and assert the footer total equals the sum over all of them, on every page.

## Check

Review only. Whether a query should see one tenant or all of them, and which members a set has to include, is intent, not syntax. For every query in a job, command or report, ask which population it runs over, and how a missing context or an empty list changes that.
