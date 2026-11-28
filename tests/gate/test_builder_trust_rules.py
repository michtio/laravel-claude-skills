"""Trust-list rules beyond the locked gate (R18, R27; decisions log 2026-11-28, consent once per machine).

Builder-added tests (G3) for `scripts/builder_trust.py`, beside tests/gate/test_builder_trust.py:

- a trust file another user owns is ignored, as one others can write is (the owner check);
- `add` and `remove` refuse, exit 2 and write nothing, when the trust file is group or other writable;
- `remove` refuses a trust file inside the project;
- `add` after a changed command keeps one entry per repository and name, holding the new command;
- `check` refuses (exit 2) a --builders file whose builder builders_check.py would have skipped;
- a trust file of valid JSON but another shape trusts nothing and is never overwritten;
- a project that is not a git repository is keyed on its real path;
- the identity ignores GIT_* variables (GIT_CONFIG_COUNT and GIT_CONFIG_KEY_<n> cannot change the origin);
- a trust file spelled with other letter case inside the project, on a case-insensitive volume, is ignored;
- builders_check.py skips an Infinity or an integer timeout too large for a float instead of crashing;
- an untrusted task-runner command shows `(runs repo code)` at the prompt (owner ruling, S10b round 2);
- a path outside the git top-level (absolute or `../`) names no repo file, so a missing one does not block add;
- `sh -c '<code>'` names no repo file (the code is the command text, already keyed);
- credentials are stripped from scheme URLs with a port, and an scp-like `git@host:path` stays as it is;
- the trust file is read through one descriptor (open, then fstat), never stat-then-open;
- add holds an exclusive lock from the read to the write, so a second writer waits;
- save fsyncs the folder after the replace;
- a trust file that fstat reports as not regular is refused even when its bytes are a valid trust file;
- a repo-file entry also keys on the file's real path: a symlink retargeted to an identical copy asks again;
- an interpreter or task runner is recognised by its resolved file name too (python3.13, a link to npm), and
  more wrapper option forms resolve (`env -u NAME`, `timeout --kill-after 5 60`, `nice -5`).

Standard library only.

    env -u GIT_OPTIONAL_LOCKS python3 -m unittest discover -s tests/gate -p 'test_builder_trust_rules.py'
"""
from __future__ import annotations

import importlib.util
import json
import os
import fcntl
import subprocess
import sys
import time
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_builder_trust import CHECK, LOCAL, ORIGIN, TRUST, TrustTest  # noqa: E402


def trust_module():
    """scripts/builder_trust.py imported as a module (it imports builders_check from its own folder)."""
    sys.path.insert(0, str(TRUST.parent))
    spec = importlib.util.spec_from_file_location("builder_trust_under_test", TRUST)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OwnerAndMode(TrustTest):
    def test_a_trust_file_another_user_owns_is_ignored(self):
        self.box.add(self.box.builders(LOCAL), "local")
        module = trust_module()
        folder = str(self.box.tmp / "unrelated")
        self.assertEqual(len(module.load(str(self.box.trust_file), (folder,))), 1)
        with mock.patch.object(module.os, "getuid", return_value=os.getuid() + 1):
            with self.assertRaises(module.Refused) as caught:
                module.load(str(self.box.trust_file), (folder,))
        self.assertIn("another user owns it", str(caught.exception))

    def test_add_and_remove_refuse_a_file_others_can_write_and_leave_it_as_it_is(self):
        builders = self.box.builders(LOCAL)
        self.box.add(builders, "local")
        os.chmod(self.box.trust_file, 0o664)
        before = self.box.trust_file.read_bytes()
        self.assertEqual(self.box.add(builders, "local").returncode, 2)
        proc = self.box.trust("remove", "--root", str(self.box.repo), "--name", "local")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(self.box.trust_file.read_bytes(), before)

    def test_remove_refuses_a_trust_file_inside_the_project(self):
        builders = self.box.builders(LOCAL)
        self.box.add(builders, "local")
        inside = self.box.repo / ".ai/trusted-builders.json"
        inside.write_bytes(self.box.trust_file.read_bytes())
        os.chmod(inside, 0o600)
        proc = self.box.trust("remove", "--root", str(self.box.repo), "--name", "local", env=self.box.env(trust=inside))
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertEqual(inside.read_bytes(), self.box.trust_file.read_bytes())


