"""Gate test for slice S7 round 2 (laravel-layer): actionlint on a generated workflow.

Ruling 5: the generated .github/workflows/claude-skills-gate.yml must pass actionlint
(image rhysd/actionlint:1.7.7). Needs ddev (the setup runs through the package's
Testbench inside DDEV, never PHP on the host) and docker; skips with a reason without
either, or when the image cannot be pulled. Standard library only.
Run: python3 -m unittest discover -s tests/gate

The project is a copy of tests/Fixtures/app with a profile `{"version":1,"laravel":{"ci":true}}`
and a mysql `.env.example`, made under a temp directory of the repo (DDEV mounts the repo only)
and removed afterwards. Contract: tests/Profile/CONTRACT.md, section 11.
"""
from __future__ import annotations

import shutil
import subprocess
import unittest
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
FIXTURE = REPO / "tests/Fixtures/app"
IMAGE = "rhysd/actionlint:1.7.7"
WORKFLOW = ".github/workflows/claude-skills-gate.yml"


@unittest.skipUnless(shutil.which("ddev") and shutil.which("docker"), "needs ddev and docker")
class ActionlintOnGeneratedWorkflow(unittest.TestCase):
    def test_generated_workflow_passes_actionlint(self):
        name = ".lint-" + uuid.uuid4().hex[:8]
        project = REPO / name
        shutil.copytree(FIXTURE, project)
        try:
            (project / ".ai").mkdir(exist_ok=True)
            (project / ".ai/skills-profile.json").write_text('{"version":1,"laravel":{"ci":true}}\n')
            (project / ".env.example").write_text("DB_CONNECTION=mysql\n")

            run = subprocess.run(
                ["ddev", "exec", "vendor/bin/testbench", "claude-skills:setup", f"--path=/var/www/html/{name}", "--yes"],
                cwd=REPO, capture_output=True, text=True,
            )
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertTrue((project / WORKFLOW).is_file(), "the setup wrote no workflow")

            pull = subprocess.run(["docker", "pull", IMAGE], capture_output=True, text=True)
            if pull.returncode != 0:
                self.skipTest("cannot pull " + IMAGE + ": " + pull.stderr.strip()[-200:])

            lint = subprocess.run(
                ["docker", "run", "--rm", "-v", f"{project}:/repo", "-w", "/repo", IMAGE, "-color=false", WORKFLOW],
                capture_output=True, text=True,
            )
            self.assertEqual(lint.returncode, 0, lint.stdout + lint.stderr)
        finally:
            shutil.rmtree(project, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
