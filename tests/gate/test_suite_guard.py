"""The suite guard: the files that decide test isolation are the same before every gate rerun of outside code.

Requirement R18 (the gate runs on the outside builder's result exactly as for the package's own builder,
which never changes the test configuration to get green). Builder-added test (G3), beside the S10 gate: the
gated build decides isolation once, snapshots the files that decide it (git-ignored ones included, such as a
local phpunit.xml that overrides phpunit.xml.dist, or .env with the dev database name), and refuses to rerun
the gate when a builder created, changed or deleted one. Standard library only.

    python3 -m unittest discover -s tests/gate -p 'test_suite_guard.py'
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GUARD = REPO / "scripts/suite_guard.py"


def guard(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(GUARD), *args], capture_output=True, text=True, timeout=30)


class Project:
    def __init__(self, root: Path):
        self.root = root
        (root / "tests").mkdir(parents=True)
        (root / "phpunit.xml.dist").write_text('<env name="DB_DATABASE" value="app_test" force="true"/>\n')
        (root / "tests/Pest.php").write_text("<?php\n")
        (root / "tests/TestCase.php").write_text("<?php\n")
        (root / ".env").write_text("DB_DATABASE=app\n")
        self.snapshot = root.parent / "suite.json"

    def take(self) -> subprocess.CompletedProcess:
        return guard("snapshot", "--root", str(self.root), "--out", str(self.snapshot))

    def verify(self) -> subprocess.CompletedProcess:
        return guard("verify", "--root", str(self.root), "--snapshot", str(self.snapshot))


class Guard(unittest.TestCase):
    """R18."""

    def test_an_untouched_project_verifies(self):
        with tempfile.TemporaryDirectory() as raw:
            project = Project(Path(raw) / "app")
            self.assertEqual(project.take().returncode, 0)
            proc = project.verify()
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_each_created_changed_or_deleted_file_is_named(self):
        changes = {
            "phpunit.xml": lambda r: (r / "phpunit.xml").write_text('<env name="DB_DATABASE" value="app"/>\n'),
            "phpunit.xml.dist": lambda r: (r / "phpunit.xml.dist").write_text('<env name="DB_DATABASE" value="app"/>\n'),
            "tests/Pest.php": lambda r: (r / "tests/Pest.php").write_text("<?php uses(RefreshDatabase::class);\n"),
            "tests/TestCase.php": lambda r: (r / "tests/TestCase.php").unlink(),
            ".env": lambda r: (r / ".env").write_text("DB_DATABASE=app_test\n"),
            ".env.testing": lambda r: (r / ".env.testing").write_text("DB_DATABASE=app\n"),
        }
        for path, change in changes.items():
            with self.subTest(path=path), tempfile.TemporaryDirectory() as raw:
                project = Project(Path(raw) / "app")
                project.take()
                change(project.root)
                proc = project.verify()
                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                self.assertEqual(proc.stdout.strip(), f"changed: {path}")

    def test_bad_calls_exit_2(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            for label, args in {"no arguments": (), "unknown action": ("check", "--root", raw),
                                "missing snapshot": ("verify", "--root", raw, "--snapshot", str(tmp / "none.json")),
                                "missing root": ("snapshot", "--root", str(tmp / "nope"), "--out", str(tmp / "s.json"))}.items():
                with self.subTest(case=label):
                    self.assertEqual(guard(*args).returncode, 2)


class GatedBuildUsesTheGuard(unittest.TestCase):
    """R18: the skill snapshots before the first builder and verifies before every gate rerun; a non-isolated
    suite with a database-wiping trait is never run; the brief tells a builder the suite is not isolated."""

    def lines(self, path: str) -> list:
        file = REPO / path
        self.assertTrue(file.is_file(), f"{path} is missing")
        return [l for l in file.read_text(encoding="utf-8").splitlines() if l.strip()]

    def has(self, path: str, *patterns: str) -> bool:
        import re
        return any(all(re.search(p, l, re.I) for p in patterns) for l in self.lines(path))

    def test_the_skill_snapshots_and_verifies_the_suite(self):
        skill = "resources/boost/skills/laravel-gated-build/SKILL.md"
        self.assertTrue(self.has(skill, r"suite_guard\.py snapshot", r"before the first builder"))
        self.assertTrue(self.has(skill, r"suite_guard\.py verify", r"before (each|every) gate rerun", r"disqualif"))
        self.assertTrue(self.has(skill, r"RefreshDatabase", r"DatabaseMigrations", r"DatabaseTruncation",
                                 r"LazilyRefreshDatabase", r"(run nothing|never run)"))

    def test_the_brief_format_has_the_not_isolated_rule(self):
        self.assertTrue(self.has("docs/brief-format.md", r"not isolated", r"RefreshDatabase", r"never run"))


if __name__ == "__main__":
    unittest.main()
