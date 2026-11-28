#!/usr/bin/env python3
"""Guard the files that decide test isolation while outside builders work (R18).

    python3 scripts/suite_guard.py snapshot --root <project-root> --out <file>
    python3 scripts/suite_guard.py verify --root <project-root> --snapshot <file>
    python3 scripts/suite_guard.py wipers --root <project-root>

The gated build decides once whether the suite is isolated, and takes the snapshot
after the gate commit and before the first builder. These files decide isolation,
and a builder could change any of them to reach another database or get green:
phpunit.xml (often git-ignored, and it wins over phpunit.xml.dist), phpunit.xml.dist,
tests/Pest.php, tests/TestCase.php, .env (the dev database name), .env.testing,
testbench.yaml (its env can override the pins), config/database.php, and the
phpunit bootstrap file named by phpunit.xml, else phpunit.xml.dist, at snapshot
time. A bootstrap under vendor/ is not watched: Composer rewrites it on every
install, and a builder may add a package.

`snapshot` records whether each exists and a sha256 of its bytes; it reads the
files on disk, so git-ignored ones count too. `verify` compares them with the
snapshot and prints `changed: <path>` for each one created, changed or deleted.
`wipers` prints `<path>: <trait>` for each test file under tests/ that names a
database-wiping trait (RefreshDatabase, DatabaseMigrations, DatabaseTruncation,
LazilyRefreshDatabase), else `<path>: <command>` for one that calls a wiping artisan
command (migrate:fresh, migrate:refresh, migrate:reset, db:wipe) through
`artisan(...)` or `Artisan::call(...)`, a new file included: on a suite that is not
isolated such a test wipes the configured database. `migrate` and `migrate:status`
are not flagged.
The command check is a tripwire on the plain call forms; known false negatives: a
command reached through exec(), shell_exec() or Process (`php artisan migrate:fresh`),
a named or array argument (`Artisan::call(command: 'db:wipe')`, `['migrate:fresh']`),
a variable or concatenation, `$kernel->call(...)` and `Artisan::queue(...)`.

Exit 0: snapshot written, nothing changed, or no wiping trait or command. Exit 1: a file
changed, or a wiping trait or command found. Exit 2: usage error, a missing --root directory,
or an unreadable snapshot. Proved by tests/gate/test_suite_guard.py.
Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

WATCHED = ("phpunit.xml", "phpunit.xml.dist", "tests/Pest.php", "tests/TestCase.php", ".env", ".env.testing",
           "testbench.yaml", "config/database.php")
WIPERS = ("LazilyRefreshDatabase", "RefreshDatabase", "DatabaseMigrations", "DatabaseTruncation")
# An artisan call that wipes the database: `artisan(...)` (`$this->artisan(...)`) or `Artisan::call(...)` (or callSilently), either
# quote, the command first in the string, arguments after it allowed; `migrate` and `migrate:status` wipe nothing.
WIPING_CALL = re.compile(r"""(?:\bartisan|\bArtisan::call(?:Silently)?)\s*\(\s*(['"])\s*(migrate:fresh|migrate:refresh|migrate:reset|db:wipe)(?=[\s'"])""")
BOOTSTRAP = re.compile(r"""\bbootstrap\s*=\s*["']([^"']+)["']""")


class Usage(argparse.ArgumentParser):
    """An argument parser whose errors exit 2."""

    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"suite_guard.py: {message}", file=sys.stderr)
        sys.exit(2)


def digest(root: str, path: str):
    """sha256 of the file's bytes, or None when it does not exist."""
    full = os.path.join(root, path)
    if not os.path.isfile(full):
        return None
    with open(full, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def bootstrap(root: str):
    """The phpunit bootstrap file, relative to the root, from phpunit.xml else phpunit.xml.dist; None when there
    is none, it is absolute or outside the root, or it is under vendor/ (test_suite_guard: Guard)."""
    for name in ("phpunit.xml", "phpunit.xml.dist"):
        full = os.path.join(root, name)
        if not os.path.isfile(full):
            continue
        with open(full, encoding="utf-8", errors="replace") as fh:
            m = BOOTSTRAP.search(fh.read())
        if not m:
            return None
        path = os.path.normpath(m.group(1))
        if os.path.isabs(path) or path.startswith("..") or path.split(os.sep)[0] == "vendor":
            return None
        return path.replace(os.sep, "/")
    return None


def state(root: str, paths) -> dict:
    """Path -> sha256, or None when it does not exist."""
    return {path: digest(root, path) for path in paths}


def wipers(root: str) -> list:
    """`<path>: <trait>` for each PHP file under tests/ naming a wiping trait, else `<path>: <command>` for one
    calling a wiping artisan command, in path order (test_suite_guard, test_wiping_commands)."""
    hits = []
    tests = os.path.join(root, "tests")
    for directory, _dirs, names in sorted(os.walk(tests)):
        for name in sorted(names):
            if not name.endswith(".php"):
                continue
            full = os.path.join(directory, name)
            with open(full, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            found = next((t for t in WIPERS if re.search(rf"\b{t}\b", text)), None)
            if not found:
                call = WIPING_CALL.search(text)
                found = call.group(2) if call else None
            if found:
                hits.append(f"{os.path.relpath(full, root).replace(os.sep, '/')}: {found}")
    return hits


def main() -> int:
    ap = Usage(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="action", required=True, parser_class=Usage)
    snap = sub.add_parser("snapshot")
    snap.add_argument("--root", required=True)
    snap.add_argument("--out", required=True)
    ver = sub.add_parser("verify")
    ver.add_argument("--root", required=True)
    ver.add_argument("--snapshot", required=True)
    wip = sub.add_parser("wipers")
    wip.add_argument("--root", required=True)
    args = ap.parse_args()
    if not os.path.isdir(args.root):
        ap.error(f"--root {args.root} is not a directory")

    if args.action == "wipers":
        hits = wipers(args.root)
        for hit in hits:
            print(hit)
        return 1 if hits else 0

    if args.action == "snapshot":
        paths = list(WATCHED)
        extra = bootstrap(args.root)
        if extra and extra not in paths:
            paths.append(extra)
        try:
            with open(args.out, "w", encoding="utf-8") as fh:
                json.dump(state(args.root, paths), fh, indent=2)
        except OSError as err:
            ap.error(f"cannot write {args.out}: {err}")
        return 0

    try:
        with open(args.snapshot, encoding="utf-8") as fh:
            before = json.load(fh)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        ap.error(f"cannot read {args.snapshot}: {err}")
    paths = list(dict.fromkeys([*WATCHED, *before]))
    now = state(args.root, paths)
    changed = [path for path in paths if before.get(path) != now[path]]
    for path in changed:
        print(f"changed: {path}")
    return 1 if changed else 0


if __name__ == "__main__":
    sys.exit(main())
