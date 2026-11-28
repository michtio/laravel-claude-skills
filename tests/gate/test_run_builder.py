"""The builder runner: one outside builder per docs/outside-builders.md, with its timeout.

Requirements R18 (the outside builder gets the brief file) and R27 (a builder that fails, times out or is
unavailable hands over to the next: the runner reports which). Builder-added test (G3), beside the S10 gate.
It also proves the docstring's claims: a signal to the runner kills the builder's tree and exits 128 + n,
children a leader leaves behind are killed, --log takes the output, and an unwritable --log is a usage error;
and the --builders mode, which takes the command from the file scripts/builders_check.py wrote, so no profile
value is ever quoted into a shell line by the caller.
Standard library only.

    python3 -m unittest discover -s tests/gate -p 'test_run_builder.py'
"""
from __future__ import annotations

import json
import os
import signal
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


def wait_gone(pid: int, tries: int = 50) -> bool:
    for _ in range(tries):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.1)
    return False


def kill_quietly(pid):
    if pid:
        try:
            os.kill(pid, 9)
        except OSError:
            pass


def term_ignoring_child(tmp: Path, pidfile: Path, then: str) -> str:
    return ("sh -c \"trap '' TERM; exec sleep 300\" >/dev/null 2>&1 </dev/null &\n"
            f"echo $! > {pidfile}\n" + then)


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


class SignalsAndLeftovers(unittest.TestCase):
    """R27: nothing a builder started outlives the runner, whatever ends it."""

    def test_a_signal_to_the_runner_kills_the_builders_tree_and_exits_128_plus_n(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            pidfile = tmp / "child.pid"
            builder = script(tmp, "builder", term_ignoring_child(tmp, pidfile, "sleep 300\n"))
            runner = subprocess.Popen(
                [sys.executable, str(RUNNER), "--cwd", str(tmp), "--timeout-minutes", "5", "--command", str(builder),
                 "brief.md", "handback.md"], cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            pid = None
            try:
                for _ in range(100):
                    if pidfile.is_file() and pidfile.read_text().strip():
                        break
                    time.sleep(0.1)
                pid = int(pidfile.read_text().strip())
                runner.send_signal(signal.SIGTERM)
                out, _ = runner.communicate(timeout=60)
                self.assertEqual(runner.returncode, 128 + signal.SIGTERM, out)
                self.assertIn("builder exit: interrupted", out)
                self.assertTrue(wait_gone(pid), f"child {pid} survived a SIGTERM to the runner")
            finally:
                if runner.poll() is None:
                    runner.kill()
                kill_quietly(pid)

    def test_children_left_by_a_leader_that_exits_0_are_killed(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            pidfile = tmp / "child.pid"
            builder = script(tmp, "builder", term_ignoring_child(tmp, pidfile, "exit 0\n"))
            pid = None
            try:
                proc = run(tmp, str(builder))
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                pid = int(pidfile.read_text().strip())
                self.assertTrue(wait_gone(pid), f"child {pid} outlived its leader and the runner")
            finally:
                kill_quietly(pid)


class Log(unittest.TestCase):
    """--log takes the builder's stdout and stderr; one that cannot be opened is a usage error."""

    def test_the_log_takes_the_builders_output(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            builder = script(tmp, "builder", "echo to-stdout; echo to-stderr >&2\n")
            proc = run(tmp, str(builder), "1", "--log", str(tmp / "log.txt"))
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            log = (tmp / "log.txt").read_text(encoding="utf-8")
            self.assertIn("to-stdout", log)
            self.assertIn("to-stderr", log)
            self.assertNotIn("to-stdout", proc.stdout + proc.stderr)

    def test_an_unwritable_log_exits_64(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            proc = run(tmp, "true", "1", "--log", str(tmp / "no-such-dir" / "log.txt"))
            self.assertEqual(proc.returncode, 64, proc.stdout + proc.stderr)


class BuildersFile(unittest.TestCase):
    """R18: with --builders the runner takes the command, the timeout and the project root from the file
    scripts/builders_check.py wrote, so a quote in a profile command never reaches a shell line."""

    def write(self, tmp: Path, builders: list) -> Path:
        path = tmp / "builders.json"
        path.write_text(json.dumps({"project_root": str(tmp / "project"), "builders": builders}), encoding="utf-8")
        (tmp / "project").mkdir(exist_ok=True)
        return path

    def run_named(self, tmp: Path, file: Path, name: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(RUNNER), "--builders", str(file), "--name", name,
                               str(tmp / "brief.md"), str(tmp / "handback.md")],
                              cwd=tmp, capture_output=True, text=True, timeout=90)

    def test_a_command_with_quotes_runs_as_written_from_the_project_root(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw).resolve()
            command = "sh -c 'pwd > \"$1\"; echo \"it'\\''s $0\" >> \"$1\"'"
            file = self.write(tmp, [{"name": "quoted", "command": command, "timeout_minutes": 1}])
            proc = self.run_named(tmp, file, "quoted")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            lines = (tmp / "handback.md").read_text(encoding="utf-8").splitlines()
            self.assertEqual(Path(lines[0]).resolve(), tmp / "project")
            self.assertEqual(lines[1], f"it's {tmp / 'brief.md'}")

    def test_the_timeout_comes_from_the_file(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            file = self.write(tmp, [{"name": "slow", "command": "sh -c 'sleep 300'", "timeout_minutes": 0.0333}])
            proc = self.run_named(tmp, file, "slow")
            self.assertEqual(proc.returncode, 124, proc.stdout + proc.stderr)

    def test_an_unknown_or_unsafe_name_is_a_usage_error(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            file = self.write(tmp, [{"name": "ok", "command": "true", "timeout_minutes": 1},
                                    {"name": "x$(touch PWNED)", "command": "true", "timeout_minutes": 1}])
            for name in ("missing", "x$(touch PWNED)"):
                with self.subTest(name=name):
                    proc = self.run_named(tmp, file, name)
                    self.assertEqual(proc.returncode, 64, proc.stdout + proc.stderr)
            self.assertFalse((tmp / "PWNED").exists())

    def test_builders_and_command_are_exclusive(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            file = self.write(tmp, [{"name": "ok", "command": "true", "timeout_minutes": 1}])
            proc = subprocess.run([sys.executable, str(RUNNER), "--builders", str(file), "--name", "ok",
                                   "--command", "true", "brief.md", "handback.md"],
                                  cwd=tmp, capture_output=True, text=True, timeout=30)
            self.assertEqual(proc.returncode, 64, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
