"""Pitfalls: ids, env values, validator regexes, database engines, DDEV services, model pruning, LIKE.

Requirements R1, R2, R5 (edge validation, test isolation, local gate and CI parity, population). Gaps rows
101, 103, 107, 109, 125, 128 (the pitfall half), 143 and 164.
Contract: tests/SkillContent/CONTRACT.md, section "Data and validation".
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from skill_content import pitfall  # noqa: E402


class InputAtTheEdge(unittest.TestCase):
    def test_a_raw_string_id_against_an_integer_key(self):
        # Row 101
        pitfall(self, 101, r"whereKey", r"Postgres", r"MySQL",
                label="whereKey() with a raw string: Postgres throws, MySQL casts 1abc to 1")
        pitfall(self, 101, r"(ctype_digit|int > 0|positive int)", r"(normali[sz]|before)",
                label="normalize ids (an int above 0, or ctype_digit) before querying")
        pitfall(self, 101, r"UUID", r"test",
                label="test with a UUID-shaped id")

    def test_env_true_passes_integer_validation(self):
        # Row 103
        pitfall(self, 103, r"filter_var", r"FILTER_VALIDATE_INT", r"true",
                label="filter_var(true, FILTER_VALIDATE_INT) returns 1, so a boolean passes as 1")
        pitfall(self, 103, r"is_int", r"is_numeric",
                label="validate is_int or a numeric string before filter_var")

    def test_dollar_matches_before_a_trailing_newline(self):
        # Row 107
        pitfall(self, 107, r"trailing newline", r"\\z", r"(`D`|D modifier)",
                label="PCRE $ matches before a trailing newline; use \\z or the D modifier")

    def test_like_escapes_are_not_portable(self):
        # Row 125. The ESCAPE clause on SQLite is already in edge-validation; the new part is the alternative.
        pitfall(self, 125, r"str_starts_with", r"(stream|range)",
                label="for a prefix match prefer streaming with str_starts_with, or a range on the key, over LIKE")
        pitfall(self, 125, r"(?-i:ESCAPE)", r"sqlite",
                label="a LIKE escape needs an explicit ESCAPE clause; sqlite has no default escape character")


class EnginesAndServices(unittest.TestCase):
    def test_local_and_ci_must_test_the_same_engine(self):
        # Row 109
        pitfall(self, 109, r"MariaDB", r"10\.11", r"MySQL", r"(?-i:\bCI\b)",
                label="DDEV defaults to MariaDB 10.11 with no database block, while CI often starts mysql:8")
        pitfall(self, 109, r"web_environment", r"config\.\*\.yaml|override", r"(replac|merg)",
                label="web_environment in a config.*.yaml override replaces a person's own keys")

    def test_ddl_in_tests_and_leaked_connections(self):
        # Row 128, pitfall half
        pitfall(self, 128, r"DDL", r"MySQL", r"(not rolled back|implicit(ly)? commit)",
                label="DDL in a test on MySQL is not rolled back: it commits implicitly")
        pitfall(self, 128, r"connections", r"(leak|Too many connections)", r"(per test|each test|every test)",
                label="an app built per test leaks connections (Too many connections)")

    def test_redis_on_the_shared_ddev_network(self):
        # Row 164, skill half
        pitfall(self, 164, r"redis", r"(ddev_default|shared network)",
                label="the hostname redis resolves on DDEV's shared network to other projects' Redis")
        pitfall(self, 164, r"\.ddev/", r"redis", r"add-on",
                label="check .ddev/ for the Redis add-on before using Redis")
        pitfall(self, 164, r"ddev-<project>-redis|ddev-\{?project\}?-redis",
                label="address the project's own Redis as ddev-<project>-redis")
        pitfall(self, 164, r"(getent|successful connect|connects?)", r"(never|not)",
                label="a resolving hostname or a successful connect is no proof the project has Redis")


class PackageModels(unittest.TestCase):
    def test_model_prune_never_finds_a_package_model(self):
        # Row 143
        pitfall(self, 143, r"model:prune", r"--model", r"(package|app/Models)",
                label="model:prune without --model only finds app/Models, never a package's Prunable model")
        pitfall(self, 143, r"schedul", r"(package|Prunable)", r"--model",
                label="the package schedules model:prune --model itself, or documents the entry")


if __name__ == "__main__":
    unittest.main()
