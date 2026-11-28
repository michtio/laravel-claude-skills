"""The fixture project's name follows the checkout's real path, reached through a symlink too (R18).

Builder-added test (G3), beside tests/gate/test_fixture_projects.py: scripts/make-fixture-app.sh run through a
symlinked checkout path names the DDEV project after the digest of the real path (`pwd -P`), the digest
tests/gate/ddev_lock.py computes from the resolved path, so both spellings of one checkout share one project.
The app it makes is its own git repository with one commit (decisions log 2026-11-28, the gitleaks ruling), so
the app's secret scan never walks up into this package's history.
A fake `ddev` on PATH records the calls. Standard library only.

    python3 -m unittest discover -s tests/gate -p 'test_fixture_project_name.py'
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_fixture_projects import SCRIPT, FakeDdev, digest  # noqa: E402


class SymlinkedCheckout(unittest.TestCase):
    def test_a_symlinked_checkout_path_uses_the_real_path_digest(self):
        with FakeDdev() as fake:
            real = fake.tmp / "real-checkout"
            (real / "scripts").mkdir(parents=True)
            shutil.copy2(SCRIPT, real / "scripts/make-fixture-app.sh")
            link = fake.tmp / "linked-checkout"
            link.symlink_to(real)
            run = subprocess.run(["bash", str(link / "scripts/make-fixture-app.sh")], cwd=link,
                                 capture_output=True, text=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            expected = f"lcs-fixture-app-{digest(real)}"
            self.assertIn(f"name: {expected}\n", (real / "fixtures/app/.ddev/config.yaml").read_text(encoding="utf-8"))
            self.assertTrue(any(f"--project-name={expected}" in c for c in fake.calls()), fake.calls())


class OwnRepository(unittest.TestCase):
    def test_the_fixture_app_is_its_own_git_repository_with_one_commit(self):
        with FakeDdev() as fake:
            checkout = fake.tmp / "checkout"
            (checkout / "scripts").mkdir(parents=True)
            shutil.copy2(SCRIPT, checkout / "scripts/make-fixture-app.sh")
            subprocess.run(["git", "init", "-q"], cwd=checkout, check=True)
            run = subprocess.run(["bash", str(checkout / "scripts/make-fixture-app.sh")], cwd=checkout,
                                 capture_output=True, text=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            app = checkout / "fixtures/app"
            top = subprocess.run(["git", "-C", str(app), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
            self.assertEqual(Path(top.stdout.strip()).resolve(), app.resolve())
            count = subprocess.run(["git", "-C", str(app), "rev-list", "--count", "HEAD"], capture_output=True, text=True)
            self.assertEqual(count.stdout.strip(), "1", count.stderr)


if __name__ == "__main__":
    unittest.main()
