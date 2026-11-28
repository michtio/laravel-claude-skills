#!/usr/bin/env python3
"""Guard the files that decide test isolation while outside builders work (R18).

    python3 scripts/suite_guard.py snapshot --root <project-root> --out <file>
    python3 scripts/suite_guard.py verify --root <project-root> --snapshot <file>

The gated build decides once, before the first builder, whether the suite is
isolated. These files decide it, and a builder could change any of them to reach
another database or get green: phpunit.xml (often git-ignored, and it wins over
phpunit.xml.dist), phpunit.xml.dist, tests/Pest.php, tests/TestCase.php, .env (the
dev database name) and .env.testing. `snapshot` records whether each exists and a
sha256 of its bytes; it reads the files on disk, so git-ignored ones count too.
`verify` compares them with the snapshot and prints `changed: <path>` for each one
created, changed or deleted.

Exit 0: snapshot written, or nothing changed. Exit 1: a file changed (the builder is
disqualified and the gate is not rerun). Exit 2: usage error, a missing --root
directory, or an unreadable snapshot. Proved by tests/gate/test_suite_guard.py.
Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

WATCHED = ("phpunit.xml", "phpunit.xml.dist", "tests/Pest.php", "tests/TestCase.php", ".env", ".env.testing")


class Usage(argparse.ArgumentParser):
    """An argument parser whose errors exit 2."""

    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"suite_guard.py: {message}", file=sys.stderr)
        sys.exit(2)


def state(root: str) -> dict:
    """Path -> sha256 of its bytes, or None when it does not exist."""
    out = {}
    for path in WATCHED:
        full = os.path.join(root, path)
        if os.path.isfile(full):
            with open(full, "rb") as fh:
                out[path] = hashlib.sha256(fh.read()).hexdigest()
        else:
            out[path] = None
    return out


def main() -> int:
    ap = Usage(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="action", required=True, parser_class=Usage)
    snap = sub.add_parser("snapshot")
    snap.add_argument("--root", required=True)
    snap.add_argument("--out", required=True)
    ver = sub.add_parser("verify")
    ver.add_argument("--root", required=True)
    ver.add_argument("--snapshot", required=True)
    args = ap.parse_args()
    if not os.path.isdir(args.root):
        ap.error(f"--root {args.root} is not a directory")

    if args.action == "snapshot":
        try:
            with open(args.out, "w", encoding="utf-8") as fh:
                json.dump(state(args.root), fh, indent=2)
        except OSError as err:
            ap.error(f"cannot write {args.out}: {err}")
        return 0

    try:
        with open(args.snapshot, encoding="utf-8") as fh:
            before = json.load(fh)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        ap.error(f"cannot read {args.snapshot}: {err}")
    now = state(args.root)
    changed = [path for path in WATCHED if before.get(path) != now[path]]
    for path in changed:
        print(f"changed: {path}")
    return 1 if changed else 0


if __name__ == "__main__":
    sys.exit(main())
