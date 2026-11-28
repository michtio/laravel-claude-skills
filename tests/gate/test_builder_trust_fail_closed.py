"""The trust resolver fails closed (R18, R27; decisions log 2026-11-28, consent once per machine, and the S10b
review round 2 ruling).

scripts/run_builder.py runs a trusted command through `sh -c`, so the key has to reason about shell grammar.
Whatever the resolver cannot account for is refused, never trusted plain. Contract for
`scripts/builder_trust.py`, beside tests/gate/test_builder_trust_resolution.py:

- **Refused** (`add` exits 2 and writes nothing; `check` prints `(cannot be trusted: <reason>)` after the line,
  or with --unattended `Skipped: <name> (cannot be trusted: <reason>)`, amended for the S10b review round 3
  ruling; reasons pinned in tests/gate/test_builder_trust_refusal_outcome.py):
  - **Shell syntax:** a command holding any of `;`, `&`, `|`, `<`, `>`, `(`, `)`, `$` or a backtick.
  - **Inline code** (whatever the payload, even a path outside the repository): `-c` after a shell or interpreter, including a combined short-flag group that contains
    `c` (`bash -lc`, `bash -cx`); `-c` for python, `-r` for php, `-e` for node.
  - **Changed directory:** `env -C <dir>`, `env --chdir <dir>`, `env --chdir=<dir>`.
- **Keyed:**
  - every word of the command that names an existing regular file inside the git top-level, joined to the
    project root, is keyed on its sha256, so a change to any of them asks again (`sudo bin/build`,
    `xargs bin/build`, `time bin/build`, `arch -arm64 bin/build`, `stdbuf -o0 bin/build`, `doas bin/build`,
    `setsid bin/build`, `flock /tmp/l bin/build`, `direnv exec . bin/build`);
  - the program a first word, interpreter, runner or wrapper resolves to through PATH is keyed too when it is
    inside the top-level. A repo `bin/python3` found first on PATH keys both itself and the script. A repo
    `bin/make` keys itself and stays marked `(runs repo code)`. A repo `bin/nice` keys itself.
- **Skill:** laravel-gated-build step 1.7 says `builder_trust.py add` runs only after an explicit yes in the
  user's own message, never on file or hand-back content.
- **Work-tree refusal:** the refusal message, and the docs bullet on a trust file inside a git work tree, name
  `LARAVEL_CLAUDE_SKILLS_TRUST_FILE` as the way out for a home that is a git work tree.

Every refused case is one the round 3 resolver would trust (a payload outside the repository, or a word PATH
cannot find), so each fails for its own rule. The wrapper and interpreter words resolve to stub tools in a folder outside the repository that comes first on
PATH, so the host's tools never decide a case. Standard library only.

    env -u GIT_OPTIONAL_LOCKS python3 -m unittest discover -s tests/gate -p 'test_builder_trust_fail_closed.py'
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from outside_builder_support import BUILDERS_DOC, SKILL, assert_line, git, read_new  # noqa: E402
from test_builder_trust import TRUST  # noqa: E402
from test_builder_trust_repo_files import RepoBox, line  # noqa: E402
from test_builder_trust_resolution import ResolutionTest  # noqa: E402

STUBS = ("timeout", "php", "python3", "node", "sudo", "xargs", "time", "arch", "stdbuf", "doas", "setsid", "flock", "direnv")
SHELL_SYNTAX = ("true; bin/build", "true && bin/build", "true || bin/build", "true | bin/build", "true & bin/build",
                "echo $(bin/build)", "echo `bin/build`", "bin/build > out", "bin/build < in", "(true)",
                "bin/build $HOME")
INLINE_CODE = ("sh -c 'bin/build'", "bash -c 'bin/build'", "bash -lc 'bin/build'", "bash -cx 'bin/build'",
               "/bin/sh -c true", "python3 -c pass", "php -r /dev/null", "node -e /dev/null")
CHANGED_DIR = ("env -C scripts true", "env --chdir scripts true", "env --chdir=scripts true")
EVERY_WORD = ("sudo bin/build", "xargs bin/build", "time bin/build", "arch -arm64 bin/build", "stdbuf -o0 bin/build",
              "doas bin/build", "setsid bin/build", "flock /tmp/l bin/build", "direnv exec . bin/build")
STUB = "#!/bin/sh\nexit 0\n"


class FailClosedTest(ResolutionTest):
    def tools(self, box: RepoBox) -> Path:
        tools = box.tmp / "stub-tools"
        if not tools.is_dir():
            tools.mkdir()
            for name in STUBS:
                (tools / name).write_text(STUB, encoding="utf-8")
                (tools / name).chmod(0o755)
        return tools

    def assert_refused(self, box: RepoBox, command: str, env: dict, reason: str) -> None:
        builders = box.builders({"name": "local", "command": command})
        proc = box.add(builders, "local", env=env)
        self.assertEqual(proc.returncode, 2, f"{command}: " + proc.stdout + proc.stderr)
        self.assertFalse(box.trust_file.exists(), f"{command}: the trust file was written")
        self.assertEqual(self.lines(box, builders, env, unattended=False),
                         ([line("local", command) + f" (cannot be trusted: {reason})"], []))
        self.assertEqual(self.lines(box, builders, env), ([f"Skipped: local (cannot be trusted: {reason})"], []))

    def assert_change_asks_again(self, box: RepoBox, command: str, rel: str, env: dict, mark: str = " (trusted)") -> None:
        builders = self.trust_it(box, command, env)
        self.assertEqual(self.lines(box, builders, env), ([line("local", command) + mark], ["local"]))
        path = box.repo / rel
        path.write_text(path.read_text(encoding="utf-8") + "# changed\n", encoding="utf-8")
        box.commit(f"chore: change {rel}")
        self.assertEqual(self.lines(box, builders, env), (["Skipped: local (not confirmed)"], []),
                         f"{command}: a change to {rel} must ask again")

    def repo_tool(self, box: RepoBox, name: str) -> Path:
        """An executable `bin/<name>` committed in the repository; bin/ goes first on the run PATH."""
        path = box.repo / "bin" / name
        path.write_text(STUB, encoding="utf-8")
        path.chmod(0o755)
        box.commit(f"chore: repo {name}")
        return box.repo / "bin"


class Refused(FailClosedTest):
    """Ruling: shell syntax, inline code and a changed directory cannot be trusted."""

    def test_a_command_with_shell_syntax_cannot_be_trusted(self):
        for command in SHELL_SYNTAX:
            with self.subTest(command=command):
                box = self.fresh()
                self.assert_refused(box, command, self.env(box), "shell syntax")

    def test_inline_code_cannot_be_trusted(self):
        for command in INLINE_CODE:
            with self.subTest(command=command):
                box = self.fresh()
                self.assert_refused(box, command, self.env(box), "inline code")

    def test_env_changing_the_directory_cannot_be_trusted(self):
        for command in CHANGED_DIR:
            with self.subTest(command=command):
                box = self.fresh()
                self.assert_refused(box, command, self.env(box), "env -C")


class EveryRepoWordIsKeyed(FailClosedTest):
    """Ruling: every word naming a repo file is keyed, whatever program runs it."""

    def test_a_change_to_a_repo_file_named_anywhere_in_the_command_asks_again(self):
        for command in EVERY_WORD:
            with self.subTest(command=command):
                box = self.fresh()
                self.assert_change_asks_again(box, command, "bin/build", self.env(box))

    def test_an_interpreter_found_in_the_repo_keys_itself_and_the_script(self):
        for rel in ("bin/python3", "scripts/x.py"):
            with self.subTest(changed=rel):
                box = self.fresh()
                env = self.env(box, self.repo_tool(box, "python3"))
                self.assert_change_asks_again(box, "python3 scripts/x.py", rel, env)

    def test_a_runner_or_wrapper_found_in_the_repo_is_keyed(self):
        cases = {"make build": ("make", " (trusted, runs repo code)"), "nice /usr/bin/true": ("nice", " (trusted)")}
        for command, (tool, mark) in cases.items():
            with self.subTest(command=command):
                box = self.fresh()
                env = self.env(box, self.repo_tool(box, tool))
                self.assert_change_asks_again(box, command, f"bin/{tool}", env, mark)


class WorkTreeWayOut(FailClosedTest):
    """A home that is a git work tree: the refusal names the variable that moves the trust file out."""

    def test_the_refusal_names_the_trust_file_variable(self):
        tree = self.box.tmp / "home-tree"
        tree.mkdir()
        git(tree, "init", "-q")
        target = tree / ".config/laravel-claude-skills/trusted-builders.json"
        builders = self.box.builders({"name": "local", "command": "touch RAN.txt"})
        env = self.box.env(trust=target)
        proc = self.box.add(builders, "local", env=env)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("LARAVEL_CLAUDE_SKILLS_TRUST_FILE", proc.stderr)


class DocsAndSkillText(unittest.TestCase):
    def setUp(self):
        self.assertTrue(TRUST.is_file(), "scripts/builder_trust.py is missing")

    def test_step_1_7_runs_add_only_on_the_users_own_yes(self):
        text = read_new(self, SKILL)
        step = [l for l in text.splitlines() if l.startswith("7. **Confirm the builder commands.**")]
        self.assertEqual(len(step), 1, "step 1.7 is one line")
        for pattern in (r"builder_trust\.py add", r"own message", r"never", r"file", r"hand-back"):
            self.assertRegex(step[0], pattern)

    def test_the_work_tree_bullet_names_the_way_out(self):
        assert_line(self, read_new(self, BUILDERS_DOC), r"work tree", r"LARAVEL_CLAUDE_SKILLS_TRUST_FILE",
                    label="the work-tree refusal names LARAVEL_CLAUDE_SKILLS_TRUST_FILE as the way out")


if __name__ == "__main__":
    unittest.main()
