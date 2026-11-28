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
- builders_check.py skips an Infinity or an integer timeout too large for a float instead of crashing.

Standard library only.

    env -u GIT_OPTIONAL_LOCKS python3 -m unittest discover -s tests/gate -p 'test_builder_trust_rules.py'
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
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
        changed = {**LOCAL, "command": "printf ran > RAN-other.txt; :"}
        self.assertEqual(self.box.add(self.box.builders(changed, out="changed.json"), "local").returncode, 0)
        listed = self.box.trust("list", "--root", str(self.box.repo))
        self.assertEqual(listed.stdout.splitlines(), ["local: printf ran > RAN-other.txt; : (timeout 30 min)"])
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


if __name__ == "__main__":
    unittest.main()
