# Single use, counters and throttles on cache stores and tables

Gap: covered partly by Boost (laravel-best-practices, rules/caching.md: "Use `Cache::add()` for atomic conditional writes"; "Configure failover cache stores in production")

Boost says `Cache::add()` writes atomically and that a failover store tries the next store when one throws. It does not say on which drivers `add` is really atomic, what the shipped failover store falls back to, how a single-use token or an exact counter breaks under two requests, or how to prove the fix. This reference covers single-use consumption (codes, challenges, magic links), counters and throttles, and the deadlock a "burn the old rows, insert the new one" write runs into.

## Pitfall 1: Cache::pull() is not a single-use consume

- `Cache::pull()` is `get` then `forget` (`Repository::pull`), not atomic on any driver: two requests can both read the value before either deletes it, and both pass.
- `DatabaseStore::forget` returns true even when no row was deleted, so the result of the delete cannot name the winner either.
- Single-use consumption needs an atomic marker, `Cache::add()` on a driver whose `add` is atomic (below), or a non-blocking lock around the read and the delete: `Cache::lock()->get()` returns false at once when another request holds it. Never a blocking `block()` around a consume that must refuse the loser.
- Pass a TTL: `Repository::add` calls the driver's own `add` only when a TTL is given; without one it runs `get` then `put` even on Redis.

```php
// One winner: the marker write is the consume.
if (! Cache::store('redis')->add('code-used:'.hash('sha256', $code), true, now()->addMinutes(15))) {
    throw new CodeAlreadyUsed();
}
```

## Pitfall 2: only some drivers have an atomic add

`Repository::add` calls the store's `add` when the method exists and otherwise falls back to `get` then `put`, which two requests can both win. Having the method is no proof either.

- The drivers with an atomic `add`, by class: RedisStore (a Lua script), MemcachedStore, DatabaseStore (`insertOrIgnore` on the key), DynamoDbStore (a conditional put) and FileStore (`flock`).
- No `add`, so `get` then `put`: ArrayStore, ApcStore, SessionStore, NullStore and any custom driver without one.
- StorageStore has an `add`, but it is itself `get` then `put`: never trust `method_exists($store, 'add')`, it does not prove atomicity.
- FailoverStore forwards `add` to whichever member answers, and the shipped `config/cache.php` defines `failover` as `database` then `array`: unwrap FailoverStore and judge every member, because an `instanceof ArrayStore` check never sees the array behind it.
- Unwrap a failover store through `cache.stores.<name>.stores` and check each named store's driver against the allowlist at boot, refusing the rest by class, for single use, locks and exact counters alike.
- Refuse the array store outside tests for single-use or lock-like cache use: it lives for one request under PHP-FPM, so every request starts with an empty store.
- With local files on several servers (the file store), a challenge is refused everywhere but the issuing server: the file store is atomic on one server only, so use a shared store for anything a load balancer spreads.

## Pitfall 3: an evicted marker reopens the token

A marker-only design ("the token is used when its used-marker exists") passes twice when the store evicts the marker early: Redis and Memcached evict under memory pressure (an LRU policy) while the issued record survives in another key or table.

- Remove the issued record after use, so eviction of the used marker cannot reopen it: the record is the token, the marker only arbitrates the race.
- Single-use keys get a TTL, never forever: a forever key is never evicted by expiry, and without a TTL the driver's atomic `add` is skipped (pitfall 1).
- Key by a hash of the token (`hash('sha256', $token)`), never the raw token, so a cache dump holds no live secret.

## Pitfall 4: write-once keys are never dropped

- The database and file drivers drop an expired entry only when that key is read again, so a key written once and never read (a used marker, an abandoned challenge) stays forever: plan a prune for write-once keys, or use a store with native expiry (Redis, Memcached, DynamoDB). `cache:prune-stale-tags` cleans Redis tags only.
- `MemcachedStore::put` returns false on failure without throwing: check the result of `put`, or an outage looks like a written key.
- Rate limit any endpoint that writes a key for a guest: an unthrottled guest endpoint fills the store, and on the database or file driver nothing removes it.
- A package that writes write-once keys ships a prune command for the database and file stores and schedules it itself with `callAfterResolving(Schedule::class, ...)` in its provider, so no consumer has to remember the schedule entry.
- A file store cannot be scoped by key, because its paths are sha1 hashes of the key with no key in the file: a prune can only delete expired files. Recommend a dedicated file store path for the package's keys, so its prune touches nothing else.