class Entries(TrustTest):
    def test_adding_a_changed_command_replaces_the_old_entry_of_that_name(self):
        self.box.add(self.box.builders(LOCAL), "local")
        changed = {**LOCAL, "command": "touch RAN-other.txt"}
        self.assertEqual(self.box.add(self.box.builders(changed, out="changed.json"), "local").returncode, 0)
        listed = self.box.trust("list", "--root", str(self.box.repo))
        self.assertEqual(listed.stdout.splitlines(), ["local: touch RAN-other.txt (timeout 30 min)"])
        _, names = self.box.check(self.box.builders(LOCAL, out="old.json"))
        self.assertEqual(names, [], "the old command is no longer trusted")

    def test_a_builders_file_with_a_builder_builders_check_skips_is_refused(self):
        builders = self.box.builders(LOCAL)
        data = json.loads(builders.read_text(encoding="utf-8"))
        data["builders"][0]["command"] = "printf ran‮ > x"
        builders.write_text(json.dumps(data), encoding="utf-8")
        proc, names = self.box.check(builders)
        self.assertEqual((proc.returncode, names), (2, None), proc.stdout + proc.stderr)

    def test_a_project_outside_git_is_keyed_on_its_real_path(self):
        with tempfile.TemporaryDirectory() as raw:
            plain = Path(raw).resolve() / "plain"
            plain.mkdir()
            builders = self.box.builders(LOCAL, root=plain, out="plain.json")
            self.assertEqual(self.box.add(builders, "local").returncode, 0)
            entry = json.loads(self.box.trust_file.read_text(encoding="utf-8"))["entries"][0]
            self.assertEqual((entry["repository"], entry["origin"]), (str(plain), ""))
            _, names = self.box.check(builders)
            self.assertEqual(names, ["local"])


class Shape(TrustTest):
    def test_valid_json_of_another_shape_trusts_nothing_and_is_never_overwritten(self):
        builders = self.box.builders(LOCAL)
        self.box.trust_file.parent.mkdir(parents=True)
        for text in ('{"version": 2, "entries": []}', '[]', '{"version": 1}', '{"version": 1, "entries": [{"name": "local"}]}'):
            with self.subTest(text=text):
                self.box.trust_file.write_text(text, encoding="utf-8")
                os.chmod(self.box.trust_file, 0o600)
                proc, names = self.box.check(builders)
                self.assertEqual((proc.returncode, names), (0, []), proc.stdout + proc.stderr)
                self.assertIn(str(self.box.trust_file), proc.stderr)
                self.assertEqual(self.box.add(builders, "local").returncode, 2)
                self.assertEqual(self.box.trust_file.read_text(encoding="utf-8"), text)


class Identity(TrustTest):
    def test_git_variables_cannot_change_the_origin_in_the_key(self):
        builders = self.box.builders(LOCAL)
        env = self.box.env()
        env.update({"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "remote.origin.url",
                    "GIT_CONFIG_VALUE_0": "https://example.com/spoofed/app.git"})
        self.assertEqual(self.box.add(builders, "local", env=env).returncode, 0)
        entry = json.loads(self.box.trust_file.read_text(encoding="utf-8"))["entries"][0]
        self.assertEqual(entry["origin"], ORIGIN)

    def test_a_differently_cased_trust_path_inside_the_project_is_ignored(self):
        repo = self.box.repo
        swapped = repo.parent / repo.name.swapcase()
        if not swapped.exists():
            self.skipTest("the temp volume is case-sensitive")
        self.box.add(self.box.builders(LOCAL), "local")
        inside = repo / ".ai/trusted-builders.json"
        inside.write_bytes(self.box.trust_file.read_bytes())
        os.chmod(inside, 0o600)
        self.assert_untrusted(self.box.builders(LOCAL, out="later.json"),
                              env=self.box.env(trust=swapped / ".ai/trusted-builders.json"))


class Timeouts(TrustTest):
    def test_an_infinite_or_huge_timeout_is_skipped_not_a_crash(self):
        for label, raw in (("Infinity", "Infinity"), ("huge integer", "1" + "0" * 400)):
            with self.subTest(timeout=label):
                profile = self.box.repo / ".ai/skills-profile.json"
                profile.parent.mkdir(exist_ok=True)
                profile.write_text('{"version": 1, "builders": [{"name": "local", "command": "true", "timeout_minutes": %s}]}' % raw,
                                   encoding="utf-8")
                proc = subprocess.run([sys.executable, str(CHECK), "--profile", str(profile), "--root", str(self.box.repo),
                                       "--out", str(self.box.work / "b.json")], capture_output=True, text=True, timeout=30)
                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                self.assertIn("Skipped: builders.0 (invalid timeout_minutes", proc.stdout)


