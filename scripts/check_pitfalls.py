#!/usr/bin/env python3
"""Check that every laravel-pitfalls reference names the gap it fills in Boost (R1).

    python3 scripts/check_pitfalls.py [--root DIR]

Scans DIR/resources/boost/skills/laravel-pitfalls/references/*.md (DIR defaults to
the repo root). Each reference must carry one line, at column 0, reading either

    Gap: not covered by Boost
    Gap: covered partly by Boost (<the Boost rule it extends>)

A reference with no `Gap:` line fails with `<file>: no gap line`. A `covered partly`
line without a non-empty parenthesised Boost rule fails with `<file>: names no Boost
rule`. Anything Boost covers fully does not ship, so there is no third form.

Exit 0 when every reference passes (or there are none), 1 on a failure, 2 on usage.
Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REFERENCES = Path("resources/boost/skills/laravel-pitfalls/references")
GAP_ANY = re.compile(r"^Gap:", re.MULTILINE)
GAP_VALID = re.compile(r"^Gap: (not covered by Boost|covered partly by Boost \(\S.*\))\s*$", re.MULTILINE)
GAP_PARTLY = re.compile(r"^Gap: covered partly by Boost\b", re.MULTILINE)


def check_file(path: Path) -> str | None:
    """Return the failure message for one reference, or None when it passes."""
    text = path.read_text(encoding="utf-8")
    if GAP_VALID.search(text):
        return None
    if GAP_PARTLY.search(text):
        return f"{path}: names no Boost rule"
    if GAP_ANY.search(text):
        return f"{path}: no gap line (a Gap: line must read 'not covered by Boost' or 'covered partly by Boost (<rule>)')"
    return f"{path}: no gap line"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=str(REPO), help="tree to check (default: the repo root)")
    args = parser.parse_args(argv)

    refs_dir = Path(args.root) / REFERENCES
    files = sorted(refs_dir.glob("*.md")) if refs_dir.is_dir() else []
    if not files:
        print(f"no pitfall references under {refs_dir}: nothing to check")
        return 0

    failures = [msg for msg in (check_file(f) for f in files) if msg]
    for f in files:
        if not any(msg.startswith(f"{f}:") for msg in failures):
            print(f"ok    {f}")
    for msg in failures:
        print(f"FAIL  {msg}")
    print(f"{len(files) - len(failures)}/{len(files)} pitfall references name their Boost gap")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