## Pitfall 5: RateLimiter is not an exact counter

`RateLimiter::hit()` (and `increment()`) runs `add(key, 0)`, `increment(key)`, then `put(key, $amount)` when its own `add` lost and the count reads back as `$amount`. Under concurrency a request that lost the `add` but increments first resets the counter with that `put`: RateLimiter is not an exact counter under concurrency, and parallel requests lose a hit (6 sends against a limit of 5 in field runs). It is fine for request throttling.

- An exact "at most N" uses an atomic add plus increment without the reset (`Cache::add($key, 0, $ttl)`, then `Cache::increment($key)` and compare), a Redis Lua script, or a guarded UPDATE (`UPDATE ... SET hits = hits + 1 WHERE key = ? AND hits < ?`, and check the affected rows).
- An add-plus-increment throttle fails open on stores that do not share or do not store: NullStore returns false from `put` and `increment`, ArrayStore lives for one request, and `FileStore::increment` is a read then a `put`, so parallel hits are lost. Check the throttle store's class at boot, as for single-use stores.
- `DatabaseStore::increment` never checks the expiration column: only `get` and `add` drop an expired row, so a counter past its window keeps counting until something reads it. Set the expiry again when the increment returns 1, or read before you count.
- With several throttle buckets (per address and per account), count them in a fixed order and stop at the first over the limit (short-circuit): counting all of them lets each bucket refuse a different request, so fewer than the limit get through.
- Prove a counter with parallel processes and exact expected counts (see [testing](testing.md), the racer): a sequential test passes either way.

## Pitfall 6: a guarded single-use UPDATE that only a lucky race proves

`UPDATE codes SET consumed_at = ? WHERE id = ? AND consumed_at IS NULL`, then "one affected row means I won", is the right guard. Proving it with parallel processes alone can pass by accident: PDO's MySQL driver reports changed rows, not matched rows, so two consumes in the same second that write the same timestamp both see 0 or 1 for reasons unrelated to the guard.

- Prove the guard by interleaving: hook the first consume's read (`DB::listen` on its SELECT), run a second consume between the read and the update, and give the two updates different written values (move the clock one second). Remove the `IS NULL` guard and the test goes red.

## Pitfall 7: burn then insert deadlocks

"Mark the earlier codes burned, then insert the new one" inside `DB::transaction()` is the InnoDB gap-lock deadlock under REPEATABLE READ: the UPDATE locks every index record it scans and the gaps between them, the gap locks of two transactions coexist, and each INSERT then waits on the other's gap lock (MySQL manual, innodb-locking and innodb-locks-set).

- An index on the supersede predicate does not stop the deadlock: an UPDATE that matches no row still takes a gap lock, and concurrent inserts into that gap deadlock (error 1213, "Deadlock found when trying to get lock").
- Select the live ids with a plain read, update by primary key only when there are any, then insert, as separate statements; or insert first and burn rows with a lower id.
- Or retry on 1213: `DB::transaction($callback, attempts: 3)`. `DB::transaction()` retries a deadlock only when `attempts` is above 1, and the default is 1.
- A NOT NULL `timestamp` column with no default gets `ON UPDATE CURRENT_TIMESTAMP` on MySQL 5.7 and on MariaDB before 10.10 (with `explicit_defaults_for_timestamp` off), so an expiry column moves on every update of the row: use `dateTime` for expiry columns.

## How to test it

- Atomicity without a shared service in CI: interleave at every store step. Wrap the store in a recording double that, before each store operation of the first request in turn (every store step), runs a complete second request. Every cut must give exactly one success. The double's `add` must be atomic, as on a real driver, or the test proves the double wrong instead of the code. A blocking `block()` lock waits in-process (the second request would block the test forever), so this recipe pins non-blocking locks and atomic adds only.
- A naive `Cache::pull()` consume fails that test; an atomic `add` marker or a `Cache::lock()->get()` passes it.
- Eviction: delete the used marker by hand after a successful consume, then consume again: it must be refused because the issued record is gone.
- Counters and deadlocks: parallel processes on the real engine, with exact counts; see the racer in [testing](testing.md).

## Check

Review only. For every single-use, lock-like or exact-count use of the cache, find the store, unwrap any failover store and confirm each member is on the atomic allowlist; for every guarded UPDATE, look for the interleaving test.