class RepoCodeAtThePrompt(TrustTest):
    def test_an_untrusted_task_runner_is_marked_before_the_yes(self):
        runner = {"name": "local", "command": "make build"}
        builders = self.box.builders(runner)
        proc, names = self.box.check(builders)
        self.assertEqual((proc.stdout.splitlines(), names), (["local: make build (timeout 30 min) (runs repo code)"], []))
        proc, _ = self.box.check(builders, unattended=True)
        self.assertEqual(proc.stdout.splitlines(), ["Skipped: local (not confirmed)"])

    def test_a_path_outside_the_repository_names_no_repo_file(self):
        for command in ("/nonexistent-tool-dir/builder --fast", "../nonexistent-sibling/builder", "sh ../nonexistent-sibling/x.sh"):
            with self.subTest(command=command):
                builders = self.box.builders({"name": "local", "command": command}, out="outside.json")
                proc = self.box.add(builders, "local")
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                _, names = self.box.check(builders)
                self.assertEqual(names, ["local"])

    def test_inline_shell_code_cannot_be_trusted(self):
        command = {"name": "local", "command": "bash -c 'touch RAN.txt'"}
        builders = self.box.builders(command)
        self.assertEqual(self.box.add(builders, "local").returncode, 2)
        self.assertFalse(self.box.trust_file.exists())
        proc, names = self.box.check(builders)
        self.assertEqual((proc.stdout.splitlines(), names),
                         (["local: bash -c 'touch RAN.txt' (timeout 30 min) (cannot be trusted: inline code)"], []))


class Credentials(unittest.TestCase):
    def test_scheme_urls_lose_their_credentials_and_scp_urls_stay(self):
        module = trust_module()
        cases = {
            "https://u:p@example.com:8443/acme/app.git": "https://example.com:8443/acme/app.git",
            "ssh://git@example.com/acme/app.git": "ssh://example.com/acme/app.git",
            "git@example.com:acme/app.git": "git@example.com:acme/app.git",
            "https://example.com/a@b/app.git": "https://example.com/a@b/app.git",
            "": "",
        }
        for url, expected in cases.items():
            with self.subTest(url=url):
                self.assertEqual(module.without_credentials(url), expected)


class OneDescriptor(TrustTest):
    def test_the_trust_file_is_never_stat_then_opened(self):
        self.box.add(self.box.builders(LOCAL), "local")
        module = trust_module()
        target = str(self.box.trust_file)
        real_stat = os.stat

        def guarded(path, *args, **kwargs):
            if str(path) == target:
                raise AssertionError("os.stat on the trust file path: stat-then-open")
            return real_stat(path, *args, **kwargs)

        with mock.patch.object(module.os, "stat", side_effect=guarded):
            entries = module.load(target, (str(self.box.tmp / "unrelated"),))
        self.assertEqual(len(entries), 1)


