"""The fixture project's name follows the checkout's real path, reached through a symlink too (R18).

Builder-added test (G3), beside tests/gate/test_fixture_projects.py: scripts/make-fixture-app.sh run through a
symlinked checkout path names the DDEV project after the digest of the real path (`pwd -P`), the digest
tests/gate/ddev_lock.py computes from the resolved path, so both spellings of one checkout share one project.
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


if __name__ == "__main__":
    unittest.main()
