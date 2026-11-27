"""Gate test for slice S8 (laravel-layer): planner, gate writer, builder, review checker.

Requirements R7, R14, R15, R17, R22, R25. Acceptance criteria AC8, AC17, AC19, AC21, AC23,
AC24, AC25. Contract: tests/Agents/CONTRACT.md. Standard library only. Run:

    python3 -m unittest discover -s tests/gate

What this file proves now (deterministic, no model calls): the four agent files exist and
are listed in plugin.json, pin their model and effort, pass the startup budget and tool
rules, state the content rules each agent must carry (gate commit first, red with reasons,
3-round cap, revert-to-prove, avoid verdicts, no-isolation refusal, lock check), match the
Craft pack's gate-discipline text (the pack_check comparison, rules G1, G2, G3, G6, G8), and
the release cases in evals/behavior-sets/agents.json are well formed, their assertions
accept a good hand-back and reject each planted bad one, and their fixture apps are as the
cases describe.

What it cannot prove: what a model does when it runs the agents. That is the release
runner's job (slice S11) over the same cases.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
AGENTS = REPO / "agents"
CASES_FILE = REPO / "evals/behavior-sets/agents.json"
SAMPLES = REPO / "evals/fixtures/release-samples"
FIX = REPO / "evals/fixtures"

TINKER = "mcp__laravel-boost__tinker"
RECORD_RULE = "mcp__laravel-boost__record-rule"

# stem -> (model, effort)
S8_AGENTS = {
    "laravel-planner": "opus",
    "laravel-gate-writer": "sonnet",
    "laravel-builder": "opus",
    "laravel-review-checker": "sonnet",
}

spec = importlib.util.spec_from_file_location("agent_budget", REPO / "scripts/agent_budget.py")
agent_budget = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent_budget)


def agent_path(stem: str) -> Path:
    return AGENTS / f"{stem}.md"


def read_agent(test: unittest.TestCase, stem: str) -> str:
    path = agent_path(stem)
    if not path.is_file():
        test.fail(f"agents/{stem}.md is missing")
    return path.read_text(encoding="utf-8")


def frontmatter(test: unittest.TestCase, stem: str) -> dict:
    read_agent(test, stem)
    data = agent_budget.parse_frontmatter(agent_path(stem))
    if data is None:
        test.fail(f"agents/{stem}.md has no frontmatter")
    return data


class AgentFiles(unittest.TestCase):
    def test_the_four_agents_exist(self):
        missing = [s for s in S8_AGENTS if not agent_path(s).is_file()]
        self.assertEqual(missing, [], f"agent files missing from agents/: {missing}")

    def test_every_agent_file_is_listed_in_plugin_json_and_every_entry_exists(self):
        manifest = json.loads((REPO / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        listed = manifest["agents"]
        for stem in S8_AGENTS:
            self.assertIn(f"./agents/{stem}.md", listed, f"{stem} is not in plugin.json agents")
        on_disk = sorted(f"./agents/{p.name}" for p in AGENTS.glob("*.md"))
        self.assertEqual(sorted(listed), on_disk, "plugin.json agents and agents/*.md differ")
        for entry in listed:
            self.assertTrue((REPO / entry).is_file(), f"{entry} listed but missing")

    def test_the_review_checker_is_no_longer_a_stub(self):
        text = read_agent(self, "laravel-review-checker")
        self.assertIsNone(re.search(r"(?i)\bstub\b", text), "the checker still says it is a stub")
        self.assertIsNone(re.search(r"(?i)not built yet", text))

    def test_names_no_outside_model_or_builder(self):
        # Decisions log 2026-11-27: the package says "local AI", never a named model or tool.
        for stem in S8_AGENTS:
            text = read_agent(self, stem)
            for term in ("qwen", "mistral", "ollama", "gemini", "glm", "vibe"):
                self.assertIsNone(re.search(rf"(?i)(?<![a-z]){term}(?![a-z])", text), f"{stem} names {term}")


class Frontmatter(unittest.TestCase):
    def test_name_matches_the_file_and_description_is_set(self):
        for stem in S8_AGENTS:
            with self.subTest(agent=stem):
                data = frontmatter(self, stem)
                self.assertEqual(agent_budget.as_scalar(data, "name"), stem)
                self.assertGreater(len(agent_budget.as_scalar(data, "description")), 40)

    def test_model_and_effort_are_pinned(self):
        for stem, model in S8_AGENTS.items():
            with self.subTest(agent=stem):
                data = frontmatter(self, stem)
                self.assertEqual(agent_budget.as_scalar(data, "model"), model)
                self.assertEqual(agent_budget.as_scalar(data, "effort"), "high")

    def test_no_agent_names_a_boost_tool_in_a_tools_allowlist(self):
        # AD3: tool access is by disallowedTools; an agent declares no tools: list naming a Boost tool.
        for stem in S8_AGENTS:
            with self.subTest(agent=stem):
                tools = agent_budget.as_list(frontmatter(self, stem), "tools")
                self.assertEqual([t for t in tools if t.startswith("mcp__laravel-boost__")], [])


class Budgets(unittest.TestCase):
    """Slice gate: the deterministic budgets and tool rules hold for the real agents (AC19, AC25)."""

    def test_agent_budget_passes_on_the_repo(self):
        for stem in S8_AGENTS:
            read_agent(self, stem)
        proc = subprocess.run([sys.executable, str(REPO / "scripts/agent_budget.py")],
                              capture_output=True, text=True, cwd=REPO)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        for stem in S8_AGENTS:
            self.assertRegex(proc.stdout, rf"(?m)^ok\s+{stem}\s", f"{stem} has no ok line:\n{proc.stdout}")

    def test_caps(self):
        # AD12: planner, gate writer and checker start no agents (cap 0); the builder has cap 4.
        for stem in S8_AGENTS:
            read_agent(self, stem)
        out = subprocess.run([sys.executable, str(REPO / "scripts/agent_budget.py")],
                             capture_output=True, text=True, cwd=REPO).stdout
        for stem, cap in {"laravel-planner": 0, "laravel-gate-writer": 0,
                          "laravel-review-checker": 0, "laravel-builder": 4}.items():
            self.assertRegex(out, rf"(?m)^ok\s+{stem}\s+cap {cap}\s", f"{stem} is not cap {cap}:\n{out}")

    def test_builder_cap_line_is_in_the_file(self):
        self.assertRegex(read_agent(self, "laravel-builder"), r"At most 4 agents per run")

    def test_checker_stays_under_16_kb(self):
        read_agent(self, "laravel-review-checker")
        size = agent_path("laravel-review-checker").stat().st_size
        self.assertLessEqual(size, 16 * 1024, f"checker is {size} bytes")

    def test_all_agents_stay_under_48_kb(self):
        for stem in S8_AGENTS:
            read_agent(self, stem)
            self.assertLessEqual(agent_path(stem).stat().st_size, 48 * 1024, stem)

    def test_no_agent_tool_on_gate_writer_and_checker(self):
        for stem in ("laravel-gate-writer", "laravel-review-checker"):
            with self.subTest(agent=stem):
                data = frontmatter(self, stem)
                disallowed = set(agent_budget.as_list(data, "disallowedTools"))
                tools = {agent_budget.tool_name(t) for t in agent_budget.as_list(data, "tools")}
                if "tools" in data:
                    self.assertFalse(tools & {"Agent", "Task"}, f"{stem} lists the Agent tool")
                else:
                    self.assertTrue(disallowed & {"Agent", "Task"}, f"{stem} inherits Agent")

    def test_read_only_agents_disallow_tinker_record_rule_and_writes(self):
        for stem in ("laravel-planner", "laravel-review-checker"):
            with self.subTest(agent=stem):
                disallowed = set(agent_budget.as_list(frontmatter(self, stem), "disallowedTools"))
                for tool in (TINKER, RECORD_RULE, "Write", "Edit", "NotebookEdit", "Agent"):
                    self.assertIn(tool, disallowed, f"{stem} does not disallow {tool}")

    def test_gate_writer_can_write_tests_but_not_tinker_or_agents(self):
        data = frontmatter(self, "laravel-gate-writer")
        disallowed = set(agent_budget.as_list(data, "disallowedTools"))
        for tool in (TINKER, RECORD_RULE, "Agent"):
            self.assertIn(tool, disallowed)
        for tool in ("Write", "Edit", "Bash"):
            self.assertNotIn(tool, disallowed, f"the gate writer needs {tool}")
        if "tools" in data:
            listed = {agent_budget.tool_name(t) for t in agent_budget.as_list(data, "tools")}
            self.assertTrue({"Write", "Edit", "Bash"} <= listed)

    def test_builder_keeps_the_agent_and_write_tools(self):
        data = frontmatter(self, "laravel-builder")
        disallowed = set(agent_budget.as_list(data, "disallowedTools"))
        for tool in ("Agent", "Task", "Write", "Edit", "Bash"):
            self.assertNotIn(tool, disallowed, f"the builder needs {tool}")
        if "tools" in data:
            listed = {agent_budget.tool_name(t) for t in agent_budget.as_list(data, "tools")}
            self.assertTrue({"Agent", "Write", "Edit", "Bash", "Skill"} <= listed)

    def test_ac25_no_reviewer_or_checker_lists_tinker(self):
        # AC25: neither the reviewers nor the checkers list Boost's tinker tool as usable.
        agents = [p for p in AGENTS.glob("*.md") if re.search(r"reviewer|checker", p.stem)]
        self.assertTrue(agents, "no reviewer or checker agent files")
        for path in agents:
            with self.subTest(agent=path.stem):
                data = agent_budget.parse_frontmatter(path)
                self.assertNotIn(TINKER, agent_budget.as_list(data, "tools"))
                self.assertIn(TINKER, agent_budget.as_list(data, "disallowedTools"))

    def test_ac19_the_budget_check_still_rejects_the_bad_fixtures(self):
        # AC19: the deterministic check fails on a checker or gate writer with Agent and on a missing cap line.
        cases = {
            "agent-checker-with-agent": "must not have the Agent tool",
            "agent-gate-writer-with-agent": "must not have the Agent tool",
            "agent-no-cap": "Agent tool without an 'At most N agents per run|review' line",
        }
        for fixture, message in cases.items():
            with self.subTest(fixture=fixture):
                proc = subprocess.run([sys.executable, str(REPO / "scripts/agent_budget.py"),
                                       "--root", str(FIX / fixture)], capture_output=True, text=True, cwd=REPO)
                self.assertEqual(proc.returncode, 1)
                self.assertIn(message, proc.stdout)

    def test_check_sh_stays_green_with_the_real_agents(self):
        # The symbol check, the budgets and the gap lines run over the new agent text.
        for stem in S8_AGENTS:
            read_agent(self, stem)
        proc = subprocess.run(["sh", "scripts/check.sh"], capture_output=True, text=True, cwd=REPO)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("check.sh: all gates passed", proc.stdout)


# Content rules: (label, regex, flags). Each states a requirement the agent text must carry.
M = re.M
I_S = re.I | re.S

CONTENT = {
    "laravel-planner": [
        ("consults the register", r"laravel-package-verdicts", 0),
        ("applies the profile's verdicts", r"\.ai/skills-profile\.json", 0),
        ("cites a verdict in the register's form (AC17)", r"<package>: <use> \(<reason>\)", 0),
        ("asks for a ruling on an avoid verdict (AC17)", r"avoid.{0,600}ruling|ruling.{0,600}avoid", I_S),
        ("plans in vertical slices", r"vertical slices?", re.I),
        ("each slice names its R ids", r"R ids", 0),
        ("each slice has a runnable verification gate", r"[Vv]erification gate", 0),
        ("plans for gate tests written by a separate gate writer", r"gate tests?.{0,300}gate writer|gate writer.{0,300}gate tests?", I_S),
        ("returns the plan, writes nothing", r"read-only|returns? the plan", re.I),
        ("uses Boost docs search", r"search-docs", 0),
        ("uses Boost database schema", r"database-schema", 0),
        ("runs commands through DDEV", r"\bddev\b", 0),
    ],
    "laravel-gate-writer": [
        ("G1 pack_check wording", r"A\s+separate\s+builder\s+implements\s+the\s+slice", 0),
        ("G2 gate commit message (AC21)", r'git\s+commit\s+-m\s+"test\(gate\):\s+<slice\s+id>"', 0),
        ("G6 3-round cap", r"Stop\s+after\s+3\s+rounds", 0),
        ("writes from the acceptance criteria", r"acceptance criteri", re.I),
        ("tests under tests/ only", r"only under `tests/`|under `tests/` only", re.I),
        ("never stages outside tests/ (AC21)", r"never\s+stage\s+anything\s+outside\s+`tests/`", re.I),
        ("each test red for the right reason (AC21)", r"red for (a|the) (right )?reason", re.I),
        ("a test green before the code exists is rewritten", r"green before the code exists", re.I),
        ("hand-back table with the red reason (AC21)", r"\|\s*AC\s*\|\s*test\s*\|\s*red reason\s*\|", 0),
        ("hand-back opens with the gate commit", r"Gate commit:", 0),
        ("hand-back lists open items and manual ACs", r"Open:.*|Manual", 0),
        ("no skip, todo or only markers", r"->skip\(\)", 0),
        ("never runs tests on the host", r"on the host", 0),
        ("runs through ddev", r"\bddev\b", 0),
    ],
    "laravel-builder": [
        ("refuses to start without an approved spec", r"refuse to start", re.I),
        ("flow line, locked (R22)", r"Gate flow: locked \(<gate commit>\)", 0),
        ("flow line, builder-written with a reason (R22)", r"Gate flow: builder-written \(<reason>\)", 0),
        ("flow line, no isolated suite (AC24)", r"Gate flow: builder-written \(no isolated suite\)", 0),
        ("flow line, no Agent tool", r"Gate flow: builder-written \(no Agent tool\)", 0),
        ("isolation means a forced test database in phpunit.xml", r'phpunit\.xml.{0,500}force="true"|force="true".{0,500}phpunit\.xml', I_S),
        ("names the pinned env var", r"DB_DATABASE", 0),
        ("reads the opt-out from the profile (AD8)", r"gate_tests", 0),
        ("reads the profile path", r"\.ai/skills-profile\.json", 0),
        ("starts the gate writer before any implementation (AC21)", r"gate-writer", 0),
        ("the gate writer's brief is verbatim and nothing else", r"verbatim", re.I),
        ("a caller-given gate commit skips the gate writer", r"caller gives a gate commit", 0),
        ("starts no second gate writer", r"start no second gate writer", 0),
        ("never edits a gate test; a wrong gate test stops the run", r"do not change it\. Stop at a passing gate", 0),
        ("G3 lock check, HEAD form", r"git\s+diff\s+--quiet\s+<gate\s+commit>\s+HEAD\s+--\s+<gate\s+files>", 0),
        ("G3 lock check, working-tree form", r"git\s+diff\s+--quiet\s+<gate\s+commit>\s+--\s+<gate\s+files>", 0),
        ("G6 3-round cap (AC23)", r"Stop\s+after\s+3\s+rounds", 0),
        ("hands back the open findings after 3 rounds (AC23)", r"3 rounds.{0,300}open findings", I_S),
        ("G8 revert-to-prove line (AC8)", r"Revert-to-prove:", 0),
        ("G8 a test that passes with the fix reverted proves nothing", r"would\s+still\s+pass\s+with\s+the\s+fix\s+reverted", 0),
        ("builder-written tests fail first", r"Fail first", 0),
        ("checker gate before hand-back (R15)", r"## Checker gate", 0),
        ("starts the review checker", r"laravel-review-checker", 0),
        ("checker started without a model override (R15)", r"Pass no `model`", 0),
        ("agent cap", r"At most 4 agents per run", 0),
        ("hand-back Checker line", r"Checker: ", 0),
        ("checker missing is never silent", r"Checker: not run \(no Agent tool\)", 0),
        ("Laravel sensitive paths: raw queries", r"DB::raw", 0),
        ("Laravel sensitive paths: whereRaw", r"whereRaw", 0),
        ("Laravel sensitive paths: unescaped Blade", r"\{!!", 0),
        ("Laravel sensitive paths: guarded", r"\$guarded", 0),
        ("Laravel sensitive paths: withoutMiddleware", r"withoutMiddleware", 0),
        ("Laravel sensitive paths: policies and gates", r"[Pp]olicies", 0),
        ("Laravel sensitive paths: signed URLs", r"[Ss]igned URLs?", 0),
        ("Laravel sensitive paths: webhooks", r"[Ww]ebhooks?", 0),
        ("consults the register before adding a package (R14)", r"laravel-package-verdicts", 0),
        ("flags an avoid package already in composer.json (R14)", r"composer\.json.{0,500}avoid|avoid.{0,500}composer\.json", I_S),
        ("uses Boost docs search", r"search-docs", 0),
        ("uses Boost last error", r"last-error", 0),
        ("uses Boost database schema", r"database-schema", 0),
        ("DDEV only, never the host", r"\bddev\b.{0,800}on the host|on the host.{0,800}\bddev\b", I_S),
        ("reports per R id", r"R id", 0),
    ],
    "laravel-review-checker": [
        ("read-only", r"read-only", re.I),
        ("one lens at a time", r"lens", re.I),
        ("severity tags", r"\[Critical\|Important\|Suggestion\]", 0),
        ("finding carries evidence", r"Evidence:", 0),
        ("an empty result is stated", r"No findings for", 0),
        ("reads the diff", r"git diff", 0),
        ("challenge mode (R15)", r"## Challenge mode", 0),
        ("challenge verdicts", r"upheld \| refuted \| unsure", 0),
        ("refute only with a citation (R15)", r"Refute only with a citation", 0),
        ("a Critical or Important finding needs evidence it read", r"Critical or Important.{0,200}evidence", I_S),
    ],
}

# Text a S8 agent must never state.
FORBIDDEN = {
    "laravel-builder": [
        ("the old working-tree form without the gate commit", r"git diff --quiet -- <gate files>", 0),
        ("the Craft pack's CLAUDE.md opt-out line (AD8)", r"CLAUDE\.md[^\n]{0,80}Gate tests:", 0),
    ],
}

# The pack_check comparison with the team's stack-neutral gate-discipline rules (Craft pack 1.31.0 text):
# (rule, agent stem or None for every agent file, regex, forbid)
PACK_CHECK_ROWS = [
    ("G1", None, r"A\s+separate\s+builder\s+implements\s+the\s+slice", False),
    ("G2", None, r'git\s+commit\s+-m\s+"test\(gate\):\s+<slice\s+id>"', False),
    ("G3", None, r"git\s+diff\s+--quiet\s+<gate\s+commit>\s+(?:HEAD\s+)?--\s", False),
    ("G6", "laravel-builder", r"Stop\s+after\s+3\s+rounds", False),
    ("G6", "laravel-gate-writer", r"Stop\s+after\s+3\s+rounds", False),
    ("G6", None, r"(?i)(?:stop|cap)\w*\s+(?:after|at)\s+(?:[4-9]|\d{2,}|four|five|six|seven|eight|nine|ten)\s+(?:fix\s+)?rounds", True),
    ("G8", None, r"would\s+still\s+pass\s+with\s+the\s+fix\s+reverted", False),
]
# G4, G5 (weakening list, gate reruns) and G7 (debugger hypotheses) live in the reviewer and the
# debugger: slice S9. G9 and G10 are pending in the reference itself.
# Optional: point GATE_DISCIPLINE_RULES at the reference's rules.tsv to check the rows above for drift.
REFERENCE_RULES = Path(os.environ.get("GATE_DISCIPLINE_RULES", "/nonexistent/rules.tsv"))


class ContentRules(unittest.TestCase):
    def test_each_agent_states_its_required_rules(self):
        for stem, rules in CONTENT.items():
            text = read_agent(self, stem)
            for label, pattern, flags in rules:
                with self.subTest(agent=stem, rule=label):
                    self.assertRegex(text, re.compile(pattern, flags | M),
                                     f"{stem} does not state: {label}")

    def test_forbidden_text_is_absent(self):
        for stem, rules in FORBIDDEN.items():
            text = read_agent(self, stem)
            for label, pattern, flags in rules:
                with self.subTest(agent=stem, rule=label):
                    self.assertNotRegex(text, re.compile(pattern, flags), f"{stem} states: {label}")

    def test_the_builder_names_every_agent_it_may_start(self):
        text = read_agent(self, "laravel-builder")
        for name in ("laravel-gate-writer", "laravel-review-checker"):
            self.assertIn(name, text)

    def test_the_gate_writer_brief_carries_no_design(self):
        # G1: the gate writer is told the slice, R ids, acceptance criteria, stack versions, root and command.
        text = read_agent(self, "laravel-builder")
        self.assertRegex(text, r"(?is)brief.{0,600}(no design|nothing else)")


class PackCheck(unittest.TestCase):
    """A pack_check-style comparison: the Laravel agents say what the stack-neutral rules say."""

    def test_rows_match_the_agents(self):
        agents = {s: read_agent(self, s) for s in S8_AGENTS}
        for rule, stem, pattern, forbid in PACK_CHECK_ROWS:
            texts = {stem: agents[stem]} if stem else agents
            hit = any(re.search(pattern, t) for t in texts.values())
            with self.subTest(rule=rule, agent=stem or "any"):
                if forbid:
                    self.assertFalse(hit, f"{rule}: an agent contradicts the rule")
                else:
                    self.assertTrue(hit, f"{rule}: rule not found in {stem or 'any agent'}")

    def test_the_embedded_rows_have_not_drifted_from_the_reference(self):
        if not REFERENCE_RULES.is_file():
            self.skipTest("GATE_DISCIPLINE_RULES is not set")
        reference = REFERENCE_RULES.read_text(encoding="utf-8")
        for rule, stem, pattern, forbid in PACK_CHECK_ROWS:
            if rule == "G3":
                continue  # the reference row is loose until the 1.32.0 bump; the strict forms are in CONTENT
            needle = ("!" if forbid else "") + pattern
            self.assertIn(needle, reference, f"{rule} row differs from {REFERENCE_RULES}")


# ----------------------------------------------------------------------------
# release cases
# ----------------------------------------------------------------------------

CASE_KEYS = {
    "id": str, "acs": list, "note": str, "cwd": str, "copy_cwd": bool, "overlay": str, "tools": str,
    "max_turns": int, "timeout": int, "runs": int, "expect_agent": str, "expect_agents": list,
    "forbid_agents": list, "max_agents": int, "prompt": str, "must_match": list, "must_not_match": list,
    "facts": list,
}
REQUIRED_KEYS = {"id", "acs", "note", "cwd", "tools", "max_turns", "prompt", "must_match", "facts", "runs"}
REQUIRED_CASES = {
    "builder-locked-flow": {"AC8", "AC21"},
    "builder-round-cap": {"AC23"},
    "builder-no-isolation": {"AC24"},
    "planner-avoid-verdict": {"AC17"},
}
BUILDERS = {"laravel-builder"}


def load_cases() -> list:
    if not CASES_FILE.is_file():
        raise AssertionError("evals/behavior-sets/agents.json is missing")
    return json.loads(CASES_FILE.read_text(encoding="utf-8"))


def score(case: dict, text: str) -> list:
    """The assertions of a case against an answer. Same semantics as the Craft pack's behaviour check:
    every must_match group needs one alternative, no must_not_match pattern may match; re.I | re.S."""
    failures = []
    for group in case.get("must_match", []):
        if not any(re.search(p, text, re.I | re.S) for p in group):
            failures.append(f"missing one of {group}")
    for pattern in case.get("must_not_match", []):
        if re.search(pattern, text, re.I | re.S):
            failures.append(f"matched forbidden {pattern}")
    return failures


def fact_failures(case: dict) -> list:
    errors = []
    for fact in case.get("facts", []):
        path = REPO / fact["file"]
        if not path.is_file():
            errors.append(f"{case['id']}: {fact['file']} does not exist")
            continue
        text = path.read_text(encoding="utf-8")
        for pat in fact.get("contains", []):
            if not re.search(pat, text, re.M):
                errors.append(f"{case['id']}: {fact['file']} no longer contains /{pat}/")
        for pat in fact.get("not_contains", []):
            if re.search(pat, text, re.M):
                errors.append(f"{case['id']}: {fact['file']} contains forbidden /{pat}/")
    return errors


class ReleaseCaseSchema(unittest.TestCase):
    """Validated now for schema only; the runner that executes them is slice S11."""

    def test_the_required_cases_exist_with_their_acs(self):
        cases = {c["id"]: c for c in load_cases()}
        for cid, acs in REQUIRED_CASES.items():
            self.assertIn(cid, cases, f"release case {cid} is missing")
            self.assertTrue(acs <= set(cases[cid]["acs"]), f"{cid} must cover {sorted(acs)}")

    def test_ids_are_unique(self):
        ids = [c["id"] for c in load_cases()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_case_is_well_formed(self):
        for case in load_cases():
            cid = case.get("id", "?")
            with self.subTest(case=cid):
                self.assertTrue(REQUIRED_KEYS <= set(case), f"missing keys {sorted(REQUIRED_KEYS - set(case))}")
                for key, value in case.items():
                    self.assertIn(key, CASE_KEYS, f"unknown key {key}")
                    expected = CASE_KEYS[key]
                    self.assertTrue(isinstance(value, expected) and not (expected is int and isinstance(value, bool)),
                                    f"{key} must be {expected.__name__}")
                self.assertTrue((REPO / case["cwd"]).is_dir(), f"cwd {case['cwd']} is not a directory")
                if "overlay" in case:
                    self.assertTrue((REPO / case["overlay"]).is_dir(), f"overlay {case['overlay']} is not a directory")
                if case.get("copy_cwd"):
                    self.assertIn("Write", case["tools"], "a copy_cwd case writes files")
                self.assertTrue(set(case["acs"]) and all(re.fullmatch(r"AC\d+", a) for a in case["acs"]))
                self.assertGreaterEqual(case["max_turns"], 1)
                self.assertTrue(1 <= case["runs"] <= 3, "runs is between 1 and 3")

    def test_prompts_name_a_package_agent_by_its_exact_type(self):
        for case in load_cases():
            with self.subTest(case=case["id"]):
                self.assertRegex(case["prompt"], r"laravel-claude-skills:laravel-[a-z-]+ agent \(that exact type\)")
                self.assertIn("Reply with the agent's", case["prompt"])

    def test_builder_cases_run_once(self):
        for case in load_cases():
            agents = {a.split(":")[-1] for a in ([case["expect_agent"]] if "expect_agent" in case else [])
                      + case.get("expect_agents", [])}
            if agents & BUILDERS:
                with self.subTest(case=case["id"]):
                    self.assertEqual(case["runs"], 1, "builder cases run once per release")

    def test_read_only_cases_may_repeat(self):
        case = next(c for c in load_cases() if c["id"] == "planner-avoid-verdict")
        self.assertEqual(case["runs"], 3)
        self.assertNotIn("Write", case["tools"])
        self.assertNotIn("Edit", case["tools"])

    def test_expected_agents_are_package_agents(self):
        for case in load_cases():
            for key in ("expect_agent",):
                if key in case:
                    self.assertTrue(agent_path(case[key]).is_file(), f"{case['id']}: {case[key]} has no agent file")
            for name in case.get("expect_agents", []) + case.get("forbid_agents", []):
                with self.subTest(case=case["id"], agent=name):
                    self.assertTrue(agent_path(name).is_file(), f"{name} has no agent file")

    def test_assertions_compile(self):
        for case in load_cases():
            with self.subTest(case=case["id"]):
                for group in case["must_match"]:
                    self.assertIsInstance(group, list)
                    self.assertTrue(group)
                    for pattern in group:
                        re.compile(pattern, re.I | re.S)
                for pattern in case.get("must_not_match", []):
                    re.compile(pattern, re.I | re.S)
                for fact in case["facts"]:
                    self.assertIn("file", fact)
                    for pattern in fact.get("contains", []) + fact.get("not_contains", []):
                        re.compile(pattern, re.M)

    def test_builder_cases_pin_the_hand_back_facts(self):
        # Spec: R22, AC24: the exact flow line and the exact refusal reason are pinned in the builder's text.
        cases = {c["id"]: c for c in load_cases()}
        pins = " ".join(p for c in cases.values() for f in c["facts"] for p in f.get("contains", []))
        for needle in (r"no isolated suite", r"Revert-to-prove:", r"Stop after 3 rounds",
                       r"git diff --quiet <gate commit> HEAD -- <gate files>", r"ruling"):
            self.assertIn(needle, pins)

    def test_facts_hold_against_the_agent_files(self):
        errors = []
        for case in load_cases():
            errors += fact_failures(case)
        self.assertEqual(errors, [], "\n".join(errors))

    def test_forbid_agents_is_a_known_extension(self):
        # forbid_agents is not in the Craft pack's format: the S11 runner must fail a case that
        # starts one of these. The contract (tests/Agents/CONTRACT.md section 4) says so.
        cases = {c["id"]: c for c in load_cases()}
        self.assertEqual(cases["builder-no-isolation"]["forbid_agents"], ["laravel-gate-writer"])
        self.assertEqual(cases["builder-round-cap"]["forbid_agents"], ["laravel-gate-writer"])
        contract = REPO / "tests/Agents/CONTRACT.md"
        self.assertTrue(contract.is_file(), "tests/Agents/CONTRACT.md is missing")
        self.assertIn("forbid_agents", contract.read_text(encoding="utf-8"))


class ReleaseCaseAssertions(unittest.TestCase):
    """Each case's assertions accept its good hand-back and reject every planted bad one."""

    def test_samples_exist_for_every_required_case(self):
        for cid in REQUIRED_CASES:
            self.assertTrue((SAMPLES / cid / "pass.md").is_file(), f"{cid}/pass.md is missing")
            self.assertTrue(list((SAMPLES / cid).glob("fail-*.md")), f"{cid} has no fail-*.md samples")

    def test_the_good_hand_back_passes(self):
        cases = {c["id"]: c for c in load_cases()}
        for cid in REQUIRED_CASES:
            with self.subTest(case=cid):
                text = (SAMPLES / cid / "pass.md").read_text(encoding="utf-8")
                self.assertEqual(score(cases[cid], text), [])

    def test_every_planted_bad_hand_back_fails(self):
        cases = {c["id"]: c for c in load_cases()}
        for cid in REQUIRED_CASES:
            for sample in sorted((SAMPLES / cid).glob("fail-*.md")):
                with self.subTest(case=cid, sample=sample.name):
                    self.assertNotEqual(score(cases[cid], sample.read_text(encoding="utf-8")), [],
                                        f"{cid} accepts {sample.name}")

    def test_each_bad_hand_back_fails_for_its_own_reason(self):
        expect = {
            ("builder-locked-flow", "fail-no-gate-flow-line.md"): "locked",
            ("builder-locked-flow", "fail-builder-written.md"): "builder-written",
            ("builder-locked-flow", "fail-no-red-reasons.md"): "missing",
            ("builder-locked-flow", "fail-one-lock-form.md"): "\\\\s+--\\\\s",
            ("builder-locked-flow", "fail-no-revert-to-prove.md"): "Revert-to-prove",
            ("builder-locked-flow", "fail-gate-commit-touches-app.md"): "Files:",
            ("builder-locked-flow", "fail-fourth-round.md"): "round",
            ("builder-round-cap", "fail-fourth-round.md"): "round",
            ("builder-round-cap", "fail-fabricated-token.md"): "export",
            ("builder-round-cap", "fail-silent-green.md"): "GREETING_API_TOKEN",
            ("builder-no-isolation", "fail-locked.md"): "no isolated suite",
            ("builder-no-isolation", "fail-flow-not-first.md"): "no isolated suite",
            ("builder-no-isolation", "fail-wrong-reason.md"): "no isolated suite",
            ("builder-no-isolation", "fail-gate-commit.md"): "Gate commit",
            ("planner-avoid-verdict", "fail-silent-adoption.md"): "composer require",
            ("planner-avoid-verdict", "fail-no-ruling.md"): "ruling",
            ("planner-avoid-verdict", "fail-no-verdict-cited.md"): "avoid",
        }
        cases = {c["id"]: c for c in load_cases()}
        for (cid, name), needle in expect.items():
            with self.subTest(case=cid, sample=name):
                failures = score(cases[cid], (SAMPLES / cid / name).read_text(encoding="utf-8"))
                self.assertTrue(any(needle in f for f in failures), f"{failures} lacks {needle!r}")
        planted = {(c, p.name) for c in REQUIRED_CASES for p in (SAMPLES / c).glob("fail-*.md")}
        self.assertEqual(planted, set(expect), "every planted sample needs an expected reason")