class Locking(TrustTest):
    def test_add_waits_for_the_lock_and_then_writes(self):
        builders = self.box.builders(LOCAL)
        self.box.trust_file.parent.mkdir(parents=True)
        lock = os.open(str(self.box.trust_file) + ".lock", os.O_RDWR | os.O_CREAT, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            proc = subprocess.Popen([sys.executable, str(TRUST), "add", "--builders", str(builders), "--name", "local"],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=self.box.env())
            time.sleep(1.5)
            self.assertIsNone(proc.poll(), "add did not wait for the lock")
            self.assertFalse(self.box.trust_file.exists())
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
            os.close(lock)
        out, err = proc.communicate(timeout=30)
        self.assertEqual((proc.returncode, out.strip()), (0, "Trusted: local"), err)
        self.assertTrue(self.box.trust_file.is_file())


class FolderSync(TrustTest):
    def test_save_fsyncs_after_the_replace_too(self):
        module = trust_module()
        order = []
        real_fsync, real_replace = os.fsync, os.replace
        with mock.patch.object(module.os, "fsync", side_effect=lambda fd: (order.append("fsync"), real_fsync(fd))[1]), \
                mock.patch.object(module.os, "replace", side_effect=lambda a, b: (order.append("replace"), real_replace(a, b))[1]):
            module.save(str(self.box.trust_file), [])
        self.assertIn("fsync", order[order.index("replace") + 1:], f"calls: {order}")


class ResolvedNames(TrustTest):
    SCRIPT = "scripts/x.py"

    def setUp(self):
        super().setUp()
        (self.box.repo / "scripts").mkdir()
        (self.box.repo / self.SCRIPT).write_text("print('x')\n", encoding="utf-8")
        (self.box.repo / "bin").mkdir()
        (self.box.repo / "bin/build").write_text("#!/bin/sh\n", encoding="utf-8")
        os.chmod(self.box.repo / "bin/build", 0o755)
        self.tools = self.box.tmp / "tools"
        self.tools.mkdir()
        for name in ("python3.13", "npm"):
            (self.tools / name).write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            os.chmod(self.tools / name, 0o755)
        (self.tools / "mynpm").symlink_to(self.tools / "npm")
        (self.tools / "timeout").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        os.chmod(self.tools / "timeout", 0o755)

    def env_with_tools(self) -> dict:
        env = self.box.env()
        env["PATH"] = f"{self.tools}{os.pathsep}{env.get('PATH', '')}"
        return env

    def trusted_line(self, command: str) -> str:
        env = self.env_with_tools()
        builders = self.box.builders({"name": "local", "command": command}, out="named.json")
        proc = self.box.add(builders, "local", env=env)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        proc, _ = self.box.check(builders, env=env)
        return proc.stdout.strip()

    def test_a_versioned_interpreter_path_keys_the_script(self):
        command = f"{self.tools}/python3.13 {self.SCRIPT}"
        self.assertTrue(self.trusted_line(command).endswith("(trusted)"))
        (self.box.repo / self.SCRIPT).write_text("print('changed')\n", encoding="utf-8")
        _, names = self.box.check(self.box.builders({"name": "local", "command": command}, out="again.json"),
                                  env=self.env_with_tools())
        self.assertEqual(names, [], "a change to the script must ask again")

    def test_a_link_to_a_task_runner_is_marked(self):
        self.assertTrue(self.trusted_line("mynpm run build").endswith("(trusted, runs repo code)"))

    def test_more_wrapper_option_forms_key_the_repo_file(self):
        for command in ("env -u HOME bin/build", "timeout --kill-after 5 60 bin/build", "nice -5 bin/build"):
            with self.subTest(command=command):
                self.trusted_line(command)
                (self.box.repo / "bin/build").write_text("#!/bin/sh\n# changed\n", encoding="utf-8")
                _, names = self.box.check(self.box.builders({"name": "local", "command": command}, out="again.json"),
                                          env=self.env_with_tools())
                self.assertEqual(names, [], f"{command}: a change to bin/build must ask again")
                (self.box.repo / "bin/build").write_text("#!/bin/sh\n", encoding="utf-8")


class NotRegular(TrustTest):
    def test_a_trust_file_fstat_reports_as_not_regular_is_refused(self):
        import stat as stat_module
        self.box.add(self.box.builders(LOCAL), "local")
        module = trust_module()
        real_fstat = os.fstat

        def as_fifo(fd):
            info = list(real_fstat(fd))
            info[0] = stat_module.S_IFIFO | 0o600
            return os.stat_result(info)

        with mock.patch.object(module.os, "fstat", side_effect=as_fifo):
            with self.assertRaises(module.Refused) as caught:
                module.load(str(self.box.trust_file), (str(self.box.tmp / "unrelated"),))
        self.assertIn("not a regular file", str(caught.exception))


class FilePathKey(TrustTest):
    def test_a_symlink_retargeted_to_an_identical_copy_asks_again(self):
        repo = self.box.repo
        (repo / "bin").mkdir()
        for name in ("real-a", "real-b"):
            (repo / "bin" / name).write_text("#!/bin/sh\necho same\n", encoding="utf-8")
            os.chmod(repo / "bin" / name, 0o755)
        (repo / "bin/linked").symlink_to("real-a")
        builders = self.box.builders({"name": "local", "command": "./bin/linked"})
        self.assertEqual(self.box.add(builders, "local").returncode, 0)
        _, names = self.box.check(builders)
        self.assertEqual(names, ["local"])
        (repo / "bin/linked").unlink()
        (repo / "bin/linked").symlink_to("real-b")
        _, names = self.box.check(builders)
        self.assertEqual(names, [], "the same bytes at another real path must ask again")


if __name__ == "__main__":
    unittest.main()
