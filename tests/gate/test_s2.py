"""Gate tests for slice S2 (laravel-layer): Laravel symbol verifier.

Requirement R19, acceptance criterion AC29. Standard library only.
Run: python3 -m unittest discover -s tests/gate

Checker entry point (what scripts/check.sh calls):
    python3 scripts/laravel_source.py check <path>...
Exit 1 and `<file>:<line>` plus the symbol on a miss; exit 0 when all symbols resolve.
"""
from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
FIX = "evals/fixtures"
SKILL = "resources/boost/skills/laravel-transactions/SKILL.md"
CHECK = ["python3", "scripts/laravel_source.py", "check"]

# fixture -> (symbol text the output must contain, exact line of the symbol)
BAD = {
    "symbol-missing-method": ("Illuminate\\Support\\Facades\\DB::transactional()", 11),
    "symbol-missing-class": ("Illuminate\\Support\\Facades\\Transactor", 12),
    "symbol-missing-command": ("queue:explode", 12),
}


def run(cmd, timeout=300):
    return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=timeout)


def fixture_file(name: str) -> str:
    return f"{FIX}/{name}/{SKILL}"


def network_available() -> bool:
    try:
        r = subprocess.run(
            ["git", "ls-remote", "https://github.com/laravel/framework", "HEAD"],
            capture_output=True, text=True, timeout=30,
        )
        return r.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


class SymbolFixtures(unittest.TestCase):
    def test_fixture_lines_are_where_the_gate_says(self):
        for name, (symbol, line) in BAD.items():
            with self.subTest(fixture=name):
                lines = (REPO / fixture_file(name)).read_text(encoding="utf-8").splitlines()
                self.assertIn(symbol, lines[line - 1])

    def test_each_missing_symbol_fails_with_symbol_and_file_line(self):
        for name, (symbol, line) in BAD.items():
            with self.subTest(fixture=name):
                path = fixture_file(name)
                r = run(CHECK + [path])
                out = r.stdout + r.stderr
                self.assertEqual(r.returncode, 1, out)
                self.assertIn(symbol, out)
                self.assertIn(f"{path}:{line}", out)

    def test_valid_symbols_pass(self):
        r = run(CHECK + [fixture_file("symbol-valid")])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class PinnedData(unittest.TestCase):
    def test_tag_file_holds_a_release_tag(self):
        tag = REPO / "scripts/data/laravel-source-tag.txt"
        self.assertTrue(tag.is_file(), "scripts/data/laravel-source-tag.txt missing")
        self.assertRegex(tag.read_text(encoding="utf-8").strip(), r"^v\d+\.\d+\.\d+$")

    def test_index_has_db_facade_and_transaction_method(self):
        index = REPO / "scripts/data/laravel-source-index.tsv"
        self.assertTrue(index.is_file(), "scripts/data/laravel-source-index.tsv missing")
        rows = [ln.split("\t") for ln in index.read_text(encoding="utf-8").splitlines()]
        flat = [r for r in rows if r]
        self.assertTrue(
            any("Illuminate\\Support\\Facades\\DB" in r for r in flat),
            "no row for Illuminate\\Support\\Facades\\DB",
        )
        self.assertTrue(
            any("Illuminate\\Support\\Facades\\DB" in r and "transaction" in r for r in flat),
            "no row naming the transaction method on the DB facade",
        )


class CheckShWiring(unittest.TestCase):
    def test_check_sh_lists_the_three_must_fail_fixtures(self):
        text = (REPO / "scripts/check.sh").read_text(encoding="utf-8")
        for name in BAD:
            with self.subTest(fixture=name):
                self.assertRegex(text, rf"must_fail[^\n]*{re.escape(name)}")

    def test_check_sh_passes(self):
        self.assertTrue((REPO / "scripts/laravel_source.py").is_file(), "scripts/laravel_source.py missing")
        self.assertIn("laravel_source.py", (REPO / "scripts/check.sh").read_text(encoding="utf-8"))
        r = run(["sh", "scripts/check.sh"], timeout=600)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class Reproducibility(unittest.TestCase):
    def test_refresh_check_reproduces_committed_index(self):
        script = REPO / "scripts/refresh-laravel-data.sh"
        self.assertTrue(script.is_file(), "scripts/refresh-laravel-data.sh missing")
        if not network_available():
            self.skipTest("no network: git ls-remote https://github.com/laravel/framework failed")
        r = run(["bash", "scripts/refresh-laravel-data.sh", "--check"], timeout=900)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
