"""The builder runner: one outside builder per docs/outside-builders.md, with its timeout.

Requirements R18 (the outside builder gets the brief file) and R27 (a builder that fails, times out or is
unavailable hands over to the next: the runner reports which). Builder-added test (G3), beside the S10 gate.
Standard library only.

    python3 -m unittest discover -s tests/gate -p 'test_run_builder.py'
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUNNER = REPO / "scripts/run_builder.py"


def run(tmp: Path, command: str, minutes: str = "1", *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(RUNNER), "--cwd", str(tmp), "--timeout-minutes", minutes, "--command", command,
         *extra, "brief.md", "handback.md"],
        cwd=tmp, capture_output=True, text=True, timeout=90)


def script(tmp: Path, name: str, body: str) -> Path:
    path = tmp / name
    path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    path.chmod(0o755)
    return path


class CallForm(unittest.TestCase):
    """R18: the command gets the brief and the hand-back path, absolute, and runs from the project root."""

    def test_the_builder_gets_both_paths_and_runs_from_the_project_root(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw).resolve()
            project = tmp / "project"
            project.mkdir()
            builder = script(tmp, "builder", 'pwd > "$2"; echo "$1" >> "$2"\n')
            proc = subprocess.run(
                [sys.executable, str(RUNNER), "--cwd", str(project), "--timeout-minutes", "1",
                 "--command", str(builder), "brief.md", "handback.md"],
                cwd=tmp, capture_output=True, text=True, timeout=90)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("builder exit: 0", proc.stdout)
            lines = (tmp / "handback.md").read_text(encoding="utf-8").splitlines()
            self.assertEqual(Path(lines[0]).resolve(), project)
            self.assertEqual(lines[1], str(tmp / "brief.md"))


class ExitCodes(unittest.TestCase):
    """R27: the builder's own exit code comes back, so exit 3 (unavailable) and others (failed) stay apart."""

    def test_the_builders_exit_code_is_passed_through(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            for code in (0, 1, 3, 7):
                with self.subTest(code=code):
                    proc = run(tmp, f"sh -c 'exit {code}' builder")
                    self.assertEqual(proc.returncode, code, proc.stdout + proc.stderr)
                    self.assertIn(f"builder exit: {code}", proc.stdout)

    def test_a_bad_call_is_a_usage_error_never_a_builder_result(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            for label, minutes, cwd in (("zero timeout", "0", str(tmp)), ("missing cwd", "1", str(tmp / "nope"))):
                with self.subTest(case=label):
                    proc = subprocess.run(
                        [sys.executable, str(RUNNER), "--cwd", cwd, "--timeout-minutes", minutes,
                         "--command", "true", "brief.md", "handback.md"],
                        cwd=tmp, capture_output=True, text=True, timeout=30)
                    self.assertEqual(proc.returncode, 64, proc.stdout + proc.stderr)


class Timeout(unittest.TestCase):
    """R27: a builder that outlives timeout_minutes counts as failed, and nothing it started survives."""

    def test_a_timeout_exits_124_and_kills_a_child_that_ignores_term(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            pidfile = tmp / "child.pid"
            builder = script(tmp, "builder",
                             "sh -c \"trap '' TERM; exec sleep 300\" >/dev/null 2>&1 </dev/null &\n"
                             f"echo $! > {pidfile}\n"
                             "sleep 300\n")
            pid = None
            try:
                proc = run(tmp, str(builder), "0.0333")
                self.assertEqual(proc.returncode, 124, proc.stdout + proc.stderr)
                self.assertIn("builder exit: timeout", proc.stdout)
                self.assertTrue(pidfile.is_file(), "the builder never started its child")
                pid = int(pidfile.read_text().strip())
                gone = False
                for _ in range(30):
                    try:
                        os.kill(pid, 0)
                    except ProcessLookupError:
                        gone = True
                        break
                    time.sleep(0.1)
                self.assertTrue(gone, f"child {pid} (ignores SIGTERM) survived the runner")
            finally:
                if pid:
                    try:
                        os.kill(pid, 9)
                    except OSError:
                        pass


if __name__ == "__main__":
    unittest.main()
