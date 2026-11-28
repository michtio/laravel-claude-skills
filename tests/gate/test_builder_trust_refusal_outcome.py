"""A command the trust list refuses gets its own visible outcome, and the last resolver gaps close (R18, R27;
decisions log 2026-11-28, consent once per machine, and the S10b review round 3 ruling).

Contract for `scripts/builder_trust.py` and its documents, beside tests/gate/test_builder_trust_fail_closed.py:

- **Refused outcome:** a command that cannot be trusted is never printed as an ordinary prompt line.
  - Interactive `check` prints `<name>: <command> (timeout <n> min) (cannot be trusted: <reason>)`.
  - `--unattended` prints `Skipped: <name> (cannot be trusted: <reason>)`.
  - It is never written to --out.
  - The reasons, exactly:
    - `shell syntax`: an operator, redirection, `$`, a backtick, or a command that does not split, such as an
      open quote;
    - `inline code`;
    - `env -C`: `env -C` or `env --chdir`;
    - `unresolvable`: a command after a wrapper that PATH cannot find, or a repo file it names that does not
      exist.
- **references/report.md** lists `<name> (cannot be trusted: <reason>)` on its `Skipped:` line.
- **docs/outside-builders.md:**
  - says such a command never runs through the gated build and its logic belongs in a repository script;
  - no longer says it "asks every time".
- **`--opt=value` words:** the part after the first `=` of a `-`-prefixed word is keyed when it names a repo
  file (`tool --script=bin/build`, `tool -o=scripts/x.sh`).
- **Bare words:** every bare word is looked up through PATH, and keyed when it resolves inside the top-level.
  `sudo build` and `time build`, with the repo's bin/ first on the run PATH, ask again after a change to
  bin/build.
- **Inline code**, refused for:
  - `osascript -e`, `fish -c`, `pwsh -c`, `pwsh -Command`, `lua -e`, `Rscript -e` and `expect -c`;
  - `php -R`, `php -B` and `php -E`.

Every case is one the round 4 resolver would trust or print plain, so each fails for its own rule. The program
words resolve to stub tools in a folder outside the repository that comes first on PATH. Standard library only.

    env -u GIT_OPTIONAL_LOCKS python3 -m unittest discover -s tests/gate -p 'test_builder_trust_refusal_outcome.py'
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from outside_builder_support import BUILDERS_DOC, REPO, assert_line, has_line, read_new  # noqa: E402
from test_builder_trust import TRUST  # noqa: E402
from test_builder_trust_fail_closed import STUB, STUBS, FailClosedTest  # noqa: E402
from test_builder_trust_repo_files import RepoBox, line  # noqa: E402

REPORT = REPO / "resources/boost/skills/laravel-gated-build/references/report.md"
MORE_STUBS = ("tool", "osascript", "fish", "pwsh", "lua", "Rscript", "expect")
REFUSED = {
    "true; bin/build": "shell syntax",
    "bin/build 'open quote": "shell syntax",
    "bash -lc true": "inline code",
    "env -C scripts true": "env -C",
    "env --chdir=scripts true": "env -C",
    "env nosuch-tool-xyz bin/build": "unresolvable",
    "./bin/missing --fast": "unresolvable",
}
OPTION_VALUES = {"tool --script=bin/build": "bin/build", "tool -o=scripts/x.sh": "scripts/x.sh"}
INLINE_CODE = ("osascript -e /dev/null", "fish -c /dev/null", "pwsh -c /dev/null", "pwsh -Command /dev/null",
               "lua -e /dev/null", "Rscript -e /dev/null", "expect -c /dev/null",
               "php -R /dev/null", "php -B /dev/null", "php -E /dev/null")


class OutcomeTest(FailClosedTest):
    def tools(self, box: RepoBox) -> Path:
        tools = box.tmp / "outcome-tools"
        if not tools.is_dir():
            tools.mkdir()
            for name in (*STUBS, *MORE_STUBS):
                (tools / name).write_text(STUB, encoding="utf-8")
                (tools / name).chmod(0o755)
        return tools

    def assert_cannot_be_trusted(self, box: RepoBox, command: str, reason: str, env: dict) -> None:
        builders = box.builders({"name": "local", "command": command})
        proc = box.add(builders, "local", env=env)
        self.assertEqual(proc.returncode, 2, f"{command}: " + proc.stdout + proc.stderr)
        self.assertFalse(box.trust_file.exists(), f"{command}: the trust file was written")
        self.assertEqual(self.lines(box, builders, env, unattended=False),
                         ([line("local", command) + f" (cannot be trusted: {reason})"], []))
        self.assertEqual(self.lines(box, builders, env), ([f"Skipped: local (cannot be trusted: {reason})"], []))


class RefusedOutcome(OutcomeTest):
    """Ruling 1: a refused command shows why, interactive and unattended."""

    def test_a_refused_command_prints_cannot_be_trusted_with_its_reason(self):
        for command, reason in REFUSED.items():
            with self.subTest(command=command):
                box = self.fresh()
                self.assert_cannot_be_trusted(box, command, reason, self.env(box))


class ResolverGaps(OutcomeTest):
    """Rulings 2, 3 and 4."""

    def test_an_option_value_naming_a_repo_file_is_keyed(self):
        for command, rel in OPTION_VALUES.items():
            with self.subTest(command=command):
                box = self.fresh()
                self.assert_change_asks_again(box, command, rel, self.env(box))

    def test_a_bare_word_found_in_the_repo_through_path_is_keyed(self):
        for command in ("sudo build", "time build"):
            with self.subTest(command=command):
                box = self.fresh()
                self.assert_change_asks_again(box, command, "bin/build", self.env(box, box.repo / "bin"))

    def test_more_inline_code_flags_cannot_be_trusted(self):
        for command in INLINE_CODE:
            with self.subTest(command=command):
                box = self.fresh()
                self.assert_cannot_be_trusted(box, command, "inline code", self.env(box))


class Documents(unittest.TestCase):
    def setUp(self):
        self.assertTrue(TRUST.is_file(), "scripts/builder_trust.py is missing")

    def test_the_report_lists_the_cannot_be_trusted_skip(self):
        assert_line(self, read_new(self, REPORT), r"^Skipped:", r"<name> \(cannot be trusted: <reason>\)",
                    label="the report's Skipped line lists <name> (cannot be trusted: <reason>)")

    def test_the_docs_say_a_refused_command_never_runs_through_the_gated_build(self):
        text = read_new(self, BUILDERS_DOC)
        assert_line(self, text, r"cannot be trusted", r"never runs", r"gated build", r"repository script",
                    label="a command that cannot be trusted never runs through the gated build; use a repository script")
        self.assertFalse(has_line(text, r"asks? every time"), "docs still say a refused command asks every time")


if __name__ == "__main__":
    unittest.main()
