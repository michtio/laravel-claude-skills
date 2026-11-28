"""The builders check: which profile builders may run, printed for the user's yes and written for the runner.

Requirements R18 (the outside builder named in the profile gets the brief) and R27 (an unusable builder is
skipped and reported, never silently). Builder-added test (G3), beside the S10 gate: a profile is a file in the
repository, so a builder name or timeout must never reach a shell line unchecked; names must match
^[A-Za-z0-9._-]{1,64}$ in full (a trailing newline is refused, as the setup's ProfileValidator does), commands are one line with no control, format or line/paragraph separator characters (Unicode C*, Zl, Zp:
no right-to-left override or zero-width character can disguise the printed consent line), and timeouts are numbers above 0.
Standard library only.

    python3 -m unittest discover -s tests/gate -p 'test_builders_check.py'
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CHECK = REPO / "scripts/builders_check.py"


def run(tmp: Path, profile) -> subprocess.CompletedProcess:
    path = tmp / "skills-profile.json"
    path.write_text(profile if isinstance(profile, str) else json.dumps(profile), encoding="utf-8")
    return subprocess.run([sys.executable, str(CHECK), "--profile", str(path), "--root", str(tmp),
                           "--out", str(tmp / "builders.json")], cwd=tmp, capture_output=True, text=True, timeout=30)


def written(tmp: Path) -> dict:
    return json.loads((tmp / "builders.json").read_text(encoding="utf-8"))


class ValidBuilders(unittest.TestCase):
    """R18: each usable builder is printed as the user confirms it and written for the runner."""

    def test_valid_builders_are_printed_for_confirmation_and_written_in_order(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw).resolve()
            proc = run(tmp, {"version": 1, "builders": [
                {"name": "local", "command": "run-local-builder --quiet", "timeout_minutes": 30},
                {"name": "team.v2", "command": "./bin/team 'a b'"},
                {"name": "fast", "command": "./bin/fast", "timeout_minutes": 2.5},
            ]})
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(proc.stdout.splitlines(), [
                "local: run-local-builder --quiet (timeout 30 min)",
                "team.v2: ./bin/team 'a b' (timeout 30 min)",
                "fast: ./bin/fast (timeout 2.5 min)",
            ])
            data = written(tmp)
            self.assertEqual(data["project_root"], str(tmp))
            self.assertEqual([b["name"] for b in data["builders"]], ["local", "team.v2", "fast"])
            self.assertEqual(data["builders"][1], {"name": "team.v2", "command": "./bin/team 'a b'", "timeout_minutes": 30})


class UnsafeBuilders(unittest.TestCase):
    """R27: an unusable builder is skipped with a reason, by its position, and never written for the runner."""

    def test_each_unusable_builder_is_skipped_by_position_with_its_reason(self):
        cases = {
            "name with a command substitution": ({"name": "x$(touch PWNED)", "command": "true"}, "name"),
            "name with a space": ({"name": "a b", "command": "true"}, "name"),
            "name with a trailing newline": ({"name": "local-ai\n", "command": "true"}, "name"),
            "name with a single quote": ({"name": "a'b", "command": "true"}, "name"),
            "name too long": ({"name": "a" * 65, "command": "true"}, "name"),
            "name not a string": ({"name": 7, "command": "true"}, "name"),
            "missing command": ({"name": "a"}, "command"),
            "empty command": ({"name": "a", "command": ""}, "command"),
            "command with a newline": ({"name": "a", "command": "true\nrm -rf ~"}, "command"),
            "command with an escape": ({"name": "a", "command": "true\x1b[2K"}, "command"),
            "command with U+202E": ({"name": "a", "command": "true \u202e x"}, "command"),
            "command with U+200B": ({"name": "a", "command": "true \u200b x"}, "command"),
            "command with U+2028": ({"name": "a", "command": "true \u2028 x"}, "command"),
            "command with U+2029": ({"name": "a", "command": "true \u2029 x"}, "command"),
            "command with U+FEFF": ({"name": "a", "command": "true \ufeff x"}, "command"),
            "timeout zero": ({"name": "a", "command": "true", "timeout_minutes": 0}, "timeout_minutes"),
            "timeout negative": ({"name": "a", "command": "true", "timeout_minutes": -1}, "timeout_minutes"),
            "timeout a string": ({"name": "a", "command": "true", "timeout_minutes": "5"}, "timeout_minutes"),
            "timeout a boolean": ({"name": "a", "command": "true", "timeout_minutes": True}, "timeout_minutes"),
            "timeout with a command": ({"name": "a", "command": "true", "timeout_minutes": "1; touch PWNED"}, "timeout_minutes"),
            "not an object": ("local", "object"),
        }
        for label, (builder, field) in cases.items():
            with self.subTest(case=label), tempfile.TemporaryDirectory() as raw:
                tmp = Path(raw)
                proc = run(tmp, {"version": 1, "builders": [builder, {"name": "ok", "command": "true"}]})
                out = proc.stdout + proc.stderr
                self.assertEqual(proc.returncode, 0, out)
                self.assertIn(f"Skipped: builders.0 (invalid {field}", proc.stdout)
                self.assertIn("ok: true (timeout 30 min)", proc.stdout)
                self.assertNotIn("PWNED", proc.stdout.replace("Skipped: builders.0", ""))
                self.assertEqual([b["name"] for b in written(tmp)["builders"]], ["ok"])
                self.assertFalse((tmp / "PWNED").exists())

    def test_a_duplicate_name_is_skipped(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            proc = run(tmp, {"version": 1, "builders": [{"name": "a", "command": "one"}, {"name": "a", "command": "two"}]})
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("Skipped: builders.1 (duplicate name a)", proc.stdout)
            self.assertEqual(written(tmp)["builders"], [{"name": "a", "command": "one", "timeout_minutes": 30}])


class Outcomes(unittest.TestCase):
    """R27: no usable builder exits 1 (the gated build falls back); a broken profile or call exits 2."""

    def test_no_usable_builder_exits_1(self):
        for label, profile in {"no builders key": {"version": 1}, "empty list": {"version": 1, "builders": []},
                               "only invalid": {"version": 1, "builders": [{"name": "a b", "command": "x"}]}}.items():
            with self.subTest(case=label), tempfile.TemporaryDirectory() as raw:
                tmp = Path(raw)
                proc = run(tmp, profile)
                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                self.assertEqual(written(tmp)["builders"], [])

    def test_a_broken_profile_or_call_exits_2(self):
        for label, profile in {"not json": "{", "not an object": "[]", "builders not a list": {"builders": {}}}.items():
            with self.subTest(case=label), tempfile.TemporaryDirectory() as raw:
                proc = run(Path(raw), profile)
                self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        with tempfile.TemporaryDirectory() as raw:
            proc = subprocess.run([sys.executable, str(CHECK)], cwd=raw, capture_output=True, text=True, timeout=30)
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
