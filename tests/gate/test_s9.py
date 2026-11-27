"""Gate test for slice S9 (laravel-layer): reviewer, deep reviewer team, debugger.

Requirements R14, R15, R16, R17, R25. Acceptance criteria AC18, AC20, AC22 (and AC19, AC25 for the
new agents). Contract: tests/Agents/CONTRACT-S9.md. Standard library only. Run:

    python3 -m unittest discover -s tests/gate

What this file proves now (deterministic, no model calls): the three agent files exist, are listed
in plugin.json, pin model and effort, pass the startup budget and the tool rules (the deep reviewer
is an orchestrator with a cap line, the plain reviewer is not), state the content rules each agent
must follow (the G4 weakening list, the G5 gate reruns with their isolation precondition, static
checks as ranked evidence, the lens team and its one fresh challenger, the G7 hypotheses table, the
failing regression test first), match the Craft pack's gate-discipline wording (rows G4, G5, G7, and
the debugger's G6), and the three release cases in evals/behavior-sets/review-debug.json are well
formed, their assertions accept a good hand-back and reject each planted bad one, and their planted
fixtures behave as the cases describe.

What it cannot prove: what a model does when it runs the agents. That is the release runner's job
(slice S11) over the same cases.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # so `python3 -m unittest tests.gate.test_s9` works from the repo root

import test_s8 as s8  # noqa: E402

REPO = s8.REPO
AGENTS = s8.AGENTS
FIX = s8.FIX
SAMPLES = s8.SAMPLES
agent_budget = s8.agent_budget
CASES_FILE = REPO / "evals/behavior-sets/review-debug.json"
I_S = re.I | re.S

S9_AGENTS = {
    "laravel-reviewer": "sonnet",
    "laravel-reviewer-deep": "opus",
    "laravel-debugger": "sonnet",
}
S8_STEMS = list(s8.S8_AGENTS)
ALL_STEMS = S8_STEMS + list(S9_AGENTS)


def text(test: unittest.TestCase, stem: str) -> str:
    return s8.read_agent(test, stem)


def section(body: str, start: str, end: str) -> str:
    a = body.find(start)
    b = body.find(end, a + 1) if a >= 0 else -1
    return body[a:b] if a >= 0 and b > a else ""


def run_budget(root: Path | None = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(REPO / "scripts/agent_budget.py")]
    if root is not None:
        cmd += ["--root", str(root)]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)


# ----------------------------------------------------------------------------
# files, frontmatter, budgets
# ----------------------------------------------------------------------------

class AgentFiles(unittest.TestCase):
    def test_the_three_agents_exist(self):
        missing = [s for s in S9_AGENTS if not s8.agent_path(s).is_file()]
        self.assertEqual(missing, [], f"agent files missing from agents/: {missing}")

    def test_plugin_json_lists_the_three_and_every_entry_exists(self):
        manifest = json.loads((REPO / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        listed = manifest["agents"]
        for stem in S9_AGENTS:
            self.assertIn(f"./agents/{stem}.md", listed, f"{stem} is not in plugin.json agents")
        self.assertEqual(sorted(listed), sorted(f"./agents/{p.name}" for p in AGENTS.glob("*.md")))
        for entry in listed:
            self.assertTrue((REPO / entry).is_file(), f"{entry} listed but missing")

    def test_names_no_outside_model_or_builder(self):
        for stem in S9_AGENTS:
            body = text(self, stem)
            for term in ("qwen", "mistral", "ollama", "gemini", "glm", "vibe"):
                self.assertIsNone(re.search(rf"(?i)(?<![a-z]){term}(?![a-z])", body), f"{stem} names {term}")


class Frontmatter(unittest.TestCase):
    def test_name_matches_the_file_and_description_is_set(self):
        for stem in S9_AGENTS:
            with self.subTest(agent=stem):
                data = s8.frontmatter(self, stem)
                self.assertEqual(agent_budget.as_scalar(data, "name"), stem)
                self.assertGreater(len(agent_budget.as_scalar(data, "description")), 40)

    def test_model_and_effort_are_pinned(self):
        for stem, model in S9_AGENTS.items():
            with self.subTest(agent=stem):
                data = s8.frontmatter(self, stem)
                self.assertEqual(agent_budget.as_scalar(data, "model"), model)
                self.assertEqual(agent_budget.as_scalar(data, "effort"), "high")

    def test_no_agent_has_a_tools_allowlist_that_names_a_boost_tool(self):
        # AD3: a tools: list naming a Boost tool stops the agent launching in a repo without Boost's MCP.
        for stem in S9_AGENTS:
            with self.subTest(agent=stem):
                data = s8.frontmatter(self, stem)
                self.assertEqual([t for t in agent_budget.as_list(data, "tools") if t.startswith("mcp__laravel-boost__")], [])

    def test_the_reviewers_deny_every_write_tool_and_keep_boost_reachable(self):
        for stem in ("laravel-reviewer", "laravel-reviewer-deep"):
            with self.subTest(agent=stem):
                data = s8.frontmatter(self, stem)
                disallowed = set(agent_budget.as_list(data, "disallowedTools"))
                for tool in ("Write", "Edit", "NotebookEdit", s8.TINKER, s8.RECORD_RULE):
                    self.assertIn(tool, disallowed, f"{stem} does not disallow {tool}")
                self.assertNotIn("tools", data, "a tools: allowlist would cut off Boost's tools (AD3)")

    def test_the_plain_reviewer_starts_no_agents_the_deep_reviewer_does(self):
        plain = set(agent_budget.as_list(s8.frontmatter(self, "laravel-reviewer"), "disallowedTools"))
        self.assertIn("Agent", plain)
        deep = set(agent_budget.as_list(s8.frontmatter(self, "laravel-reviewer-deep"), "disallowedTools"))
        self.assertFalse(deep & {"Agent", "Task"}, "the deep reviewer is the orchestrator: it needs the Agent tool")

    def test_the_deep_reviewer_preloads_nothing(self):
        # AD12: the lens checkers load what they need; the orchestrator's startup stays small.
        self.assertNotIn("skills", s8.frontmatter(self, "laravel-reviewer-deep"))

    def test_the_debugger_can_write_and_run_but_starts_no_agents_and_never_records_rules(self):
        data = s8.frontmatter(self, "laravel-debugger")
        disallowed = set(agent_budget.as_list(data, "disallowedTools"))
        for tool in ("Agent", s8.RECORD_RULE):
            self.assertIn(tool, disallowed, f"the debugger must disallow {tool}")
        for tool in ("Write", "Edit", "Bash"):
            self.assertNotIn(tool, disallowed, f"the debugger needs {tool}")
        if "tools" in data:
            listed = {agent_budget.tool_name(t) for t in agent_budget.as_list(data, "tools")}
            self.assertTrue({"Write", "Edit", "Bash"} <= listed)


class Budgets(unittest.TestCase):
    def test_agent_budget_passes_on_the_repo_with_the_expected_caps(self):
        for stem in S9_AGENTS:
            text(self, stem)
        proc = run_budget()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        for stem, cap in {"laravel-reviewer": 0, "laravel-reviewer-deep": 5, "laravel-debugger": 0}.items():
            self.assertRegex(proc.stdout, rf"(?m)^ok\s+{stem}\s+cap {cap}\s", f"{stem} is not cap {cap}:\n{proc.stdout}")

    def test_the_deep_reviewer_carries_its_cap_line(self):
        self.assertRegex(text(self, "laravel-reviewer-deep"), r"At most 5 agents per review")

    def test_the_deep_reviewer_cannot_be_over_cap(self):
        for m in re.findall(r"At most (\d+) agents per (?:run|review)", text(self, "laravel-reviewer-deep")):
            self.assertLessEqual(int(m), 5)

    def test_every_agent_stays_under_48_kb(self):
        for stem in S9_AGENTS:
            text(self, stem)
            self.assertLessEqual(s8.agent_path(stem).stat().st_size, 48 * 1024, stem)

    def test_budget_fixtures_the_deep_reviewer_exemption_is_narrow(self):
        # AD12, decided 2026-11-27 after S1: the deep reviewer is exempt from "a reviewer disallows Agent"
        # when it carries a cap line. A cap line does not exempt a plain reviewer, and a missing or
        # oversized cap still fails.
        cases = {
            "agent-reviewer-deep-orchestrator": (0, r"(?m)^ok\s+laravel-reviewer-deep\s+cap 5\s"),
            "agent-reviewer-deep-no-cap": (1, r"Agent tool without an 'At most N agents per run\|review' line|must disallow Agent"),
            "agent-reviewer-deep-cap-6": (1, "cap above 5"),
            "agent-reviewer-with-cap-line": (1, "must disallow Agent"),
            "agent-debugger-with-agent": (1, r"Agent tool without an 'At most N agents per run\|review' line"),
            "agent-debugger-valid": (0, r"(?m)^ok\s+laravel-debugger\s+cap 0\s"),
        }
        for fixture, (code, expected) in cases.items():
            with self.subTest(fixture=fixture):
                proc = run_budget(FIX / fixture)
                self.assertEqual(proc.returncode, code, proc.stdout + proc.stderr)
                self.assertRegex(proc.stdout, re.escape(expected) if expected in ("cap above 5", "must disallow Agent") else expected)

    def test_check_sh_stays_green_with_the_new_agents(self):
        for stem in S9_AGENTS:
            text(self, stem)
        proc = subprocess.run(["sh", "scripts/check.sh"], capture_output=True, text=True, cwd=REPO)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("check.sh: all gates passed", proc.stdout)


# ----------------------------------------------------------------------------
# content rules
# ----------------------------------------------------------------------------

BASH_FORBIDDEN = ("migrate", "db:wipe", "composer require", "composer remove", "git commit", "git push", "git stash")
WEAKENING_LINE = r"Test\s+weakening.{0,600}skip.{0,600}expectation"
CLAIMS_LINE = r"A\s+builder.s\s+PASS\s+lines\s+are\s+claims"

# Shared by the reviewer and the deep reviewer's conventions brief: the G4 list and the G5 reruns.
WEAKENING_ITEMS = [
    ("skip marker", r"->skip\("),
    ("todo marker", r"->todo\("),
    ("only marker", r"->only\("),
    ("markTestSkipped", r"markTestSkipped"),
    ("a deleted test block", r"(?is)delet\w+[^.\n]{0,40}(test|it)\b[^.\n]{0,20}block|(test|it)\(\)? blocks? (is |are )?(deleted|removed)"),
    ("a commented-out test counts as deleted", r"(?i)comment(ed|s|ing)?[- ]+(one |it |a test )?out|commented-out"),
    ("fewer assertions", r"(?i)(lower\w*|fewer|drop\w*)[^.\n]{0,40}(assertion|expect\()"),
    ("a looser matcher with examples", r"(?is)(looser|loosen|widen)[^.\n]{0,200}toBe\b[^.\n]{0,200}(toBeTruthy|toBeString|toBeInt|not->toBeNull)"),
    ("a narrowed dataset", r"(?i)(narrow\w*|shrunk|smaller)[^.\n]{0,30}(dataset|data set)"),
    ("a changed, renamed or deleted gate-commit file", r"(?is)(chang|renam|delet)\w+[^.\n]{0,120}gate[- ]commit"),
    ("test configuration", r"(?is)tests/Pest\.php.{0,200}(TestCase).{0,200}phpunit\.xml|phpunit\.xml.{0,300}(pin|force)"),
]


def reviewer_rules() -> list:
    """The shared review rules; both reviewers carry them, the deep reviewer in its conventions brief."""
    rules = [
        ("G4 pack_check wording on one line", WEAKENING_LINE, 0),
        ("weakening is Important or higher", r"(?is)weakening.{0,900}Important[^.\n]{0,40}(or higher|at least|minimum)|"
                                             r"Important[^.\n]{0,40}(or higher)[^.\n]{0,300}weakening", 0),
        ("a lost isolation pin on a database-wiping suite is Critical",
         r"(?is)(pin|force=\"true\"|isolation)[^.]{0,300}Critical|Critical[^.]{0,300}(pin|force=\"true\"|isolation)", 0),
        ("the gate commit comes from git history", r"git log --grep ['\"]\^test\(gate\):", 0),
        ("gate files come from the commit, never a hand-back list", r"git show --name-only --format= <gate commit>", 0),
        ("gate files never come from a hand-back", r"(?i)never from (a|the|any) hand-?back", 0),
        ("lock check, working-tree form", r"git diff --quiet <gate commit> -- <gate files>", 0),
        ("lock check, commit form", r"git diff --quiet <gate commit> HEAD -- <gate files>", 0),
        ("the lock check results are reported", r"(?is)(lock check|git diff --quiet).{0,400}(exit|result|report)", 0),
        ("G5 pack_check wording", CLAIMS_LINE, 0),
        ("report form: rerun", r"Gate <command>: rerun, pass\|fail", 0),
        ("report form: claimed, not rerun", r"Gate <command>: claimed, not rerun \(<reason>\)", 0),
        ("isolation: a forced DB_DATABASE pin", r"DB_DATABASE[^.\n]{0,120}force=\"true\"|force=\"true\"[^.\n]{0,120}DB_DATABASE", 0),
        ("isolation: the pinned name differs from the dev database", r"(?is)(differ\w*|not the same|other than)[^.]{0,200}(dev|development|\.env)[^.]{0,80}(database|name)|(dev|\.env)[^.]{0,200}(database|name)[^.]{0,120}(differ|not the same)", 0),
        ("isolation: in-memory sqlite and Testbench count", r"(?is):memory:.{0,300}testbench|testbench.{0,300}:memory:", 0),
        ("isolation is judged on the code under review", r"(?i)(judged|decided|checked|read|taken)[^.\n]{0,80}(code|tree|tip) under review|(code|tree|tip) under review[^.\n]{0,200}(isolat|pin)", 0),
        ("a suite that is not isolated is never run", r"(?is)never run[^.]{0,120}(suite|test)[^.]{0,120}(without|not)[^.]{0,40}isolat", 0),
        ("reruns only the commands the hand-back or plan names", r"(?is)(hand-?back or (the )?plan|plan or (the )?hand-?back)[^.]{0,200}names?|names?[^.]{0,200}(hand-?back|plan)", 0),
        ("reruns with the command's filter, through the runner", r"(?is)--filter[^.]{0,300}(ddev|runner)|(ddev|runner)[^.]{0,300}--filter", 0),
        ("a green rerun does not clear a weakening finding", r"(?is)(rerun|green)[^.]{0,200}(does not|doesn.t|never)[^.]{0,120}(clear|cancel|excuse|prove)[^.]{0,160}(weaken|skip)|weaken\w*[^.]{0,200}(stays|remains)[^.]{0,80}(green|pass)", 0),
        ("G8 wording: a test that passes with the fix reverted", r"would\s+still\s+pass\s+with\s+the\s+fix\s+reverted", 0),
        ("untracked files are part of uncommitted work", r"(?is)untracked[^.]{0,300}(git status|read|review|include)|git status[^.]{0,200}untracked", 0),
        ("uncommitted work is diffed with git diff <base>, never three-dot", r"(?is)git diff <base>.{0,500}three-dot|three-dot.{0,300}git diff <base>", 0),
        ("findings carry evidence", r"Evidence:", 0),
        ("a Critical or Important needs evidence it read", r"(?is)(Critical or Important|Important or Critical)[^.]{0,200}evidence", 0),
        ("framework claims trace through source or docs, else Verify:", r"(?is)Verify:.{0,300}|vendor/laravel/framework/src", 0),
        ("a static-check line is evidence", r"(?is)(larastan|pint|static[- ]check)[^.]{0,200}(evidence|line)", 0),
        ("consults the package register", r"laravel-package-verdicts", 0),
        ("cites an avoid verdict in the register's form", r"<package>: <use> \(<reason>\)", 0),
        ("a missing register means no verdict, reported",
         r"(?is)(missing|not installed|cannot load|not available)[^.]{0,200}register.{0,400}no verdict|register[^.]{0,200}(missing|not installed|cannot load|not available).{0,400}no verdict", 0),
        ("sensitive paths", r"\$request->input", 0),
        ("sensitive paths: raw SQL", r"whereRaw", 0),
        ("sensitive paths: unescaped Blade", r"\{!! !!\}", 0),
        ("sensitive paths: mass assignment", r"\$guarded", 0),
        ("sensitive paths: middleware and signed URLs", r"withoutMiddleware", 0),
        ("per-R-id table when the brief names a spec", r"R id \| met / partly / not met", 0),
        ("loads the pitfalls skill", r"laravel-pitfalls", 0),
        ("uses Boost's read-only tools", r"search-docs", 0),
    ]
    rules += [(f"weakening list: {label}", pattern, 0) for label, pattern in WEAKENING_ITEMS]
    return rules


CONTENT9 = {
    "laravel-reviewer": reviewer_rules() + [
        ("read-only: changes nothing", r"(?i)read-only", 0),
        ("starts no agents", r"(?i)(start|starts|starting) no agents|never start (an )?agents?|no agents", 0),
        ("Bash is limited by instruction only", r"(?is)Bash[^.]{0,300}(by instruction|instruction only|only by instruction)|(by instruction|instruction only)[^.]{0,200}Bash", 0),
        ("Bash is for git reads and the gate reruns", r"(?is)git diff.{0,200}git log.{0,200}git show.{0,400}(rerun|pest)", 0),
        ("never the full suite unless a hand-back names it, never a pass without isolation", r"(?is)(full|whole) suite", 0),
        ("one line per gate in the report", r"(?is)one line per gate|a line per gate|each gate", 0),
    ],
    "laravel-reviewer-deep": reviewer_rules() + [
        ("never modifies files", r"(?i)never modify|you change nothing|read-only", 0),
        ("depth comes from separate checkers, evidence and one challenge", r"(?is)(separate|small team|team of)[^.]{0,200}checkers?", 0),
        ("starts no more agents than the diff needs", r"(?is)no more agents than", 0),
        ("the checker is the package's own", r"laravel-review-checker", 0),
        ("conventions and security always", r"(?is)always[^.\n]{0,40}\*{0,2}conventions\*{0,2}[^.\n]{0,80}\*{0,2}security|always.{0,120}conventions.{0,120}security", 0),
        ("at most two other lenses", r"(?is)at most two (of )?(the )?others?|at most two more", 0),
        ("the optional lenses", r"(?i)performance", 0),
        ("the optional lenses: data and migrations", r"(?i)migrations?", 0),
        ("security lens runs on Opus", r"(?is)security[^.\n]{0,160}model: opus|model: opus[^.\n]{0,160}security", 0),
        ("other lenses pass no model", r"(?is)(other|remaining|every other)[^.\n]{0,80}(lens|checker)[^.\n]{0,160}(no `?model`?|without a `?model`?|no model)|pass no `model`", 0),
        ("checkers start in parallel in one message", r"(?is)parallel[^.]{0,80}one message", 0),
        ("a checker brief holds the lens, versions, files with the diff command and static-check lines",
         r"(?is)each (checker )?(prompt|brief) holds[^.]{0,500}(version)[^.]{0,500}(diff command)[^.]{0,300}static", 0),
        ("single pass rule: under 200 lines and one area, or no Agent tool", r"(?is)single pass[^.]{0,300}200[^.]{0,300}(one area|single area)[^.]{0,300}(Agent)", 0),
        ("single pass still confirms Critical and Important findings against source or the check output", r"(?is)single pass.{0,900}(confirm|verify)[^.]{0,200}(Critical|Important)", 0),
        ("static checks: Larastan", r"vendor/bin/phpstan analyse", 0),
        ("static checks: Pint in test mode only", r"vendor/bin/pint --test", 0),
        ("static checks: the architecture tests", r"(?i)architecture tests?|arch tests?|\barch\b", 0),
        ("static checks: only what the project configures", r"(?is)only what the project configures", 0),
        ("static checks: never fixes", r"(?is)never[^.\n]{0,40}(--fix|without --test|a fix run)", 0),
        ("static checks: keeps only the lines for changed files", r"(?is)keep only (the )?lines for (the )?changed files", 0),
        ("static checks: a Pest run of any kind waits for isolation", r"(?is)(pest|architecture tests?|arch tests?)[^.]{0,300}isolat", 0),
        ("R16: a check-backed finding ranks above one that is not", r"(?is)(backed by|backed)[^.\n]{0,200}(ranks?|above|before)[^.\n]{0,200}(not|unbacked)|rank\w*[^.\n]{0,80}above[^.\n]{0,160}(not|unbacked)", 0),
        ("R16: the header carries the check tag", r"\[larastan\]", 0),
        ("R16: the other check tags", r"\[pint\]", 0),
        ("R16: the arch check tag", r"\[arch\]", 0),
        ("R16: an unbacked opinion is a Suggestion and never displaces a check-backed finding", r"(?is)(unbacked|no check|not backed|opinion)[^.\n]{0,300}Suggestion|Suggestion[^.\n]{0,300}(unbacked|opinion)", 0),
        ("R16: an error in an unchanged file is not the diff's finding", r"(?is)(unchanged|not in the diff|pre-?existing|already there)[^.\n]{0,200}(file|line|error)", 0),
        ("R14: reads composer.json require and require-dev against the register", r"(?is)composer\.json[^.]{0,300}require-dev|require-dev[^.]{0,300}composer\.json", 0),
        ("R14 / AC18: flags an avoid package with the verdict's reason, even when not in the diff", r"(?is)avoid[^.]{0,400}(reason)[^.]{0,400}(not in the diff|already|whether)|(whether|even when)[^.]{0,200}(diff|already)[^.]{0,400}avoid", 0),
        ("AC18: Important when the diff adds it", r"(?is)(diff adds|adds? it|added)[^.]{0,200}Important|Important[^.]{0,200}(diff adds|adds? it|added)", 0),
        ("challenge: one round, one fresh checker call", r"(?is)(one|a single) fresh `?laravel-review-checker`?", 0),
        ("challenge: every Critical and Important in one prompt", r"(?is)every Critical and Important[^.]{0,200}one prompt", 0),
        ("challenge: Challenge mode", r"Challenge mode", 0),
        ("challenge: refute only with a citation", r"(?is)refute[^.]{0,120}(file:line|citation)", 0),
        ("challenge: never resume an earlier checker", r"(?is)(do not|never) resume", 0),
        ("challenge: unsure is kept and tagged disputed", r"(?is)unsure[^.]{0,200}disputed", 0),
        ("challenge: refuted findings are listed as dropped", r"Dropped after challenge", 0),
        ("challenge: suggestions are not challenged", r"(?is)suggestions are not challenged", 0),
        ("report: the mode line with the agent count and the static checks", r"Mode: team \([^)\n]*\)[^\n]{0,40}agents: \d[^\n]{0,40}static checks:", 0),
        ("report: the single pass mode line", r"Mode: single pass \(<reason>\)", 0),
        ("report: one line per gate, rerun or claimed", r"(?is)one line per gate|gate[^.\n]{0,60}(rerun|claimed)", 0),
        ("report: severity sections", r"(?m)^#+ Critical", 0),
        ("Bash is limited by instruction only", r"(?is)Bash[^.]{0,300}(by instruction|instruction only|only by instruction)|(by instruction|instruction only)[^.]{0,200}Bash", 0),
    ],
    "laravel-debugger": [
        ("G7 pack_check wording", r"Form\s+2-3\s+possible\s+explanations\s+before\s+reading\s+code", 0),
        ("G6 3-round cap", r"Stop\s+after\s+3\s+rounds", 0),
        ("reproduces first, with the red output pasted", r"(?is)reproduc\w+[^.]{0,300}(paste|red output|run the failing)", 0),
        ("cannot reproduce: say so and stop", r"(?is)(cannot|can.t|unable to) reproduce[^.]{0,300}(say so|stop|report)", 0),
        ("every hypothesis has the one check that tells it apart", r"(?is)each with the one check|one check that tells (it|them) apart", 0),
        ("every check runs before any fix", r"(?is)run every[^.]{0,80}check[^.]{0,80}before any fix", 0),
        ("fixes only the hypothesis the evidence supports", r"(?is)fix only the hypothesis the evidence supports", 0),
        ("none survives: form new ones", r"(?is)if none survives?[^.]{0,120}(new|form)", 0),
        ("never fix on a guess", r"(?i)never fix on a guess", 0),
        ("a recent change in a related area is the prime suspect", r"(?is)prime suspect", 0),
        ("hand-back Hypotheses table with its columns", r"\| hypothesis \| check \| result \| kept/rejected \|", 0),
        ("one row per hypothesis, the evidence in the result cell", r"(?is)one row per hypothesis[^.\n]{0,200}(evidence|result)", 0),
        ("rejected hypotheses are listed with the evidence against them", r"(?is)rejected[^.\n]{0,160}evidence", 0),
        ("hand-back Root cause line with file:line", r"Root cause( <n>)?:", 0),
        ("more than one cause is reported as Root cause <n>", r"Root cause <n>", 0),
        ("hand-back Regression test line", r"Regression test: <[^>]+> red before the fix", 0),
        ("regression test is written before the fix", r"(?is)(write|writes?)[^.]{0,120}(failing )?(regression )?test[^.]{0,200}before (you |the )?(fix|change|touch)", 0),
        ("the regression test must be red for the right reason", r"(?is)red for (a|the) (right )?reason", 0),
        ("an empty filter is not red", r"(?is)No tests found[^.]{0,250}not[^.]{0,80}(red|right reason)", 0),
        ("the regression test goes green after the fix", r"(?is)red before[^.]{0,120}green after|green after", 0),
        ("a fix that does not turn the test green counts as a round", r"(?is)(does not|doesn.t|not) turn[^.]{0,80}green[^.]{0,80}(counts as|is) (one|a) round", 0),
        ("a second cause: continue with the remaining hypotheses", r"(?is)(remaining|still open|other) hypothes[^.]{0,200}|second cause|more than one cause", 0),
        ("open findings are handed back with attempts and results", r"(?is)(attempts?)[^.]{0,120}(results?)[^.]{0,200}hypotheses? still open|open findings[^.]{0,200}attempts", 0),
        ("smallest root-cause fix", r"(?is)smallest (change|fix)", 0),
        ("unrelated cleanup is a separate change", r"(?is)unrelated[^.]{0,120}(separate|leave)", 0),
        ("never fix a symptom", r"(?is)never fix a symptom|root cause", 0),
        ("every conclusion carries evidence", r"(?is)evidence[^.]{0,200}(file:line|log line|query|test output)", 0),
        ("never weakens a test to get green", r"(?is)never[^.\n]{0,160}skip[^.\n]{0,160}(todo|only)[^.\n]{0,200}(delet|loosen)", 0),
        ("never edits a gate test or test config", r"(?is)never[^.\n]{0,200}(gate test|gate-commit)[^.\n]{0,200}(config|Pest\.php|phpunit)|(gate test|gate-commit)[^.\n]{0,200}never[^.\n]{0,200}(edit|chang)", 0),
        ("a test believed wrong is reported, not edited", r"(?is)(believe|think)[^.]{0,120}(test )?(is )?wrong[^.]{0,200}(report|never)", 0),
        ("runs the suite only when it is isolated", r"(?is)(only when|only if|unless)[^.\n]{0,80}isolated|isolated[^.\n]{0,80}(before|first)[^.\n]{0,120}run", 0),
        ("isolation: a forced DB_DATABASE pin", r"DB_DATABASE[^.\n]{0,120}force=\"true\"|force=\"true\"[^.\n]{0,120}DB_DATABASE", 0),
        ("isolation: sqlite in memory counts", r":memory:", 0),
        ("DDEV only, never php, composer or npm on the host", r"(?is)never[^.]{0,200}(php|composer|npm)[^.]{0,200}host|host[^.]{0,200}never", 0),
        ("an explicit profile runner wins over detection", r"(?is)(explicit|profile)[^.]{0,80}runner[^.]{0,200}(wins|takes precedence|overrides)[^.]{0,200}(detect|\.ddev)", 0),
        ("Boost: last-error and read-log-entries", r"last-error", 0),
        ("Boost: read-log-entries", r"read-log-entries", 0),
        ("Boost: database-schema", r"database-schema", 0),
        ("Boost: search-docs", r"search-docs", 0),
        ("loads the pitfalls skill", r"laravel-pitfalls", 0),
        ("asks before anything destructive to a database other than the test database", r"(?is)ask before[^.]{0,200}(destructive|migrate:fresh|db:wipe)", 0),
        ("leaves git to the caller", r"(?is)leave[^.]{0,40}(git|commit)[^.]{0,200}caller|caller[^.]{0,100}git", 0),
        ("version first", r"composer\.lock", 0),
    ],
}

FORBIDDEN9 = {
    stem: [
        ("the old lock form without a gate commit", r"git diff --quiet -- <gate files>", 0),
        ("a cap of 4 or more rounds", r"(?i)(?:stop|cap)\w*\s+(?:after|at)\s+(?:[4-9]|\d{2,}|four|five|six|seven|eight|nine|ten)\s+(?:fix\s+)?rounds", 0),
    ]
    for stem in S9_AGENTS
}


class ContentRules(unittest.TestCase):
    def test_each_agent_states_its_required_rules(self):
        for stem, rules in CONTENT9.items():
            body = text(self, stem)
            for label, pattern, flags in rules:
                with self.subTest(agent=stem, rule=label):
                    self.assertRegex(body, re.compile(pattern, flags | re.M), f"{stem} does not state: {label}")

    def test_forbidden_text_is_absent(self):
        for stem, rules in FORBIDDEN9.items():
            body = text(self, stem)
            for label, pattern, flags in rules:
                with self.subTest(agent=stem, rule=label):
                    self.assertNotRegex(body, re.compile(pattern, flags), f"{stem} states: {label}")

    def test_the_reviewers_never_use_the_three_dot_form_for_uncommitted_work(self):
        # The sentence that forbids it is allowed; an instruction to run it is not.
        for stem in ("laravel-reviewer", "laravel-reviewer-deep"):
            body = text(self, stem)
            with self.subTest(agent=stem):
                self.assertNotRegex(body, r"(?m)^\s*[-*\d.]*\s*`?git diff <base>\.\.\.HEAD`?\s*$",
                                    "a bare three-dot instruction drops uncommitted changes")

    def test_the_deep_reviewer_gives_only_the_security_lens_an_opus_override(self):
        body = text(self, "laravel-reviewer-deep")
        self.assertGreaterEqual(len(re.findall(r"model: opus", body)), 1)
        for other in ("conventions", "performance", "migrations", "data"):
            self.assertIsNone(re.search(rf"(?i)\*{{0,2}}{other}\*{{0,2}}[^.\n]{{0,60}}\(pass `?model: opus", body),
                              f"the {other} lens must not pass model: opus")


class ReviewerBash(unittest.TestCase):
    """Bash is limited by instruction only: every forbidden class is named (as for the planner and the checker)."""

    def test_forbidden_classes_are_listed(self):
        for stem in ("laravel-reviewer", "laravel-reviewer-deep"):
            body = text(self, stem)
            with self.subTest(agent=stem):
                for needle in BASH_FORBIDDEN:
                    self.assertIn(needle, body, f"{stem} does not list {needle} as forbidden Bash")
                self.assertRegex(body, r"(?i)file writes|writes? (to )?files|redirect")

    def test_a_rerun_is_the_only_test_run_a_reviewer_does(self):
        for stem in ("laravel-reviewer", "laravel-reviewer-deep"):
            body = text(self, stem)
            with self.subTest(agent=stem):
                self.assertRegex(body, r"(?is)(only|except)[^.]{0,200}(gate )?rerun[^.]{0,200}(isolated|isolation)|rerun[^.]{0,200}only[^.]{0,120}isolat")


# ----------------------------------------------------------------------------
# pack comparison (rows G4, G5, G7 and the debugger's G6)
# ----------------------------------------------------------------------------

PACK_ROWS9 = [
    ("G4", "laravel-reviewer", WEAKENING_LINE, False),
    ("G4", "laravel-reviewer-deep", WEAKENING_LINE, False),
    ("G5", "laravel-reviewer", CLAIMS_LINE, False),
    ("G5", "laravel-reviewer-deep", CLAIMS_LINE, False),
    ("G6", "laravel-debugger", r"Stop\s+after\s+3\s+rounds", False),
    ("G7", "laravel-debugger", r"Form\s+2-3\s+possible\s+explanations\s+before\s+reading\s+code", False),
    ("G8", "laravel-reviewer", r"would\s+still\s+pass\s+with\s+the\s+fix\s+reverted", False),
    ("G8", "laravel-reviewer-deep", r"would\s+still\s+pass\s+with\s+the\s+fix\s+reverted", False),
]
# G4, G5 and G7 are the rows this slice owns; G9 and G10 are pending in the reference itself.
OWNED_ROWS = ("G4", "G5", "G7")


class PackCheck(unittest.TestCase):
    """A pack_check-style comparison. No flags, like pack_check: `.` does not cross a newline, so the
    G4 wording sits on one line of the agent, as it does in the Craft reviewers."""

    def test_rows_match_the_agents(self):
        for rule, stem, pattern, _ in PACK_ROWS9:
            with self.subTest(rule=rule, agent=stem):
                self.assertTrue(re.search(pattern, text(self, stem)), f"{rule}: rule not found in {stem}")

    def test_no_agent_contradicts_the_round_cap(self):
        row = next(r for r in s8.PACK_CHECK_ROWS if r[0] == "G6" and r[3])
        for stem in ALL_STEMS:
            with self.subTest(agent=stem):
                self.assertIsNone(re.search(row[2], text(self, stem)), "a fix loop above 3 rounds")

    def test_the_embedded_rows_have_not_drifted_from_the_reference(self):
        if not s8.REFERENCE_RULES.is_file():
            self.skipTest("GATE_DISCIPLINE_RULES is not set")
        reference = s8.REFERENCE_RULES.read_text(encoding="utf-8")
        seen = set()
        for rule, stem, pattern, forbid in PACK_ROWS9:
            if rule == "G8":
                continue  # embedded by test_s8
            seen.add(rule)
            self.assertIn(("!" if forbid else "") + pattern, reference, f"{rule} row differs from {s8.REFERENCE_RULES}")
        self.assertTrue(set(OWNED_ROWS) <= seen, "rows G4, G5 and G7 must be compared")


# ----------------------------------------------------------------------------
# release cases (evals/behavior-sets/review-debug.json); run by S11's runner
# ----------------------------------------------------------------------------

CASE_KEYS = dict(s8.CASE_KEYS, setup=str)
REQUIRED_KEYS = {"id", "acs", "note", "cwd", "tools", "max_turns", "prompt", "must_match", "facts", "runs"}
REQUIRED_CASES = {
    "review-weakened-tests": {"AC22"},
    "deep-static-evidence": {"AC18", "AC20"},
    "debugger-hypotheses": {"R17"},
}
PLANTED = {  # fail sample -> a substring that must appear in the failure it triggers
    "review-weakened-tests": {
        "fail-no-gate-line.md": "claimed, not rerun",
        "fail-rerun-without-isolation.md": "rerun,",
        "fail-no-isolation-reason.md": "isolat",
        "fail-no-lock-check.md": "git diff --quiet",
        "fail-missed-pin.md": "phpunit",
        "fail-missed-skip.md": "shouts when asked",
        "fail-missed-widened.md": "toBeString",
        "fail-missed-fewer-assertions.md": "greets a name",
        "fail-missed-todo.md": "rejects a name longer",
        "fail-missed-deleted-block.md": "trims surrounding spaces",
        "fail-missed-only.md": "GreetingExtraTest",
        "fail-weakening-as-suggestion.md": "Suggestion",
        "fail-no-findings.md": "No findings",
    },
    "deep-static-evidence": {
        "fail-single-pass.md": "Mode",
        "fail-opinion-ranked-first.md": "OrderFormatter",
        "fail-opinion-promoted.md": "OrderFormatter",
        "fail-larastan-untagged.md": "larastan",
        "fail-larastan-as-suggestion.md": "larastan",
        "fail-no-avoid-flag.md": "laravel/ui",
        "fail-avoid-without-reason.md": "legacy",
        "fail-avoid-as-suggestion.md": "composer",
        "fail-baseline-noise-reported.md": "Legacy/Report",
        "fail-no-challenge.md": "challenge",
        "fail-no-static-line.md": "static checks",
    },
    "debugger-hypotheses": {
        "fail-prose-no-table.md": "hypothesis",
        "fail-one-cause.md": "Root cause 2",
        "fail-regression-green-before.md": "Regression test",
        "fail-fourth-round.md": "round",
        "fail-no-rejected-rows.md": "rejected",
        "fail-rejected-without-evidence.md": "rejected",
        "fail-root-cause-without-location.md": "Root cause 1",
        "fail-no-verification.md": "Tests:",
    },
}


def load_cases() -> list:
    if not CASES_FILE.is_file():
        raise AssertionError("evals/behavior-sets/review-debug.json is missing")
    return json.loads(CASES_FILE.read_text(encoding="utf-8"))


class ReleaseCaseSchema(unittest.TestCase):
    """Validated now for schema only; the runner that executes them is slice S11."""

    def test_the_required_cases_exist_with_their_acs(self):
        cases = {c["id"]: c for c in load_cases()}
        for cid, acs in REQUIRED_CASES.items():
            self.assertIn(cid, cases, f"release case {cid} is missing")
            self.assertTrue(acs <= set(cases[cid]["acs"]), f"{cid} must cover {sorted(acs)}")
        self.assertEqual(set(cases), set(REQUIRED_CASES), "unexpected extra cases")

    def test_ids_are_unique(self):
        ids = [c["id"] for c in load_cases()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_case_is_well_formed(self):
        for case in load_cases():
            with self.subTest(case=case.get("id", "?")):
                self.assertTrue(REQUIRED_KEYS <= set(case), f"missing keys {sorted(REQUIRED_KEYS - set(case))}")
                for key, value in case.items():
                    self.assertIn(key, CASE_KEYS, f"unknown key {key}")
                    expected = CASE_KEYS[key]
                    self.assertTrue(isinstance(value, expected) and not (expected is int and isinstance(value, bool)),
                                    f"{key} must be {expected.__name__}")
                self.assertTrue((REPO / case["cwd"]).is_dir(), f"cwd {case['cwd']} is not a directory")
                self.assertTrue(set(case["acs"]) and all(re.fullmatch(r"(AC|R)\d+", a) for a in case["acs"]))
                self.assertGreaterEqual(case["max_turns"], 1)
                if "setup" in case:
                    self.assertTrue(case.get("copy_cwd"), "setup runs in the copy")
                    self.assertTrue((REPO / case["cwd"] / case["setup"]).is_file(), "setup script is missing")
                    self.assertTrue(os.access(REPO / case["cwd"] / case["setup"], os.X_OK), "setup is not executable")

    def test_every_case_runs_three_times(self):
        # plan S9: `--runs 3`, 3 of 3 each.
        for case in load_cases():
            with self.subTest(case=case["id"]):
                self.assertEqual(case["runs"], 3)

    def test_prompts_name_a_package_agent_by_its_exact_type(self):
        for case in load_cases():
            with self.subTest(case=case["id"]):
                self.assertRegex(case["prompt"], r"laravel-claude-skills:laravel-[a-z-]+ agent \(that exact type\)")
                self.assertIn("Reply with the agent's", case["prompt"])

    def test_the_review_cases_are_read_only_and_the_debugger_case_may_write(self):
        cases = {c["id"]: c for c in load_cases()}
        for cid in ("review-weakened-tests", "deep-static-evidence"):
            with self.subTest(case=cid):
                tools = cases[cid]["tools"]
                for write in ("Write", "Edit", "NotebookEdit"):
                    self.assertNotIn(write, tools)
                self.assertNotRegex(tools, r"Bash\((?!git:|sh:|vendor/bin/(pest|phpstan|pint):)")
        self.assertIn("Write", cases["debugger-hypotheses"]["tools"])
        self.assertIn("Edit", cases["debugger-hypotheses"]["tools"])

    def test_the_review_cases_name_the_agent_under_test_and_the_deep_case_allows_its_team(self):
        cases = {c["id"]: c for c in load_cases()}
        self.assertEqual(cases["review-weakened-tests"]["expect_agent"], "laravel-reviewer")
        self.assertEqual(cases["review-weakened-tests"]["max_agents"], 1)
        self.assertEqual(cases["debugger-hypotheses"]["expect_agent"], "laravel-debugger")
        self.assertEqual(cases["debugger-hypotheses"]["max_agents"], 1)
        deep = cases["deep-static-evidence"]
        self.assertEqual(deep["expect_agents"], ["laravel-reviewer-deep", "laravel-review-checker"])
        # the agent under test counts itself: 1 + at most 5 started (the cap line)
        self.assertEqual(deep["max_agents"], 6)
        self.assertIn("Agent", deep["tools"])

    def test_expected_agents_are_package_agents(self):
        for case in load_cases():
            names = ([case["expect_agent"]] if "expect_agent" in case else []) + case.get("expect_agents", [])
            for name in names + case.get("forbid_agents", []):
                with self.subTest(case=case["id"], agent=name):
                    self.assertTrue(s8.agent_path(name).is_file(), f"{name} has no agent file")

    def test_assertions_compile(self):
        for case in load_cases():
            with self.subTest(case=case["id"]):
                for group in case["must_match"]:
                    self.assertTrue(isinstance(group, list) and group)
                    for pattern in group:
                        re.compile(pattern, I_S)
                for pattern in case.get("must_not_match", []):
                    re.compile(pattern, I_S)
                for fact in case["facts"]:
                    for pattern in fact.get("contains", []) + fact.get("not_contains", []):
                        re.compile(pattern, re.M)

    def test_facts_hold_against_the_agent_files(self):
        errors = []
        for case in load_cases():
            errors += s8.fact_failures(case)
        self.assertEqual(errors, [], "\n".join(errors))

    def test_the_cases_pin_the_hand_back_forms(self):
        pins = " ".join(p for c in load_cases() for f in c["facts"] for p in f.get("contains", []))
        for needle in (r"Gate <command>: claimed, not rerun", r"\[larastan\]", r"Dropped after challenge",
                       r"At most 5 agents per review", r"kept/rejected", r"Stop\s+after\s+3\s+rounds"):
            self.assertIn(needle, pins)

    def test_the_contract_documents_the_setup_key_and_the_other_choices(self):
        contract = REPO / "tests/Agents/CONTRACT-S9.md"
        self.assertTrue(contract.is_file(), "tests/Agents/CONTRACT-S9.md is missing")
        body = contract.read_text(encoding="utf-8")
        for needle in ("setup", "review-debug.json", "proven now", "S11", "Ambiguit"):
            self.assertIn(needle, body)


class ReleaseCaseAssertions(unittest.TestCase):
    """Each case's assertions accept its good hand-back and reject every planted bad one."""

    def test_samples_exist(self):
        for cid, bad in PLANTED.items():
            self.assertTrue((SAMPLES / cid / "pass.md").is_file(), f"{cid}/pass.md is missing")
            on_disk = {p.name for p in (SAMPLES / cid).glob("fail-*.md")}
            self.assertEqual(on_disk, set(bad), f"{cid}: every planted sample needs an expected reason")

    def test_the_good_hand_back_passes(self):
        cases = {c["id"]: c for c in load_cases()}
        for cid in REQUIRED_CASES:
            with self.subTest(case=cid):
                self.assertEqual(s8.score(cases[cid], (SAMPLES / cid / "pass.md").read_text(encoding="utf-8")), [])

    def test_every_planted_bad_hand_back_fails_for_its_own_reason(self):
        cases = {c["id"]: c for c in load_cases()}
        for cid, bad in PLANTED.items():
            for name, needle in bad.items():
                with self.subTest(case=cid, sample=name):
                    failures = s8.score(cases[cid], (SAMPLES / cid / name).read_text(encoding="utf-8"))
                    self.assertNotEqual(failures, [], f"{cid} accepts {name}")
                    self.assertTrue(any(needle in f for f in failures), f"{failures} lacks {needle!r}")

    def test_no_sample_names_a_real_client_or_person(self):
        for path in (SAMPLES).rglob("*.md"):
            if path.parent.name in REQUIRED_CASES:
                self.assertIsNone(re.search(r"/Users/|@[a-z0-9-]+\.(com|be|io)", path.read_text(encoding="utf-8")), path.name)