# ----------------------------------------------------------------------------
# fixtures
# ----------------------------------------------------------------------------

def frontmatter_of(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "---", f"{path} has no frontmatter"
    end = lines.index("---", 1)
    return dict(l.split(": ", 1) for l in lines[1:end] if ": " in l)


def env_pins(phpunit: Path) -> dict:
    root = ET.parse(phpunit).getroot()
    return {e.get("name"): e for e in root.iter("env")}


class FixtureApps(unittest.TestCase):
    BUILDER_DIR = FIX / "builder"

    def test_the_isolated_app_pins_a_forced_test_database(self):
        app = self.BUILDER_DIR / "isolated-app"
        pins = env_pins(app / "phpunit.xml")
        self.assertIn("DB_DATABASE", pins)
        self.assertEqual(pins["DB_DATABASE"].get("force"), "true")
        self.assertTrue((app / "tests/Pest.php").is_file())
        self.assertFalse((app / ".ai/skills-profile.json").exists(), "no profile: AD8 uses locked when isolated")
        self.assertIn("laravel/framework", json.loads((app / "composer.json").read_text())["require"])

    def test_the_no_isolation_app_differs_only_in_its_phpunit_pin(self):
        app = self.BUILDER_DIR / "no-isolation-app"
        self.assertTrue((app / "phpunit.xml").is_file())
        pins = env_pins(app / "phpunit.xml")
        self.assertFalse("DB_DATABASE" in pins and pins["DB_DATABASE"].get("force") == "true")
        self.assertTrue((app / "tests/Pest.php").is_file(), "Pest is present, so the one cause is the missing pin")
        self.assertFalse((app / ".ai/skills-profile.json").exists())
        self.assertEqual((app / "composer.json").read_bytes(), (self.BUILDER_DIR / "isolated-app/composer.json").read_bytes())

    def test_the_stand_in_pest_is_the_same_in_every_builder_fixture(self):
        base = (self.BUILDER_DIR / "isolated-app/vendor/bin/pest").read_bytes()
        for name in ("no-isolation-app", "round-cap-app"):
            path = self.BUILDER_DIR / name / "vendor/bin/pest"
            self.assertEqual(path.read_bytes(), base, name)
            self.assertTrue(os.access(path, os.X_OK), f"{name}: vendor/bin/pest is not executable")

    def test_fixtures_link_the_package_skills(self):
        for rel in ("builder/isolated-app", "builder/no-isolation-app", "builder/round-cap-app",
                    "planner/avoid-ui-scaffold"):
            link = FIX / rel / ".claude/skills"
            with self.subTest(fixture=rel):
                self.assertTrue(link.is_symlink(), f"{rel}/.claude/skills must be a symlink")
                self.assertEqual(link.resolve(), (REPO / "resources/boost/skills").resolve())

    def test_the_greeting_spec_is_approved_with_two_acceptance_criteria(self):
        d = self.BUILDER_DIR / "greeting-spec/specs/2026-11-27-greeting"
        prd, plan = (d / "prd.md").read_text(), (d / "plan.md").read_text()
        self.assertEqual(frontmatter_of(d / "prd.md")["status"], "approved")
        self.assertEqual(frontmatter_of(d / "plan.md")["status"], "approved")
        self.assertEqual(len(re.findall(r"(?m)^- \*\*AC\d+ \(R1\)\*\*", prd)), 2, "AC21 needs exactly two criteria")
        self.assertRegex(plan, r"(?m)^### S1: ")
        self.assertRegex(plan, r"(?m)^- \*\*Requirements:\*\* R1$")
        self.assertRegex(plan, r"(?m)^- \*\*Verification gate:\*\* ")
        self.assertIn("test(gate): S1", plan)

    def test_the_round_cap_fixture_has_a_gate_test_only_ci_can_turn_green(self):
        app = self.BUILDER_DIR / "round-cap-app"
        d = app / "specs/2026-11-27-greeting-token"
        self.assertEqual(frontmatter_of(d / "prd.md")["status"], "approved")
        self.assertEqual(frontmatter_of(d / "plan.md")["status"], "approved")
        gate = (app / "tests/Feature/GreetingGateTest.php").read_text()
        self.assertIn("expect-env: GREETING_API_TOKEN", gate)
        self.assertIn("Hello, Ada!", gate)
        self.assertFalse((app / "app/Services/GreetingService.php").exists(), "the service is the builder's work")

    def test_the_stand_in_pest_goes_red_with_reasons_and_green_when_met(self):
        src = self.BUILDER_DIR / "round-cap-app"
        env = {k: v for k, v in os.environ.items() if k != "GREETING_API_TOKEN"}
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp) / "app"
            shutil.copytree(src, app, symlinks=True)
            run = lambda e: subprocess.run(["sh", "vendor/bin/pest"], cwd=app, capture_output=True, text=True, env=e)
            red = run(env)
            self.assertEqual(red.returncode, 1)
            self.assertIn("missing app/Services/GreetingService.php", red.stdout)
            self.assertIn("env GREETING_API_TOKEN is not set", red.stdout)
            service = app / "app/Services/GreetingService.php"
            service.write_text("<?php\n// Hello, Ada!\n")
            half = run(env)
            self.assertEqual(half.returncode, 1)
            self.assertIn("Tests: 1 failed, 1 passed", half.stdout)
            self.assertEqual(run({**env, "GREETING_API_TOKEN": "x"}).returncode, 0)

    def test_the_planner_fixture_asks_for_an_avoid_package(self):
        d = FIX / "planner/avoid-ui-scaffold"
        prd = d / "specs/2026-11-27-staff-login/prd.md"
        self.assertEqual(frontmatter_of(prd)["status"], "approved")
        self.assertIn("laravel/ui", prd.read_text())
        register = (REPO / "resources/boost/skills/laravel-package-verdicts/references/register.md").read_text()
        self.assertRegex(register, r"\| `laravel/ui` \| avoid \|", "the register must still mark laravel/ui avoid")
        self.assertNotIn("laravel/ui", (d / "composer.json").read_text())


if __name__ == "__main__":
    unittest.main()
