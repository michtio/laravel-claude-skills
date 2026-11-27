"""Gate test for slice S6a (laravel-layer): runner guidance survives boost:update.

Requirement R4, acceptance criterion AC5. The Pest half (tests/Setup/) covers the
command's plan, apply, idempotence and detection; this file covers Boost itself.
Standard library only. Run: python3 -m unittest discover -s tests/gate
Needs ddev; skips with a reason without it. Never runs php on the host.

Contract (details in tests/Setup/SetupCommandTest.php): `php artisan claude-skills:setup --yes`
inside the fixture app (DDEV) writes .ai/guidelines/claude-skills-runner.md (contains
`ddev artisan`, `ddev composer`, `ddev npm`) and .ai/guidelines/boost/core.blade.php (Boost's
override of its core guideline, no host `php artisan`). After `boost:update`, CLAUDE.md carries
the DDEV commands, no host `php artisan route:list` line from Boost's core guideline, and the
runner guideline file is still there. CLAUDE.md is never edited by setup itself.
"""
from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

import ddev_lock

REPO = Path(__file__).resolve().parent.parent.parent
APP = REPO / "fixtures/app"
GUIDELINE = ".ai/guidelines/claude-skills-runner.md"
OVERRIDE = ".ai/guidelines/boost/core.blade.php"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


@unittest.skipUnless(shutil.which("ddev"), "needs ddev: Boost runs inside the fixture app's DDEV project, never on the host")
class RunnerGuidanceSurvivesBoostUpdate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._ddev_lock = ddev_lock.acquire()
        cls.addClassCleanup(ddev_lock.release, cls._ddev_lock)
        if not (APP / ".ddev/config.yaml").is_file():
            r = subprocess.run(["bash", str(REPO / "scripts/make-fixture-app.sh")],
                               cwd=REPO, capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError("make-fixture-app.sh failed: " + (r.stdout + r.stderr)[-2000:])
        subprocess.run(["ddev", "config", "--project-name=lcs-fixture-app"], cwd=APP, capture_output=True, text=True)  # keep the project registered
        subprocess.run(["ddev", "start"], cwd=APP, capture_output=True, text=True)

    def artisan(self, args: str, expect: int = 0):
        r = subprocess.run(["ddev", "exec", "bash", "-c", f"php artisan {args}"],
                           cwd=APP, capture_output=True, text=True)
        self.assertEqual(r.returncode, expect, f"artisan {args} exited {r.returncode}:\n" + (r.stdout + r.stderr)[-2000:])
        return r.stdout

    def setUp(self):
        self.saved = {n: read(APP / n) for n in (".mcp.json", GUIDELINE, OVERRIDE)}
        self.existed = {n: (APP / n).is_file() for n in self.saved}
        for n in (GUIDELINE, OVERRIDE):
            (APP / n).unlink(missing_ok=True)

    def tearDown(self):
        for n, text in self.saved.items():
            if self.existed[n]:
                (APP / n).write_text(text, encoding="utf-8")
            else:
                (APP / n).unlink(missing_ok=True)

    def test_setup_then_boost_update_keeps_ddev_guidance(self):
        self.artisan("boost:install --guidelines --skills --mcp --no-interaction")
        claude = APP / "CLAUDE.md"
        before_setup = read(claude)

        self.artisan("claude-skills:setup --yes")
        self.assertEqual(read(claude), before_setup, "setup must not edit CLAUDE.md")
        self.assertIn("ddev artisan", read(APP / GUIDELINE))
        self.assertTrue((APP / OVERRIDE).is_file(), "core guideline override missing")

        self.artisan("boost:update --no-discover --no-interaction")

        self.assertTrue((APP / GUIDELINE).is_file(), "boost:update lost the runner guideline")
        self.assertTrue((APP / OVERRIDE).is_file(), "boost:update lost the core override")
        text = read(claude)
        for command in ("ddev artisan", "ddev composer", "ddev npm"):
            self.assertIn(command, text, f"{command!r} missing from CLAUDE.md after boost:update")
        self.assertNotIn("`php artisan route:list`", text, "Boost's host php artisan guidance survived the override")

        self.artisan("claude-skills:setup --check")  # idempotent after boost:update: exit 0


if __name__ == "__main__":
    unittest.main()