# ----------------------------------------------------------------------------
# planted fixtures
# ----------------------------------------------------------------------------

def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check, env=env)


def build_repo(src: Path, setup: str) -> Path:
    """What S11's runner does for a case with `setup`: copy the folder (symlinks kept), run the script there."""
    tmp = Path(tempfile.mkdtemp(prefix="lcs-s9-"))
    shutil.copytree(src, tmp / "repo", symlinks=True)
    proc = subprocess.run(["sh", setup], cwd=tmp / "repo", capture_output=True, text=True,
                          env={**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"})
    if proc.returncode != 0:
        raise AssertionError(f"setup failed: {proc.stdout}{proc.stderr}")
    return tmp / "repo"


class WeakenedTestsFixture(unittest.TestCase):
    SRC = FIX / "review/weakened-tests"
    GATE_FILES = ["tests/Feature/GreetingGateTest.php", "tests/Feature/GreetingLimitsGateTest.php"]

    @classmethod
    def setUpClass(cls):
        cls.repo = build_repo(cls.SRC, ".fixture/setup.sh")
        cls.addClassCleanup(shutil.rmtree, cls.repo.parent, True)

    def test_the_history_is_base_then_the_gate_commit_alone_in_tests(self):
        log = git(self.repo, "log", "--format=%s").stdout.split()
        self.assertEqual(git(self.repo, "log", "--format=%s").stdout.splitlines(), ["test(gate): S1", "base"])
        self.assertEqual(log[0:2], ["test(gate):", "S1"])
        files = git(self.repo, "show", "--name-only", "--format=", "HEAD").stdout.split()
        self.assertEqual(sorted(files), self.GATE_FILES)
        grep = git(self.repo, "log", "--grep", "^test(gate):", "--name-only", "--format=%h").stdout
        self.assertIn("tests/Feature/GreetingGateTest.php", grep)

    def test_the_setup_leaves_no_fixture_scaffolding_behind(self):
        self.assertFalse((self.repo / ".fixture").exists())
        self.assertEqual(git(self.repo, "ls-files", ".fixture").stdout, "")

    def test_the_lock_check_forms_disagree_because_the_work_is_uncommitted(self):
        files = self.GATE_FILES
        self.assertEqual(git(self.repo, "diff", "--quiet", "HEAD", "--", *files, check=False).returncode, 1)
        self.assertEqual(git(self.repo, "diff", "--quiet", "HEAD", "HEAD", "--", *files, check=False).returncode, 0)

    def test_the_work_is_uncommitted_and_includes_untracked_files(self):
        status = {line[3:]: line[:2] for line in git(self.repo, "status", "--porcelain").stdout.splitlines()}
        self.assertEqual(status.get("app/Services/GreetingService.php"), "??")
        self.assertEqual(status.get("tests/Feature/GreetingExtraTest.php"), "??")
        for tracked in ("phpunit.xml", *self.GATE_FILES):
            self.assertEqual(status.get(tracked), " M", tracked)

    def test_every_weakening_is_planted(self):
        gate = (self.repo / "tests/Feature/GreetingGateTest.php").read_text()
        limits = (self.repo / "tests/Feature/GreetingLimitsGateTest.php").read_text()
        extra = (self.repo / "tests/Feature/GreetingExtraTest.php").read_text()
        self.assertIn("->skip(", gate)
        self.assertIn("toBeString()", gate)
        self.assertEqual(gate.count("expect("), 3, "the dropped assertion: 4 in the gate commit, 3 now")
        self.assertIn("->todo()", limits)
        self.assertNotIn("trims surrounding spaces", limits)
        self.assertIn("->only()", extra)
        base = git(self.repo, "show", "HEAD:tests/Feature/GreetingGateTest.php").stdout
        self.assertEqual(base.count("expect("), 4)
        self.assertIn("trims surrounding spaces", git(self.repo, "show", "HEAD:tests/Feature/GreetingLimitsGateTest.php").stdout)

    def test_the_isolation_pin_is_in_the_gate_commit_and_gone_from_the_work(self):
        committed = s8.ET.fromstring(git(self.repo, "show", "HEAD:phpunit.xml").stdout)
        pins = {e.get("name"): e for e in committed.iter("env")}
        self.assertEqual(pins["DB_DATABASE"].get("force"), "true")
        self.assertEqual(pins["DB_DATABASE"].get("value"), "hello_test")
        now = s8.env_pins(self.repo / "phpunit.xml")
        self.assertIsNone(now["DB_DATABASE"].get("force"), "the work removes force=\"true\"")
        self.assertIn("RefreshDatabase", (self.repo / "tests/Pest.php").read_text(), "the suite wipes its database")
        self.assertIn("DB_DATABASE=hello\n", (self.repo / ".env.example").read_text(), "the dev database name differs from the test one")

    def test_the_skills_are_linked_for_the_register_and_pitfalls(self):
        link = self.repo / ".claude/skills"
        self.assertTrue(link.is_symlink())

    def test_the_source_folder_links_the_package_skills(self):
        link = self.SRC / ".claude/skills"
        self.assertTrue(link.is_symlink())
        self.assertEqual(link.resolve(), (REPO / "resources/boost/skills").resolve())

    def test_the_stand_in_pest_is_the_one_the_builder_fixtures_use(self):
        self.assertEqual((self.SRC / ".fixture/base/vendor/bin/pest").read_bytes(),
                         (FIX / "builder/isolated-app/vendor/bin/pest").read_bytes())


class StaticEvidenceFixture(unittest.TestCase):
    SRC = FIX / "review/static-evidence"

    @classmethod
    def setUpClass(cls):
        cls.repo = build_repo(cls.SRC, ".fixture/setup.sh")
        cls.addClassCleanup(shutil.rmtree, cls.repo.parent, True)

    def run_stand_in(self, name: str, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["sh", f"vendor/bin/{name}", *args], cwd=self.repo, capture_output=True, text=True)

    def test_the_change_spans_several_areas_and_is_small(self):
        # Team mode, not single pass: more than one area; the size alone must not be the reason.
        status = git(self.repo, "status", "--porcelain").stdout
        for area in ("app/Http/Controllers/OrderController.php", "database/migrations/", "tests/Feature/OrderShowTest.php", "composer.json"):
            self.assertIn(area, status)
        added = sum(int(a) for a, _, _ in (l.split("\t") for l in git(self.repo, "diff", "HEAD", "--numstat").stdout.splitlines()))
        self.assertLess(added, 200)

    def test_the_base_is_one_commit_and_the_work_uncommitted(self):
        self.assertEqual(git(self.repo, "log", "--format=%s").stdout.splitlines(), ["base"])
        self.assertFalse((self.repo / ".fixture").exists())

    def test_larastan_reports_the_real_error_on_the_changed_line_and_one_old_error(self):
        out = self.run_stand_in("phpstan", "analyse", "--no-progress", "--error-format=raw")
        self.assertEqual(out.returncode, 1)
        lines = out.stdout.splitlines()
        self.assertEqual(len(lines), 2, out.stdout)
        path, line, message = lines[0].split(":", 2)
        self.assertEqual(path, "app/Http/Controllers/OrderController.php")
        self.assertIn("customer->email", (self.repo / path).read_text().splitlines()[int(line) - 1])
        self.assertEqual(line, "29", "the release case pins OrderController.php:29")
        self.assertIn("Customer|null", message)
        self.assertTrue(lines[1].startswith("app/Legacy/Report.php:"))
        changed = git(self.repo, "status", "--porcelain").stdout
        self.assertNotIn("Legacy", changed, "the old error is in a file the diff does not touch")
        self.assertEqual(git(self.repo, "log", "--format=%s", "--", "app/Legacy/Report.php").stdout.strip(), "base")

    def test_the_nullable_relation_is_real(self):
        self.assertIn("Customer|null", (self.repo / "app/Models/Order.php").read_text())
        self.assertIn("nullable()", (self.repo / "database/migrations/2026_11_01_000000_create_orders_table.php").read_text())

    def test_pint_stand_in_runs_only_in_test_mode(self):
        self.assertEqual(self.run_stand_in("pint", "--test").returncode, 0)
        self.assertEqual(self.run_stand_in("pint").returncode, 2, "a fix run is refused, so a run can never rewrite files")

    def test_the_opinion_is_in_a_file_no_check_touches(self):
        formatter = (self.repo / "app/Support/OrderFormatter.php").read_text()
        self.assertIn("$res", formatter)
        self.assertNotIn("OrderFormatter", self.run_stand_in("phpstan").stdout)
        self.assertIn("app/Support/OrderFormatter.php", git(self.repo, "diff", "HEAD", "--name-only").stdout)

    def test_the_diff_adds_a_package_the_register_marks_avoid(self):
        composer = json.loads((self.repo / "composer.json").read_text())
        self.assertIn("laravel/ui", composer["require"])
        base = json.loads(git(self.repo, "show", "HEAD:composer.json").stdout)
        self.assertNotIn("laravel/ui", base["require"])
        register = (REPO / "resources/boost/skills/laravel-package-verdicts/references/register.md").read_text()
        row = re.search(r"\| `laravel/ui` \| avoid \| ([^|]+)\|", register)
        self.assertIsNotNone(row, "the register must still mark laravel/ui avoid")
        self.assertIn("Legacy Bootstrap authentication scaffolding", row.group(1))

    def test_the_project_configures_larastan_and_pint(self):
        self.assertIn("larastan", (self.repo / "phpstan.neon").read_text())
        composer = json.loads((self.repo / "composer.json").read_text())
        self.assertIn("laravel/pint", composer["require-dev"])

    def test_the_source_folder_links_the_package_skills(self):
        link = self.SRC / ".claude/skills"
        self.assertTrue(link.is_symlink())
        self.assertEqual(link.resolve(), (REPO / "resources/boost/skills").resolve())


class DebuggerFixture(unittest.TestCase):
    SRC = FIX / "debugger/two-cause-app"

    def pest(self, app: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["sh", "vendor/bin/pest", *args], cwd=app, capture_output=True, text=True)

    def copy(self) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="lcs-s9-dbg-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        shutil.copytree(self.SRC, tmp / "app", symlinks=True)
        return tmp / "app"

    def test_the_suite_is_isolated_and_the_skills_are_linked(self):
        pins = s8.env_pins(self.SRC / "phpunit.xml")
        self.assertEqual(pins["DB_DATABASE"].get("force"), "true")
        link = self.SRC / ".claude/skills"
        self.assertTrue(link.is_symlink())
        self.assertEqual(link.resolve(), (REPO / "resources/boost/skills").resolve())

    def test_red_with_both_symptoms_and_no_cause_named(self):
        app = self.copy()
        red = self.pest(app)
        self.assertEqual(red.returncode, 1)
        self.assertIn("discount for a subtotal of 5000 is 0, expected 750", red.stdout)
        self.assertIn("the invoice counts 2 lines, expected 1", red.stdout)
        self.assertIn("Tests: 1 failed, 1 passed", red.stdout)
        for cause in ("withTrashed", "intdiv", "(int)"):
            self.assertNotIn(cause, red.stdout, "the red output must not name the cause")

    def test_either_fix_alone_leaves_the_test_red_with_the_other_symptom(self):
        app = self.copy()
        calc = app / "app/Services/DiscountCalculator.php"
        calc.write_text(calc.read_text().replace("(int) ($coupon->percent / 100)", "$coupon->percent / 100"))
        half = self.pest(app)
        self.assertEqual(half.returncode, 1)
        self.assertIn("the invoice counts 2 lines", half.stdout)
        self.assertNotIn("discount for a subtotal", half.stdout)

        app2 = self.copy()
        inv = app2 / "app/Services/InvoiceCalculator.php"
        inv.write_text(inv.read_text().replace("->withTrashed()", ""))
        other = self.pest(app2)
        self.assertEqual(other.returncode, 1)
        self.assertIn("discount for a subtotal", other.stdout)
        self.assertNotIn("the invoice counts", other.stdout)

    def test_fixing_both_is_green_and_a_filter_matching_nothing_is_not_red(self):
        app = self.copy()
        calc = app / "app/Services/DiscountCalculator.php"
        calc.write_text(calc.read_text().replace("$subtotal * (int) ($coupon->percent / 100)", "intdiv($subtotal * $coupon->percent, 100)"))
        inv = app / "app/Services/InvoiceCalculator.php"
        inv.write_text(inv.read_text().replace("->withTrashed()", ""))
        green = self.pest(app)
        self.assertEqual(green.returncode, 0, green.stdout)
        self.assertIn("Tests: 2 passed", green.stdout)
        none = self.pest(app, "--filter=nothing matches this")
        self.assertEqual(none.returncode, 1)
        self.assertIn("No tests found", none.stdout)

    def test_a_decoy_hypothesis_exists_for_each_cause_the_agent_may_reject(self):
        # The causes are in two files and two models are involved (Order, OrderLine, Coupon), so more than
        # two hypotheses are plausible and at least one can be rejected on evidence.
        for rel in ("app/Models/Order.php", "app/Models/OrderLine.php", "app/Models/Coupon.php",
                    "app/Services/DiscountCalculator.php", "app/Services/InvoiceCalculator.php"):
            self.assertTrue((self.SRC / rel).is_file(), rel)
        self.assertIn("SoftDeletes", (self.SRC / "app/Models/OrderLine.php").read_text())
        self.assertIn("whole number of percent", (self.SRC / "app/Models/Coupon.php").read_text())

    def test_the_fixture_documents_the_markers_it_supports(self):
        doc = (self.SRC / "CLAUDE.md").read_text()
        for marker in ("expect-file", "expect-contains", "expect-absent", "No tests found"):
            self.assertIn(marker, doc)


if __name__ == "__main__":
    unittest.main()
