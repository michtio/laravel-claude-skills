"""Gate test for slice S9d-1 (laravel-layer): the two outside tools, run for real.

Requirements R1, R2, R13. Owner rulings 2026-11-27: skills.sh as a second distribution channel next
to Composer and Boost, and an unused-public-code CI check chosen through the verdict register.
Contract: tests/S9d1/CONTRACT.md sections 14 and 15.

Commands run inside this repository's own DDEV project (`ddev exec`), never php, composer or npm on
the host; in CI (the CI variable set, no ddev) they run on the runner. Without either the class skips
with the reason, as test_s9b_ddev does.

skills.sh: the CLI `skills` (vercel-labs/skills) at the pinned SKILLS_CLI, released 2026-11-10, run on
`git archive HEAD` (what `npx skills add michtio/laravel-claude-skills` clones: tracked files only), so
the check sees the committed tree. Documented behavior used (docs/commands.md and
docs/creating-skills.md at v1.8.1): `skills add <local path>`, `--skill '*'`, `-a claude-code` installs
into `./.claude/skills/`, `-y` skips prompts, `--copy` copies instead of symlinking; discovery searches
the standard containers, then `skills.sh.json` `paths`, then recursively when nothing was found.

Unused public code: the CI workflow's step that runs PHPStan with shipmonk/dead-code-detector
(https://github.com/shipmonk-rnd/dead-code-detector, rules.neon) is read from
.github/workflows/ci.yml and run as written; it must pass on the pack, and the same command with the
planted fixture tests/Fixtures/s9d1-dead-code as its path must fail and name the unused method.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SKILLS_CLI = "skills@1.8.1"
SKILLS = REPO / "resources/boost/skills"
CI_WORKFLOW = REPO / ".github/workflows/ci.yml"
DEAD_CODE_FIXTURE = "tests/Fixtures/s9d1-dead-code"
HAVE_DDEV = shutil.which("ddev") is not None
IN_CI = bool(os.environ.get("CI"))


def plain(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text)


def run_shell(script: str, timeout: int = 900) -> subprocess.CompletedProcess:
    """Run a bash script inside the repo's DDEV web container, or on the CI runner."""
    if HAVE_DDEV:
        return subprocess.run(["ddev", "exec", "bash", "-c", script], cwd=REPO, capture_output=True, text=True, timeout=timeout)
    return subprocess.run(["bash", "-c", script], cwd=REPO, capture_output=True, text=True, timeout=timeout)


def shipped_skills() -> set:
    return {p.parent.name for p in SKILLS.glob("*/SKILL.md")}


@unittest.skipUnless(HAVE_DDEV or IN_CI, "needs ddev (or CI): npx never runs on the host")
class SkillsShInstall(unittest.TestCase):
    """Owner ruling: the pack's skills install through skills.sh, exactly the shipped set."""

    @classmethod
    def setUpClass(cls):
        work = "/tmp/lcs-s9d1-skills"
        cls.result = run_shell(
            f"set -e; rm -rf {work}; mkdir -p {work}/src {work}/project; "
            f"git archive HEAD | tar -x -C {work}/src; "
            f"cd {work}/project; npx -y {SKILLS_CLI} add {work}/src --skill '*' -a claude-code -y --copy; "
            f"echo '--- installed'; cd {work}/project/.claude/skills && find . -type f | sort"
        )
        out = plain(cls.result.stdout)
        cls.installed = out.split("--- installed", 1)[1].split() if "--- installed" in out else []

    def test_the_cli_installs_without_error(self):
        self.assertEqual(self.result.returncode, 0, plain(self.result.stdout + self.result.stderr)[-3000:])

    def test_exactly_the_shipped_skills_are_installed(self):
        self.assertTrue(shipped_skills(), "the pack ships no skill under resources/boost/skills")
        names = {path.split("/")[1] for path in self.installed if path.endswith("/SKILL.md") and path.count("/") == 2}
        self.assertEqual(names, shipped_skills(), "skills.sh installs the shipped skills and nothing else (no fixture skill)")

    def test_references_come_with_the_skills(self):
        for skill in shipped_skills():
            for ref in (SKILLS / skill / "references").glob("*.md"):
                self.assertIn(f"./{skill}/references/{ref.name}", self.installed, f"{skill}: references/{ref.name} not installed")


def dead_code_step() -> str:
    """The run line of the CI step that runs PHPStan with the dead-code rules, or ''."""
    if not CI_WORKFLOW.is_file():
        return ""
    for m in re.finditer(r"(?m)^\s*run:\s*(.+)$", CI_WORKFLOW.read_text(encoding="utf-8")):
        line = m.group(1).strip()
        if "phpstan" in line and re.search(r"(\s-c\s|--configuration[ =])", line):
            config = re.search(r"(?:-c\s+|--configuration[ =])(\S+)", line).group(1)
            path = REPO / config
            if path.is_file() and "vendor/shipmonk/dead-code-detector/rules.neon" in path.read_text(encoding="utf-8"):
                return line
    return ""


@unittest.skipUnless(HAVE_DDEV or (IN_CI and (REPO / "vendor/bin/phpstan").is_file()), "needs ddev, or CI with vendor installed")
class UnusedPublicCodeCheck(unittest.TestCase):
    def test_ci_runs_a_dead_code_phpstan_step(self):
        self.assertTrue(dead_code_step(), "ci.yml has no step running vendor/bin/phpstan -c <config> whose config includes vendor/shipmonk/dead-code-detector/rules.neon")

    def test_the_check_passes_on_the_pack(self):
        step = dead_code_step()
        self.assertTrue(step, "no dead-code step in ci.yml")
        r = run_shell(step)
        self.assertEqual(r.returncode, 0, plain(r.stdout + r.stderr)[-3000:])

    def test_the_check_reports_a_planted_unused_public_method(self):
        self.assertTrue((REPO / DEAD_CODE_FIXTURE / "S9d1Unused.php").is_file(), "the planted fixture is missing")
        step = dead_code_step()
        self.assertTrue(step, "no dead-code step in ci.yml")
        command = re.sub(r"\s+(src|tests)(?=\s|$)", "", step) + f" --error-format=raw {DEAD_CODE_FIXTURE}"
        r = run_shell(command)
        out = plain(r.stdout + r.stderr)
        self.assertNotEqual(r.returncode, 0, out[-2000:])
        self.assertIn("S9d1Unused::neverCalled", out)


if __name__ == "__main__":
    unittest.main()
