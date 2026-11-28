#!/usr/bin/env python3
"""Run one outside builder per docs/outside-builders.md, with its timeout (R18, R27).

    python3 scripts/run_builder.py --builders <file> --name <name> [--log <file>] <brief-file> <handback-file>
    python3 scripts/run_builder.py --cwd <project-root> --timeout-minutes <n> \
        --command '<command>' [--log <file>] <brief-file> <handback-file>

With --builders, the project root, the timeout and the command come from the file
scripts/builders_check.py wrote, and --name must match ^[A-Za-z0-9._-]{1,64}$: the
gated build uses this form, so no value from the profile is quoted into its shell
line. The second form is for a team tool that already holds the values.

Runs `<command> <brief-file> <handback-file>` through sh, from the project root,
in its own process group. The brief and hand-back paths are made absolute first.
The builder's stdout and stderr go to --log when given, otherwise to this
script's own output.

When the builder has not exited within the timeout, the whole process group is
killed: SIGTERM, up to 10 seconds of polling, then SIGKILL to the group even when
the leader has already exited, so a child that ignores SIGTERM dies too. When this
script itself gets SIGTERM, SIGINT or SIGHUP, it kills the group the same way and
exits 128 + the signal number.

Prints one last line, `builder exit: <n>` or `builder exit: timeout`. Exit codes:
    the builder's own exit code (128 + n when a signal killed it)
    124  timeout (failed, per the protocol)
    64   usage error in this script (bad arguments, both forms or neither, a name
         not in --builders, missing --cwd directory, unwritable --log); never a
         builder result
Proved by tests/gate/test_run_builder.py.

Ported from craftcms-claude-skills (bin/run_builder.py), so one team tool serves
both packs. Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time

USAGE_ERROR = 64
TIMEOUT = 124
NAME = re.compile(r"[A-Za-z0-9._-]{1,64}")


class Usage(argparse.ArgumentParser):
    """An argument parser whose errors exit 64, so a bad call never reads as a builder's exit."""

    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"run_builder.py: {message}", file=sys.stderr)
        sys.exit(USAGE_ERROR)


def from_builders(ap: Usage, path: str, name: str) -> tuple:
    """The project root, timeout and command of one checked builder (test_run_builder: BuildersFile).

    The caller passes only a name that matches the builders check's pattern and paths it made itself, so no
    profile value is quoted into a shell line; a name that is unsafe or not in the file is a usage error.
    """
    if not NAME.fullmatch(name):
        ap.error(f"--name must match {NAME.pattern}")
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        builder = next(b for b in data["builders"] if b["name"] == name)
        return data["project_root"], float(builder["timeout_minutes"]), builder["command"]
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as err:
        ap.error(f"no builder {name} in {path} ({type(err).__name__})")


def group_alive(pgid: int) -> bool:
    """Whether any process of the group is still alive."""
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def kill_group(pgid: int, proc: subprocess.Popen) -> None:
    """TERM the group, poll up to 10 seconds, then always KILL the group (test_run_builder: Timeout)."""
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        proc.poll()
        if not group_alive(pgid):
            break
        time.sleep(0.1)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass


def main() -> int:
    ap = Usage(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cwd", help="the project root")
    ap.add_argument("--timeout-minutes", type=float)
    ap.add_argument("--command", help="the builder's command")
    ap.add_argument("--builders", help="the file scripts/builders_check.py wrote")
    ap.add_argument("--name", help="the builder to run from --builders")
    ap.add_argument("--log", help="file for the builder's stdout and stderr")
    ap.add_argument("brief")
    ap.add_argument("handback")
    args = ap.parse_args()
    direct = (args.cwd, args.timeout_minutes, args.command)
    if args.builders is not None or args.name is not None:
        if any(v is not None for v in direct) or args.builders is None or args.name is None:
            ap.error("use --builders with --name, or --cwd, --timeout-minutes and --command, not both")
        args.cwd, args.timeout_minutes, args.command = from_builders(ap, args.builders, args.name)
    elif any(v is None for v in direct):
        ap.error("--cwd, --timeout-minutes and --command are required without --builders")
    if not args.timeout_minutes > 0 or not os.path.isdir(args.cwd):
        ap.error("--timeout-minutes must be above 0 and --cwd a directory")
    brief, handback = os.path.abspath(args.brief), os.path.abspath(args.handback)
    out = None
    if args.log:
        try:
            out = open(os.path.abspath(args.log), "ab")
        except OSError as err:
            ap.error(f"cannot open --log: {err}")

    cmd = ["sh", "-c", args.command + ' "$1" "$2"', "sh", brief, handback]
    proc = subprocess.Popen(cmd, cwd=args.cwd, start_new_session=True, stdin=subprocess.DEVNULL,
                            stdout=out, stderr=subprocess.STDOUT if out else None)
    pgid = proc.pid  # start_new_session: the leader's pid is the group id

    def on_signal(signum, _frame):
        kill_group(pgid, proc)
        print(f"builder exit: interrupted (signal {signum})", flush=True)
        sys.exit(128 + signum)

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(sig, on_signal)

    try:
        code = proc.wait(timeout=args.timeout_minutes * 60)
    except subprocess.TimeoutExpired:
        kill_group(pgid, proc)
        print("builder exit: timeout", flush=True)
        return TIMEOUT
    if group_alive(pgid):
        # The leader exited but left children behind in its group: clean them up.
        kill_group(pgid, proc)
    if code < 0:  # killed by a signal
        code = 128 - code
    print(f"builder exit: {code}", flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
