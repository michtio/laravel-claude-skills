"""The trust list: an outside-builder command confirmed once is trusted on this machine (R18, R27).

Requirements R18 and R27; decisions log 2026-11-28, "Outside-builder consent is given once per machine: the
yes is kept in a trust list outside the repo, keyed on the exact command, so unattended runs use approved
builders; a changed command asks again; a cloned repo cannot approve itself". Standard library only.

Contract (the script `scripts/builder_trust.py`, Python 3.9+, standard library only):

    builder_trust.py check  --builders <file> --out <file> [--unattended]
    builder_trust.py add    --builders <file> --name <name>
    builder_trust.py list   --root <project-root>
    builder_trust.py remove --root <project-root> --name <name>

- `--builders` is the file scripts/builders_check.py wrote (`project_root` and the usable `builders`).
- An entry is keyed on the repository identity and the builder's exact name, command and timeout_minutes.
  The repository identity is the real path of the git top-level of the project root plus its
  `remote.origin.url` (empty when there is none): another clone, or a changed origin, is another repository.
- The trust file is `$LARAVEL_CLAUDE_SKILLS_TRUST_FILE` when set, else
  `$XDG_CONFIG_HOME/laravel-claude-skills/trusted-builders.json` when XDG_CONFIG_HOME is set, else
  `~/.config/laravel-claude-skills/trusted-builders.json`. `add` creates it with mode 0600.
- A trust file whose real path is inside the project root (the git top-level), whose group or other write bit
  is set, or that is not valid is ignored: nothing in it is trusted (a corrupt one is named on stderr).
- `check` prints one line per builder of --builders, in order: `<name>: <command> (timeout <n> min) (trusted)`
  for a trusted one, `<name>: <command> (timeout <n> min)` for the rest, or with --unattended
  `Skipped: <name> (not confirmed)` for the rest. It writes --out in the --builders format with the trusted
  builders only, which scripts/run_builder.py --builders reads, so an untrusted builder cannot be run from it.
  Exit 0; exit 2 for a usage error or an unreadable --builders file.
- `add` records the builder of --builders with that name (never a command from the arguments), prints
  `Trusted: <name>`, exit 0; adding it again keeps one entry. Exit 2, trust file untouched, for a name not in
  --builders, a trust file inside the project, or a corrupt trust file.
- `list` prints `<name>: <command> (timeout <n> min)` per entry of this repository. `remove` deletes the
  entries of this repository with that name, prints `Removed: <name>`, exit 0; exit 1 when there is none.
  Entries of other repositories stay.

    env -u GIT_OPTIONAL_LOCKS python3 -m unittest discover -s tests/gate -p 'test_builder_trust.py'
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from outside_builder_support import REPO, git  # noqa: E402

TRUST = REPO / "scripts/builder_trust.py"
CHECK = REPO / "scripts/builders_check.py"
RUNNER = REPO / "scripts/run_builder.py"
TRUST_ENV = "LARAVEL_CLAUDE_SKILLS_TRUST_FILE"
HOME_TRUST = ".config/laravel-claude-skills/trusted-builders.json"
XDG_TRUST = "laravel-claude-skills/trusted-builders.json"
ORIGIN = "https://example.com/acme/app.git"
LOCAL = {"name": "local", "command": "touch RAN-local.txt"}
TEAM = {"name": "team", "command": "touch RAN-team.txt"}


class Sandbox:
    """A temp home, a work folder and a git project with an origin, all outside this repository."""

    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.home = tmp / "home"
        self.home.mkdir()
        self.work = tmp / "work"
        self.work.mkdir()
        self.trust_file = tmp / "machine" / "trusted-builders.json"
        self.repo = self.clone("app")

    def clone(self, name: str, origin: str = ORIGIN) -> Path:
        root = self.tmp / name
        root.mkdir()
        git(root, "init", "-q")
        git(root, "remote", "add", "origin", origin)
        return root

    def env(self, trust: Path | None | str = "default-test-file", xdg: Path | None = None, home: Path | None = None) -> dict:
        env = {k: v for k, v in os.environ.items()
               if k not in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OPTIONAL_LOCKS", TRUST_ENV, "XDG_CONFIG_HOME")}
        env["HOME"] = str(home or self.home)
        if trust == "default-test-file":
            env[TRUST_ENV] = str(self.trust_file)
        elif trust is not None:
            env[TRUST_ENV] = str(trust)
        if xdg is not None:
            env["XDG_CONFIG_HOME"] = str(xdg)
        return env

    def builders(self, *builders: dict, root: Path | None = None, out: str = "builders.json") -> Path:
        """The profile written to the project, checked by builders_check.py: the file the gated build makes."""
        root = root or self.repo
        (root / ".ai").mkdir(exist_ok=True)
        (root / ".ai/skills-profile.json").write_text(json.dumps({"version": 1, "builders": list(builders)}), encoding="utf-8")
        path = self.work / out
        proc = subprocess.run([sys.executable, str(CHECK), "--profile", str(root / ".ai/skills-profile.json"),
                               "--root", str(root), "--out", str(path)], capture_output=True, text=True, timeout=30)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        return path

    def trust(self, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(TRUST), *args], capture_output=True, text=True, timeout=30,
                              env=env if env is not None else self.env(), cwd=self.tmp)

    def add(self, builders: Path, name: str, env: dict | None = None) -> subprocess.CompletedProcess:
        return self.trust("add", "--builders", str(builders), "--name", name, env=env)

    def check(self, builders: Path, unattended: bool = False, env: dict | None = None) -> tuple:
        out = self.work / "run.json"
        if out.exists():
            out.unlink()
        args = ["check", "--builders", str(builders), "--out", str(out)] + (["--unattended"] if unattended else [])
        proc = self.trust(*args, env=env)
        names = [b["name"] for b in json.loads(out.read_text(encoding="utf-8"))["builders"]] if out.is_file() else None
        return proc, names


class TrustTest(unittest.TestCase):
    def setUp(self):
        self.assertTrue(TRUST.is_file(), "scripts/builder_trust.py is missing")
        self._tmp = tempfile.TemporaryDirectory()
        self.box = Sandbox(Path(self._tmp.name).resolve())

    def tearDown(self):
        self._tmp.cleanup()

    def assert_untrusted(self, builders: Path, name: str = "local", env: dict | None = None) -> None:
        proc, names = self.box.check(builders, unattended=True, env=env)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn(f"Skipped: {name} (not confirmed)", proc.stdout.splitlines())
        self.assertNotIn("(trusted)", proc.stdout)
        self.assertEqual(names, [])


class Confirming(TrustTest):
    """R18: a builder confirmed once is trusted on the next run, and the printed list marks it."""

    def test_an_unconfirmed_builder_is_printed_unmarked_and_not_written_for_the_runner(self):
        builders = self.box.builders(LOCAL)
        proc, names = self.box.check(builders)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout.splitlines(), ["local: touch RAN-local.txt (timeout 30 min)"])
        self.assertEqual(names, [])
        written = json.loads((self.box.work / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(written["project_root"], str(self.box.repo))

    def test_a_confirmed_builder_is_marked_trusted_on_the_next_run(self):
        builders = self.box.builders(LOCAL)
        proc = self.box.add(builders, "local")
        self.assertEqual((proc.returncode, proc.stdout.strip()), (0, "Trusted: local"), proc.stderr)
        proc, names = self.box.check(self.box.builders(LOCAL, out="later.json"))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout.splitlines(), ["local: touch RAN-local.txt (timeout 30 min) (trusted)"])
        self.assertEqual(names, ["local"])

    def test_adding_twice_keeps_one_entry(self):
        builders = self.box.builders(LOCAL)
        self.box.add(builders, "local")
        self.assertEqual(self.box.add(builders, "local").returncode, 0)
        proc = self.box.trust("list", "--root", str(self.box.repo))
        self.assertEqual(proc.stdout.splitlines(), ["local: touch RAN-local.txt (timeout 30 min)"])

    def test_a_name_not_in_the_checked_builders_is_refused_and_nothing_is_written(self):
        builders = self.box.builders(LOCAL)
        proc = self.box.add(builders, "team")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertFalse(self.box.trust_file.exists())


class Unattended(TrustTest):
    """R18, R27: an unattended run runs a trusted builder without asking and skips every other one."""

    def test_a_trusted_builder_runs_and_an_untrusted_one_is_skipped_and_cannot_run(self):
        self.box.add(self.box.builders(LOCAL), "local")
        builders = self.box.builders(LOCAL, TEAM, out="later.json")
        proc, names = self.box.check(builders, unattended=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout.splitlines(),
                         ["local: touch RAN-local.txt (timeout 30 min) (trusted)", "Skipped: team (not confirmed)"])
        self.assertEqual(names, ["local"])
        run = self.box.work / "run.json"
        brief, handback = self.box.work / "brief.md", self.box.work / "handback.md"
        brief.write_text("# Brief\n", encoding="utf-8")
        ran = subprocess.run([sys.executable, str(RUNNER), "--builders", str(run), "--name", "local", str(brief), str(handback)],
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
        self.assertTrue((self.box.repo / "RAN-local.txt").is_file())
        refused = subprocess.run([sys.executable, str(RUNNER), "--builders", str(run), "--name", "team", str(brief), str(handback)],
                                 capture_output=True, text=True, timeout=60)
        self.assertEqual(refused.returncode, 64, refused.stdout + refused.stderr)
        self.assertFalse((self.box.repo / "RAN-team.txt").exists())


class ChangesAskAgain(TrustTest):
    """Ruling 2026-11-28: a changed command asks again; so does a changed timeout, a renamed or a new builder."""

    def test_any_change_to_the_builder_asks_again(self):
        changes = {
            "one character in the command": ({**LOCAL, "command": "touch RAN-local.txT"}, "local"),
            "a trailing space in the command": ({**LOCAL, "command": LOCAL["command"] + " "}, "local"),
            "a changed timeout": ({**LOCAL, "timeout_minutes": 31}, "local"),
            "a renamed builder": ({**LOCAL, "name": "local2"}, "local2"),
        }
        self.box.add(self.box.builders({**LOCAL, "timeout_minutes": 30}), "local")
        for label, (changed, name) in changes.items():
            with self.subTest(change=label):
                builders = self.box.builders(changed, out="changed.json")
                self.assert_untrusted(builders, name)
                proc, _ = self.box.check(builders)
                self.assertNotIn("(trusted)", proc.stdout)

    def test_a_new_builder_asks_while_the_confirmed_one_stays_trusted(self):
        self.box.add(self.box.builders(LOCAL), "local")
        proc, names = self.box.check(self.box.builders(LOCAL, TEAM, out="later.json"), unattended=True)
        self.assertIn("Skipped: team (not confirmed)", proc.stdout.splitlines())
        self.assertEqual(names, ["local"])

    def test_another_clone_or_a_changed_origin_is_another_repository(self):
        self.box.add(self.box.builders(LOCAL), "local")
        other = self.box.clone("other-clone")
        with self.subTest(case="same origin, another clone"):
            self.assert_untrusted(self.box.builders(LOCAL, root=other, out="other.json"))
        with self.subTest(case="same clone, changed origin"):
            git(self.box.repo, "remote", "set-url", "origin", "https://example.com/someone-else/app.git")
            self.assert_untrusted(self.box.builders(LOCAL, out="moved.json"))


class InsideTheProject(TrustTest):
    """Ruling 2026-11-28: a cloned repo cannot approve itself; a trust file inside the project is ignored."""

    def trusted_copy(self, destination: Path) -> bytes:
        """A trust file that does trust LOCAL for this project, made by `add` outside it and copied to destination."""
        self.box.add(self.box.builders(LOCAL), "local")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.box.trust_file, destination)
        os.chmod(destination, 0o600)
        return destination.read_bytes()

    def test_a_trust_file_inside_the_project_is_ignored_however_it_is_reached(self):
        repo, box = self.box.repo, self.box
        inside = repo / ".ai/trusted-builders.json"
        self.trusted_copy(inside)
        self.trusted_copy(repo / ".config" / XDG_TRUST)
        self.trusted_copy(repo / HOME_TRUST)
        link = box.tmp / "elsewhere" / "trusted-builders.json"
        link.parent.mkdir()
        link.symlink_to(inside)
        empty_home = box.tmp / "empty-home"
        empty_home.mkdir()
        cases = {
            "the env var names it": box.env(trust=inside),
            "the env var names a symlink to it": box.env(trust=link),
            "XDG_CONFIG_HOME is inside the project": box.env(trust=None, xdg=repo / ".config"),
            "HOME is the project": box.env(trust=None, home=repo),
            "only the project has one, the machine none": box.env(trust=None, home=empty_home),
        }
        builders = box.builders(LOCAL, out="later.json")
        for label, env in cases.items():
            with self.subTest(case=label):
                self.assert_untrusted(builders, env=env)

    def test_add_refuses_to_write_a_trust_file_inside_the_project(self):
        inside = self.box.repo / ".ai/trusted-builders.json"
        builders = self.box.builders(LOCAL)
        proc = self.box.add(builders, "local", env=self.box.env(trust=inside))
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertFalse(inside.exists())


class Location(TrustTest):
    """The trust file lives in the user's config folder, outside every repository."""

    def test_the_default_is_under_home_config(self):
        builders = self.box.builders(LOCAL)
        env = self.box.env(trust=None)
        self.assertEqual(self.box.add(builders, "local", env=env).returncode, 0)
        self.assertTrue((self.box.home / HOME_TRUST).is_file(), f"no {HOME_TRUST} under HOME")
        proc, names = self.box.check(builders, env=env)
        self.assertEqual(names, ["local"], proc.stdout + proc.stderr)

    def test_xdg_config_home_moves_it(self):
        xdg = self.box.tmp / "xdg"
        builders = self.box.builders(LOCAL)
        env = self.box.env(trust=None, xdg=xdg)
        self.assertEqual(self.box.add(builders, "local", env=env).returncode, 0)
        self.assertTrue((xdg / XDG_TRUST).is_file(), f"no {XDG_TRUST} under XDG_CONFIG_HOME")
        self.assertFalse((self.box.home / HOME_TRUST).exists())

    def test_it_is_created_readable_and_writable_by_the_owner_only(self):
        self.box.add(self.box.builders(LOCAL), "local")
        self.assertEqual(stat.S_IMODE(self.box.trust_file.stat().st_mode), 0o600)

    def test_a_file_others_can_write_is_ignored(self):
        builders = self.box.builders(LOCAL)
        self.box.add(builders, "local")
        for mode, trusted in ((0o644, True), (0o620, False), (0o602, False), (0o666, False)):
            with self.subTest(mode=oct(mode)):
                os.chmod(self.box.trust_file, mode)
                _, names = self.box.check(builders)
                self.assertEqual(names, ["local"] if trusted else [])

    def test_a_corrupt_trust_file_trusts_nothing_and_is_never_overwritten(self):
        builders = self.box.builders(LOCAL)
        self.box.trust_file.parent.mkdir(parents=True)
        self.box.trust_file.write_text("{", encoding="utf-8")
        os.chmod(self.box.trust_file, 0o600)
        proc, names = self.box.check(builders)
        self.assertEqual((proc.returncode, names), (0, []), proc.stdout + proc.stderr)
        self.assertIn(str(self.box.trust_file), proc.stderr)
        self.assertEqual(self.box.add(builders, "local").returncode, 2)
        self.assertEqual(self.box.trust_file.read_text(encoding="utf-8"), "{")


