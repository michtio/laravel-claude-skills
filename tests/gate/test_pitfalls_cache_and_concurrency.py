"""Pitfalls: cache stores, single-use tokens, counters, throttles and deadlocks.

Requirements R1, R2, R5 (concurrency, idempotency, population). Gaps rows 111, 112, 115, 119, 120, 121,
131, 141, 151, 154 and 159, each with the Laravel 13 facts the row records.
Contract: tests/SkillContent/CONTRACT.md, section "Cache and concurrency".

Each item must be in a laravel-pitfalls reference (which carries a Gap: line) and cited by its row in
internal-docs/pitfall-sources.md.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from skill_content import pitfall  # noqa: E402


class InterleavingTests(unittest.TestCase):
    def test_atomicity_is_pinned_by_interleaving_at_every_store_step(self):
        # Row 111: the recipe and its limits
        pitfall(self, 111, r"interleav", r"(every|each) store (step|operation|call)",
                label="pin atomicity by running a second request before each store step of the first")
        pitfall(self, 111, r"interleav|test double|double", r"\badd\b", r"atomic",
                label="the test double's add must be atomic, as on a real driver")
        pitfall(self, 111, r"block\(\)", r"(in-process|in process|waits?)",
                label="a blocking block() lock waits in-process, so it cannot be interleaved")


class SingleUseTokens(unittest.TestCase):
    def test_cache_pull_is_never_a_single_use_consume(self):
        # Row 112
        pitfall(self, 112, r"(Cache::pull\(\)|`pull\(\)`|`pull`)", r"not atomic", r"\bget\b", r"\bforget\b",
                label="Cache::pull() is get then forget, not atomic on any driver")
        pitfall(self, 112, r"(Cache::add\(\)|`add\(\)`|Cache::add)", r"(Cache::lock\(\)->get\(\)|non-blocking lock)",
                label="single-use consumption needs an atomic add or a non-blocking lock around the read and delete")
        pitfall(self, 112, r"DatabaseStore::forget|forget\(\)", r"returns? true",
                label="DatabaseStore::forget returns true even when no row was deleted, so it cannot name the winner")

    def test_a_used_marker_that_is_evicted_cannot_reopen_the_token(self):
        # Row 115
        pitfall(self, 115, r"evict", r"marker", r"(issued record|issued entry|remove)",
                label="remove the issued record after use, so eviction of the used marker cannot reopen it")
        pitfall(self, 115, r"(?-i:\bTTL\b)", r"forever",
                label="single-use keys get a TTL, never forever")
        pitfall(self, 115, r"array store|ArrayStore|`array`", r"outside (of )?tests",
                label="refuse the array store outside tests for single-use or lock-like cache use")

    def test_only_drivers_with_an_atomic_add_are_trusted(self):
        # Rows 119 and 120: the allowlist by class, FailoverStore unwrapped, method_exists no proof
        pitfall(self, 120, r"RedisStore", r"MemcachedStore", r"DatabaseStore", r"DynamoDbStore", r"FileStore",
                label="the drivers with an atomic add, named by class")
        pitfall(self, 119, r"FailoverStore", r"unwrap",
                label="unwrap FailoverStore: the shipped failover store is database then array")
        pitfall(self, 120, r"cache\.stores\.\S+\.stores",
                label="unwrap a failover store through cache.stores.<name>.stores")
        pitfall(self, 119, r"method_exists", r"(never|not proof|no proof|is not enough|does not prove)",
                label="never trust method_exists($store, 'add')")
        pitfall(self, 119, r"StorageStore", r"\bget\b", r"\bput\b",
                label="StorageStore::add is itself get then put")

    def test_store_results_and_write_once_keys(self):
        # Row 119: put results, pruning, guest rate limits, the file store correction
        pitfall(self, 119, r"MemcachedStore", r"\bput\b", r"false",
                label="MemcachedStore::put answers false on failure without throwing; check the result")
        pitfall(self, 119, r"(write-once|written once|never read)", r"prune",
                label="the database and file drivers never drop a write-once key; plan a prune")
        pitfall(self, 119, r"rate.limit", r"guest",
                label="rate limit any endpoint that writes a key for a guest")
        pitfall(self, 119, r"file", r"(several|multiple|more than one) servers", r"(issuing server|refused)",
                label="with local files on several servers a challenge is refused everywhere but the issuing server")

    def test_a_package_prunes_its_write_once_keys(self):
        # Row 121
        pitfall(self, 121, r"prune", r"callAfterResolving", r"Schedule",
                label="a package that writes write-once keys ships a prune and schedules it with callAfterResolving(Schedule::class)")
        pitfall(self, 121, r"(file store|FileStore)", r"(sha1|hash)", r"dedicated",
                label="a file store cannot be scoped by key (sha1 paths); recommend a dedicated file store path")

    def test_a_guarded_single_use_update_is_proven_by_interleaving(self):
        # Row 141, pitfall half
        pitfall(self, 141, r"changed rows|rows changed", r"matched", r"MySQL",
                label="PDO's MySQL driver counts changed rows, not matched rows")
        pitfall(self, 141, r"interleav", r"(read|SELECT)", r"update", r"different",
                label="prove the guard by interleaving a second consume between the read and the update, with different written values")


class CountersAndThrottles(unittest.TestCase):
    def test_rate_limiter_is_not_an_exact_counter(self):
        # Row 131
        pitfall(self, 131, r"RateLimiter", r"(not an exact|not exact|loses? a hit|lost)", r"(concurren|parallel)",
                label="RateLimiter::hit() is not an exact counter under concurrency")
        pitfall(self, 131, r"\badd\b", r"increment", r"(?-i:(Lua|UPDATE))",
                label="an exact 'at most N' uses an atomic add plus increment, a Redis Lua script or a guarded UPDATE")

    def test_throttles_fail_open_on_stores_that_do_not_share_or_store(self):
        # Row 151 (a)
        pitfall(self, 151, r"(NullStore|ArrayStore|FileStore::increment)", r"(fails? open|lost|loses)",
                label="an add-plus-increment throttle fails open on NullStore, ArrayStore and FileStore")
        pitfall(self, 151, r"DatabaseStore::increment", r"expir",
                label="DatabaseStore::increment never checks the expiration")

    def test_several_buckets_count_in_a_fixed_order(self):
        # Row 159
        pitfall(self, 159, r"(several|two|multiple|more than one) (throttle )?(buckets|counters)", r"fixed order",
                r"(short-circuit|stop at the first|stops at the first)",
                label="with several throttle buckets, count in a fixed order and stop at the first over the limit")


class Deadlocks(unittest.TestCase):
    def test_burn_then_insert_takes_a_gap_lock(self):
        # Rows 151 (b, c) and 154
        pitfall(self, 151, r"gap.lock", r"deadlock", r"(?-i:REPEATABLE READ)",
                label="burn-then-insert in one transaction is the InnoDB gap-lock deadlock under REPEATABLE READ")
        pitfall(self, 151, r"attempts", r"retr", r"\b1\b",
                label="DB::transaction() retries a deadlock only with attempts above 1; the default is 1")
        pitfall(self, 151, r"ON UPDATE CURRENT_TIMESTAMP", r"dateTime",
                label="a NOT NULL timestamp gets ON UPDATE CURRENT_TIMESTAMP on older engines; use dateTime for expiry")
        pitfall(self, 154, r"index", r"deadlock", r"(alone|not the fix|does not stop|doesn't stop)",
                label="an index on the supersede predicate does not stop the deadlock")
        pitfall(self, 154, r"1213",
                label="retry on 1213, the deadlock error")
        pitfall(self, 154, r"plain read", r"(primary key|by key)",
                label="select the live ids with a plain read and update by primary key, then insert")


if __name__ == "__main__":
    unittest.main()
