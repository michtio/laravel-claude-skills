"""Gate tests for slice S1 (laravel-layer): skeleton, both deliveries, package quality gate.

Contract: tests/gate/CONTRACT.md. Standard library only.
Run: python3 -m unittest discover -s tests/gate
"""
from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
FIX = "evals/fixtures"

BUDGET = ["python3", "bin/agent_budget.py"]
VALIDATE = ["bash", "bin/validate-skills.sh"]

# fixture -> (command, message substrings the output must contain)
BAD = {
    "agent-no-cap": (BUDGET, ["Agent tool without an 'At most N agents per run|review' line"]),
    "agent-checker-with-agent": (BUDGET, ["must not have the Agent tool"]),
    "agent-gate-writer-with-agent": (BUDGET, ["must not have the Agent tool"]),
    "agent-cap-6": (BUDGET, ["cap above 5"]),
    "agent-readonly-tinker": (BUDGET, ["must disallow mcp__laravel-boost__tinker"]),
    "skill-body-over-12kb": (VALIDATE, ["SKILL.md body is", "max 12288"]),
    "skill-listing-over-1300": (VALIDATE, ["description + when_to_use is", "max 1300"]),
}


def run(cmd, timeout=300):
    return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=timeout)


def frontmatter(path: Path) -> dict:
    parts = path.read_text(encoding="utf-8").split("---", 2)
    out = {}
    for line in parts[1].splitlines():
        m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


class FixtureSelfTests(unittest.TestCase):
    def test_bad_fixtures_exist(self):
        for name in BAD:
            self.assertTrue((REPO / FIX / name).is_dir(), name)

    def test_each_bad_fixture_fails_with_its_message(self):
        for name, (tool, needles) in BAD.items():
            with self.subTest(fixture=name):
                r = run(tool + ["--root", f"{FIX}/{name}"])
                out = r.stdout + r.stderr
                self.assertEqual(r.returncode, 1, out)
                for needle in needles:
                    self.assertIn(needle, out)

    def test_valid_fixture_passes_both_tools(self):
        for tool in (BUDGET, VALIDATE):
            with self.subTest(tool=tool[-1]):
                r = run(tool + ["--root", f"{FIX}/valid"])
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class PackageQualityGate(unittest.TestCase):
    def test_check_sh_passes_on_the_repo(self):
        r = run(["sh", "bin/check.sh"], timeout=600)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_check_sh_has_a_self_test_for_every_bad_fixture(self):
        text = (REPO / "bin/check.sh").read_text(encoding="utf-8")
        lines = text.splitlines()
        for name in BAD:
            with self.subTest(fixture=name):
                hit = [l for l in lines if l.lstrip().startswith("must_fail") and f"{FIX}/{name}" in l]
                self.assertTrue(hit, f"bin/check.sh has no must_fail line for {FIX}/{name}")

    def test_check_sh_gates_the_valid_fixture(self):
        text = (REPO / "bin/check.sh").read_text(encoding="utf-8")
        hit = [l for l in text.splitlines() if l.lstrip().startswith("gate") and f"{FIX}/valid" in l]
        self.assertTrue(hit, "bin/check.sh must run a gate on evals/fixtures/valid")


class PackageSkeleton(unittest.TestCase):
    def load(self, rel):
        p = REPO / rel
        self.assertTrue(p.is_file(), f"{rel} is missing")
        return json.loads(p.read_text(encoding="utf-8"))

    def test_plugin_json(self):
        data = self.load(".claude-plugin/plugin.json")
        self.assertNotIn("skills", data, "AD2: skills ship through Boost, never as plugin skills")
        agents = data.get("agents")
        self.assertIsInstance(agents, list)
        self.assertTrue(agents, "agents must list at least one file")
        for a in agents:
            self.assertIsInstance(a, str)
            self.assertTrue(a.endswith(".md"), f"agent path must be a .md file: {a}")

    def test_marketplace_json(self):
        data = self.load(".claude-plugin/marketplace.json")
        self.assertIsInstance(data, dict)

    def test_composer_json(self):
        data = self.load("composer.json")
        self.assertEqual(data.get("name"), "michtio/laravel-claude-skills")
        deps = {**data.get("require", {}), **data.get("require-dev", {})}
        self.assertEqual(deps.get("laravel/boost"), "^2.5")

    def test_pitfalls_stub_skill(self):
        p = REPO / "resources/boost/skills/laravel-pitfalls/SKILL.md"
        self.assertTrue(p.is_file(), "stub skill is missing")
        fm = frontmatter(p)
        self.assertEqual(fm.get("name"), "laravel-pitfalls")
        self.assertTrue(fm.get("description"), "description is required")

    def test_ci_workflow(self):
        p = REPO / ".github/workflows/ci.yml"
        self.assertTrue(p.is_file(), ".github/workflows/ci.yml is missing")
        text = p.read_text(encoding="utf-8")
        self.assertIn("bin/check.sh", text)
        self.assertIn("python3 -m unittest discover -s tests/gate", text)
        for action in ("actions/checkout", "actions/setup-python"):
            uses = re.findall(rf"uses:\s*{re.escape(action)}@(\S+)", text)
            self.assertTrue(uses, f"{action} is not used")
            for ref in uses:
                m = re.match(r"v(\d+)", ref)
                self.assertIsNotNone(m, f"{action}@{ref} must use a major tag (vN)")
                self.assertGreaterEqual(int(m.group(1)), 5, f"{action}@{ref} is below v5")

    def test_fixture_app_script_exists(self):
        p = REPO / "tests/gate/fixture-app.sh"
        self.assertTrue(p.is_file())


class SpikeNotes(unittest.TestCase):
    HEADINGS = [
        "Preload of a project skill from a plugin agent",
        "Boost MCP tool names",
        "Pest custom presets",
    ]

    @unittest.skipUnless((REPO / "internal-docs").is_dir(), "internal-docs/ absent (public clone or CI)")
    def test_spike_notes_record_three_results(self):
        p = REPO / "internal-docs/spikes/s1.md"
        self.assertTrue(p.is_file(), "internal-docs/spikes/s1.md is missing")
        sections = re.split(r"^#+\s+", p.read_text(encoding="utf-8"), flags=re.M)[1:]
        by_title = {s.splitlines()[0].strip(): s for s in sections}
        for h in self.HEADINGS:
            with self.subTest(heading=h):
                self.assertIn(h, by_title, f"heading missing: {h}")
                self.assertRegex(by_title[h], r"(?m)^Result:\s*\S", f"no 'Result:' line under: {h}")


if __name__ == "__main__":
    unittest.main()