class Revoking(TrustTest):
    """A documented way to remove an entry: `remove --root <project root> --name <name>`."""

    def test_remove_revokes_one_builder_of_this_repository_only(self):
        self.box.add(self.box.builders(LOCAL, TEAM), "local")
        self.box.add(self.box.builders(LOCAL, TEAM), "team")
        other = self.box.clone("other-clone")
        other_builders = self.box.builders(LOCAL, root=other, out="other.json")
        self.box.add(other_builders, "local")

        proc = self.box.trust("remove", "--root", str(self.box.repo), "--name", "local")
        self.assertEqual((proc.returncode, proc.stdout.strip()), (0, "Removed: local"), proc.stderr)

        proc, names = self.box.check(self.box.builders(LOCAL, TEAM, out="later.json"), unattended=True)
        self.assertEqual(names, ["team"])
        self.assertIn("Skipped: local (not confirmed)", proc.stdout.splitlines())
        listed = self.box.trust("list", "--root", str(self.box.repo))
        self.assertEqual(listed.stdout.splitlines(), ["team: touch RAN-team.txt (timeout 30 min)"])
        _, names = self.box.check(other_builders)
        self.assertEqual(names, ["local"], "the other clone's entry was removed too")

    def test_removing_an_entry_that_does_not_exist_exits_1(self):
        proc = self.box.trust("remove", "--root", str(self.box.repo), "--name", "local")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)


class BadCalls(TrustTest):
    def test_bad_calls_exit_2(self):
        missing = self.box.work / "none.json"
        for label, args in {"no arguments": (), "unknown action": ("trust",),
                            "check without --out": ("check", "--builders", str(missing)),
                            "unreadable builders file": ("check", "--builders", str(missing), "--out", str(self.box.work / "o.json"))}.items():
            with self.subTest(case=label):
                self.assertEqual(self.box.trust(*args).returncode, 2)


if __name__ == "__main__":
    unittest.main()
