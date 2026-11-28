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
        (root / "phpunit.xml.dist").write_text(
            '<phpunit bootstrap="tests/bootstrap.php"><env name="DB_DATABASE" value="app_test" force="true"/></phpunit>\n')
        (root / "tests/bootstrap.php").write_text("<?php\n")
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
            "testbench.yaml": lambda r: (r / "testbench.yaml").write_text("env:\n  DB_DATABASE: app\n"),
            "config/database.php": lambda r: (r / "config").mkdir() or (r / "config/database.php").write_text("<?php return ['default' => 'mysql'];\n"),
            "tests/bootstrap.php": lambda r: (r / "tests/bootstrap.php").write_text("<?php putenv('DB_DATABASE=app');\n"),
        }
        for path, change in changes.items():
            with self.subTest(path=path), tempfile.TemporaryDirectory() as raw:
                project = Project(Path(raw) / "app")
                project.take()
                change(project.root)
                proc = project.verify()
                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                self.assertEqual(proc.stdout.strip(), f"changed: {path}")

    def test_the_bootstrap_comes_from_phpunit_xml_before_the_dist_file(self):
        with tempfile.TemporaryDirectory() as raw:
            project = Project(Path(raw) / "app")
            (project.root / "phpunit.xml").write_text('<phpunit bootstrap="tests/local.php"></phpunit>\n')
            (project.root / "tests/local.php").write_text("<?php\n")
            project.take()
            (project.root / "tests/local.php").write_text("<?php putenv('DB_DATABASE=app');\n")
            proc = project.verify()
            self.assertEqual((proc.returncode, proc.stdout.strip()), (1, "changed: tests/local.php"))

    def test_a_composer_bootstrap_under_vendor_is_not_watched(self):
        """Any composer install rewrites vendor/autoload.php, so watching it would disqualify every builder that adds a package."""
        with tempfile.TemporaryDirectory() as raw:
            project = Project(Path(raw) / "app")
            (project.root / "phpunit.xml.dist").write_text('<phpunit bootstrap="vendor/autoload.php"></phpunit>\n')
            (project.root / "vendor").mkdir()
            (project.root / "vendor/autoload.php").write_text("<?php // a\n")
            project.take()
            (project.root / "vendor/autoload.php").write_text("<?php // b\n")
            self.assertEqual(project.verify().returncode, 0)

    def test_bad_calls_exit_2(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            for label, args in {"no arguments": (), "unknown action": ("check", "--root", raw),
                                "missing snapshot": ("verify", "--root", raw, "--snapshot", str(tmp / "none.json")),
                                "missing root": ("snapshot", "--root", str(tmp / "nope"), "--out", str(tmp / "s.json"))}.items():
                with self.subTest(case=label):
                    self.assertEqual(guard(*args).returncode, 2)


class Wipers(unittest.TestCase):
    """R18: on a suite that is not isolated, a database-wiping trait anywhere under tests/ is found, a builder's new
    test file included, so the gate is never run against the configured database."""

    def test_each_wiping_trait_under_tests_is_named(self):
        for trait in ("RefreshDatabase", "DatabaseMigrations", "DatabaseTruncation", "LazilyRefreshDatabase"):
            with self.subTest(trait=trait), tempfile.TemporaryDirectory() as raw:
                project = Project(Path(raw) / "app")
                (project.root / "tests/Feature").mkdir()
                (project.root / "tests/Feature/NewTest.php").write_text(f"<?php\nuses({trait}::class);\n")
                proc = guard("wipers", "--root", str(project.root))
                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                self.assertEqual(proc.stdout.strip(), f"tests/Feature/NewTest.php: {trait}")

    def test_a_suite_without_wiping_traits_passes(self):
        with tempfile.TemporaryDirectory() as raw:
            project = Project(Path(raw) / "app")
            (project.root / "tests/Unit").mkdir()
            (project.root / "tests/Unit/MathTest.php").write_text("<?php\nit('adds', fn () => expect(1 + 1)->toBe(2));\n")
            proc = guard("wipers", "--root", str(project.root))
            self.assertEqual((proc.returncode, proc.stdout), (0, ""))


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

    def test_the_snapshot_is_taken_after_the_gate_commit_and_before_the_first_builder(self):
        text = (REPO / "resources/boost/skills/laravel-gated-build/SKILL.md").read_text(encoding="utf-8")
        snapshot = text.find("suite_guard.py snapshot")
        self.assertGreater(snapshot, text.find("## 2. Gate tests first"), "the snapshot is taken before the gate writer runs")
        self.assertLess(snapshot, text.find("**Run it:**"), "the snapshot is taken after the first builder runs")
        self.assertTrue(self.has("docs/outside-builders.md", r"snapshot", r"after the gate commit", r"before the first builder"))

    def test_wiping_traits_are_searched_again_before_every_gate_rerun(self):
        skill = "resources/boost/skills/laravel-gated-build/SKILL.md"
        self.assertTrue(self.has(skill, r"suite_guard\.py wipers", r"before (each|every) gate rerun",
                                 r"wiping trait on a not-isolated suite"))

    def test_the_report_names_a_change_that_survives_the_reset(self):
        self.assertTrue(self.has("resources/boost/skills/laravel-gated-build/references/report.md",
                                 r"Stopped: <path> changed by <name> survives the reset"))

    def test_the_brief_format_has_the_not_isolated_rule(self):
        self.assertTrue(self.has("docs/brief-format.md", r"not isolated", r"RefreshDatabase", r"never run"))


if __name__ == "__main__":
    unittest.main()
