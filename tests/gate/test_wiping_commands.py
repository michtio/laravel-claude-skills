"""The suite guard also finds database-wiping artisan commands in tests (R18; skills-gaps row 240, item 2).

On a suite that is not isolated, `suite_guard.py wipers` must find not only the four wiping traits but every
test that calls `migrate:fresh`, `migrate:refresh`, `migrate:reset` or `db:wipe`, in the `artisan(...)` form
(`$this->artisan(...)`) and the `Artisan::call(...)` form, with single or double quotes and with arguments
after the command. It prints `<path>: <command>` for such a file and exits 1. Commands that wipe nothing
(`migrate`, `migrate:status`) are not flagged, so a suite that only migrates is not stopped. The user docs
name the commands beside the traits. Standard library only.

    python3 -m unittest discover -s tests/gate -p 'test_wiping_commands.py'
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GUARD = REPO / "scripts/suite_guard.py"
COMMANDS = ("migrate:fresh", "migrate:refresh", "migrate:reset", "db:wipe")
FORMS = {
    "artisan, single quotes": "$this->artisan('{c}');",
    "artisan, double quotes, with options": "$this->artisan(\"{c}\", ['--force' => true]);",
    "Artisan::call, single quotes": "Artisan::call('{c}');",
    "Artisan::call, double quotes, with options": "\\Illuminate\\Support\\Facades\\Artisan::call(\"{c}\", ['--seed' => true]);",
}


def wipers(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(GUARD), "wipers", "--root", str(root)], capture_output=True, text=True, timeout=30)


def project(tmp: Path, body: str) -> Path:
    root = tmp / "app"
    (root / "tests/Feature").mkdir(parents=True)
    (root / "tests/Feature/NewTest.php").write_text(
        f"<?php\n\nuse Illuminate\\Support\\Facades\\Artisan;\n\nbeforeEach(function () {{\n    {body}\n}});\n", encoding="utf-8")
    return root


class WipingCommands(unittest.TestCase):
    """R18: a wiping command in any test file is found, a builder's new test included."""

    def test_each_wiping_command_in_each_call_form_is_named(self):
        for command in COMMANDS:
            for form, template in FORMS.items():
                with self.subTest(command=command, form=form), tempfile.TemporaryDirectory() as raw:
                    proc = wipers(project(Path(raw), template.format(c=command)))
                    self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                    self.assertEqual(proc.stdout.strip(), f"tests/Feature/NewTest.php: {command}")

    def test_commands_that_wipe_nothing_are_not_flagged(self):
        for body in ("$this->artisan('migrate');", "Artisan::call('migrate', ['--seed' => true]);",
                     "$this->artisan('migrate:status');", "Artisan::call(\"migrate:status\");"):
            with self.subTest(body=body), tempfile.TemporaryDirectory() as raw:
                proc = wipers(project(Path(raw), body))
                self.assertEqual((proc.returncode, proc.stdout), (0, ""), proc.stderr)

    def test_the_user_docs_name_the_wiping_commands_beside_the_traits(self):
        lines = (REPO / "docs/outside-builders.md").read_text(encoding="utf-8").splitlines()
        patterns = (r"RefreshDatabase", *(re.escape(c) for c in COMMANDS))
        self.assertTrue(any(all(re.search(p, line) for p in patterns) for line in lines),
                        "no line of docs/outside-builders.md names the wiping traits and the four wiping commands")


if __name__ == "__main__":
    unittest.main()
