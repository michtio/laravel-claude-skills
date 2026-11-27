"""Gate test for slice S9b (laravel-layer): the README sections and the profile docs.

Requirements R8, R10, R23 (docs). Skills-gaps rows 1, 2, 3, 4, 11, 13, 16, 32, and the merge rule.
Contract: tests/S9b/CONTRACT.md section 7. Standard library only; no DDEV, no network.

Each check reads a section by its heading, so a sentence in the wrong place does not count: the
install order has to be in the install section, under the kind it belongs to.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
README = REPO / "README.md"
PROFILE_DOCS = REPO / "docs/profile.md"
I = re.I


def sections(markdown: str) -> list:
    """[(level, title, body)] where body runs to the next heading of the same or a higher level."""
    lines = markdown.splitlines()
    heads = [(i, len(m.group(1)), m.group(2).strip()) for i, line in enumerate(lines) if (m := re.match(r"^(#{1,6})\s+(.*)$", line))]
    out = []
    for n, (i, level, title) in enumerate(heads):
        end = len(lines)
        for j, lv, _ in heads[n + 1:]:
            if lv <= level:
                end = j
                break
        out.append((level, title, "\n".join(lines[i + 1:end])))
    return out


def find(markdown: str, level: int, pattern: str):
    for lv, title, body in sections(markdown):
        if lv == level and re.search(pattern, title, I):
            return title, body
    return None


def in_order(test: unittest.TestCase, body: str, needles: list, where: str) -> None:
    last = -1
    for needle in needles:
        pos = body.find(needle, last + 1)
        test.assertNotEqual(pos, -1, f"{where}: `{needle}` is missing, or comes before the step it follows")
        last = pos


class Readme(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = README.read_text(encoding="utf-8")

    def install_with_heading(self) -> str:
        """The level-2 Install section, with its level-3 kinds."""
        lines = self.text.splitlines()
        start = next((i for i, l in enumerate(lines) if re.match(r"^##\s+.*install", l, I)), None)
        self.assertIsNotNone(start, "README has no level-2 'Install' section")
        end = next((j for j in range(start + 1, len(lines)) if re.match(r"^##\s", lines[j])), len(lines))
        return "\n".join(lines[start:end])

    def kind(self, pattern: str) -> str:
        for lv, title, body in sections(self.install_with_heading()):
            if lv == 3 and re.search(pattern, title, I):
                return body
        self.fail(f"the Install section has no level-3 heading matching /{pattern}/")

    # Row 1, 3: the order per kind
    def test_app_section_runs_setup_then_boost_install_then_setup_again(self):
        body = self.kind(r"\bapp\b")
        in_order(self, body, ["claude-skills:setup", "boost:install", "claude-skills:setup --check"], "app section")

    def test_package_section_runs_the_same_order_through_testbench(self):
        body = self.kind(r"package")
        in_order(self, body, ["claude-skills:setup", "boost:install", "claude-skills:setup --check"], "package section")
        self.assertIn("vendor/bin/testbench", body, "a package has no artisan: the commands go through testbench")

    def test_the_order_says_why_boost_install_runs_between_two_setups(self):
        body = self.install_with_heading()
        self.assertRegex(body, r"(?is)boost:install[^.]{0,200}\.mcp\.json[^.]{0,200}(reset|overwrit|rewrit)",
                         "the second setup run exists because boost:install resets .mcp.json: say so")

    def test_claude_md_before_boost_is_explained(self):
        body = self.install_with_heading()
        self.assertRegex(body, r"(?is)CLAUDE\.md[^.]{0,240}AGENTS\.md|AGENTS\.md[^.]{0,240}CLAUDE\.md",
                         "say that Boost writes AGENTS.md when CLAUDE.md is missing, and that the setup creates CLAUDE.md first")

    # Row 4: non-interactive Boost
    def test_non_interactive_boost_recipe(self):
        body = self.install_with_heading()
        self.assertIn("boost.json", body)
        self.assertRegex(body, r'"agents"\s*:\s*\[\s*"claude_code"\s*\]')
        self.assertRegex(body, r'"packages"\s*:\s*\[\s*"michtio/laravel-claude-skills"\s*\]')
        self.assertRegex(body, r'"cloud"\s*:\s*false')
        self.assertRegex(body, r"boost:install[^\n]*(--no-interaction|\s-n\b)")

    # Row 2: the unreleased pack
    def test_requiring_the_unreleased_pack_from_vcs(self):
        body = self.install_with_heading()
        self.assertRegex(body, r'"type"\s*:\s*"vcs"')
        self.assertIn("https://github.com/michtio/laravel-claude-skills", body)
        self.assertRegex(body, r'"michtio/laravel-claude-skills"\s*:\s*"dev-main"')
        self.assertRegex(body, r"(?i)first (tag|release)", "say it is for the time before the first tag")
        self.assertRegex(body, r"(?is)lock[^.]{0,160}(pin|commit)")

    # Row 11: the workbench
    def test_package_section_creates_the_workbench_and_formats_it(self):
        body = self.kind(r"package")
        self.assertRegex(body, r"workbench:install\s+--basic\s+--devtool")
        self.assertRegex(body, r"(?:vendor/bin/)?pint\s+workbench")

    # Row 16: agents
    def test_plugin_install_commands(self):
        body = self.text
        self.assertIn("/plugin marketplace add michtio/laravel-claude-skills", body)
        self.assertIn("/plugin install laravel-claude-skills@laravel-claude-skills", body)
        in_order(self, body, ["/plugin marketplace add michtio/laravel-claude-skills", "/plugin install laravel-claude-skills@laravel-claude-skills"], "README")

    def test_the_agents_section_points_to_the_install_step_for_the_agents(self):
        found = find(self.text, 2, r"agents")
        self.assertIsNotNone(found)
        self.assertIn("/plugin install", found[1], "the Agents section says how a project gets the agents")

    # Row 32: boost:update
    def test_boost_update_after_a_ddev_php_change(self):
        paragraphs = [p for p in re.split(r"\n\s*\n", self.text) if "boost:update" in p]
        self.assertTrue(paragraphs, "README never says boost:update")
        self.assertTrue(any(re.search(r"DDEV", p) and re.search(r"PHP", p) for p in paragraphs),
                        "boost:update must be tied to a change of the DDEV PHP version in the same paragraph")

    # The merge rule
    def test_gated_prs_merge_with_a_merge_commit(self):
        paragraphs = [p for p in re.split(r"\n\s*\n", self.text) if re.search(r"merge commit", p, I)]
        self.assertTrue(paragraphs, "README never says a gated PR merges with a merge commit")
        self.assertTrue(any(re.search(r"squash", p, I) and re.search(r"gate commit", p, I) for p in paragraphs),
                        "say never squash, and why: a squash removes the gate commit the lock check needs")


class ProfileDocs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = PROFILE_DOCS.read_text(encoding="utf-8")

    def option_line(self, key: str) -> str:
        for line in self.text.splitlines():
            if f"`{key}`" in line:
                return line
        self.fail(f"docs/profile.md has no line for `{key}`")

    def test_the_new_keys_are_listed_with_their_defaults(self):
        for key, default in {"test_database": "auto", "php_matrix": "auto", "test_pins": "none"}.items():
            with self.subTest(key=key):
                self.assertIn(f"`{default}`", self.option_line(key))

    def test_test_database_values(self):
        line = self.option_line("test_database")
        for token in ("`ddev`", "`auto`"):
            self.assertIn(token, line)
        self.assertRegex(self.text, r"(?is)test_database[^\n]*ddev[^\n]*(package|Testbench)|package[^\n]*test_database")

    def test_test_pins_lists_the_four_names_and_says_isolation_is_the_default(self):
        block = "\n".join(l for l in self.text.splitlines() if "test_pins" in l or re.search(r"SESSION_DRIVER|CACHE_STORE", l))
        for name in ("SESSION_DRIVER", "CACHE_STORE", "QUEUE_CONNECTION", "MAIL_MAILER"):
            self.assertIn(f"`{name}`", self.text)
        self.assertRegex(self.text, r"(?is)test_pins.{0,800}(forced|isolation)")
        self.assertRegex(self.text, r"(?is)(DB_DATABASE|database pins)[^.]{0,200}(cannot|can't|not)[^.]{0,80}(named|overrid|listed)")

    def test_php_matrix_default_for_a_package(self):
        self.assertRegex(self.text, r"(?is)php_matrix.{0,900}require\.php[^.]{0,200}(floor|lowest)")

    def test_ddev_check_exit_line_is_explained(self):
        self.assertRegex(self.text, r"(?is)--check[^\n]*\n?.{0,600}Failed to execute command",
                         "name DDEV's red 'Failed to execute command' line that follows the expected exit 1 of --check")

    def test_planned_wording(self):
        self.assertIn("changes planned", self.text, "the docs quote the new summary line: `N changes planned.`")
