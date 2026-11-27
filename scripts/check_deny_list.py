#!/usr/bin/env python3
"""Fail when a published file names anything on the internal deny list (R2, AC3).

    python3 scripts/check_deny_list.py [--root DIR] [--list FILE]

The deny list (default DIR/internal-docs/deny-list.txt) holds client, app, company,
person and domain names the public package must never carry: one term per line,
blank lines and lines starting with # ignored. Matching is a case-insensitive
substring search, so a name embedded in an identifier (FooServiceProvider) is
caught too; keep the terms distinctive.

Files checked: `git ls-files` when DIR is a git work tree (exactly what gets
published), otherwise every file under DIR. The deny list itself is never checked.

The list lives in git-ignored internal-docs/, so public clones and CI have none:
then the check prints that it was skipped and exits 0. Exit 1 on a hit, printing
`<file>:<line>: names a deny-listed term`, without echoing the term (the output
may land in a public CI log). Exit 2 on usage errors.
Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_LIST = Path("internal-docs/deny-list.txt")


def load_terms(path: Path) -> list[str]:
    """Read the deny list: one lower-cased term per non-blank, non-comment line."""
    terms = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            terms.append(line.lower())
    return terms


def published_files(root: Path) -> list[Path]:
    """List the files to check: git-tracked files in a work tree, else every file."""
    try:
        out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, check=True)
        top = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, check=True).stdout.strip()
        if Path(top).resolve() == root.resolve():
            return [root / name for name in out.stdout.decode("utf-8").split("\0") if name]
    except (OSError, subprocess.CalledProcessError):
        pass
    return [p for p in root.rglob("*") if p.is_file() and ".git" not in p.relative_to(root).parts]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=str(REPO), help="tree to check (default: the repo root)")
    parser.add_argument("--list", help="deny list file (default: ROOT/internal-docs/deny-list.txt)")
    args = parser.parse_args(argv)

    root = Path(args.root)
    deny = Path(args.list) if args.list else root / DEFAULT_LIST
    if not deny.is_file():
        print(f"skipped: no deny list at {deny} (public clone or CI)")
        return 0
    terms = load_terms(deny)
    if not terms:
        print(f"skipped: deny list {deny} is empty")
        return 0

    hits = 0
    checked = 0
    for path in published_files(root):
        if not path.is_file() or path.resolve() == deny.resolve():
            continue
        checked += 1
        try:
            text = path.read_text(encoding="utf-8", errors="replace").lower()
        except OSError:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if any(term in line for term in terms):
                print(f"{path.relative_to(root)}:{number}: names a deny-listed term")
                hits += 1
    print(f"{checked} files checked against {len(terms)} deny-listed terms, {hits} hits")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
