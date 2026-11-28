#!/usr/bin/env python3
"""Check the profile's outside builders before a gated build asks to run them (R18, R27).

    python3 scripts/builders_check.py --profile <skills-profile.json> --root <project-root> --out <file>

The profile is a file in the repository, so nothing in it reaches a shell line
unchecked. A builder is usable when:

    name             matches ^[A-Za-z0-9._-]{1,64}$ and no earlier builder has it
    command          a non-empty string with no Unicode control, format, surrogate,
                     private-use or unassigned character (category C*) and no line or
                     paragraph separator (Zl, Zp): one printable line that shows what
                     it runs, with no right-to-left override or zero-width character
    timeout_minutes  absent (30) or a JSON number above 0 (a boolean or string is refused)

Prints one line per builder, in profile order: `<name>: <command> (timeout <n> min)`
for a usable one (the list the user says yes to), `Skipped: builders.<i> (invalid
<field>: <reason>)` or `Skipped: builders.<i> (duplicate name <name>)` for the rest.
An unusable builder is named by its position, never by its name, so a hostile name
is never printed or run. Writes the usable builders and the absolute project root
to --out as JSON, which scripts/run_builder.py --builders reads, so the caller
passes only a checked name and paths it made itself.

Exit 0: at least one usable builder. Exit 1: none (no `builders`, an empty list, or
only unusable ones; --out still lists none). Exit 2: usage error, an unreadable or
invalid JSON profile, a profile that is not an object, or `builders` not a list.
Proved by tests/gate/test_builders_check.py. Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata

NAME = re.compile(r"[A-Za-z0-9._-]{1,64}")
DEFAULT_TIMEOUT = 30


class Usage(argparse.ArgumentParser):
    """An argument parser whose errors exit 2."""

    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"builders_check.py: {message}", file=sys.stderr)
        sys.exit(2)


def hidden(text: str) -> bool:
    """Whether the text holds a character that can hide or reorder what the consent line shows: any Unicode
    control, format, surrogate, private-use or unassigned character (category C*), such as U+202E or U+200B,
    or a line or paragraph separator (Zl, Zp). Proved by test_builders_check: UnsafeBuilders."""
    return any(unicodedata.category(ch)[0] == "C" or unicodedata.category(ch) in ("Zl", "Zp") for ch in text)


def problem(builder) -> str | None:
    """Why a builder is unusable, as `invalid <field>: <reason>`, or None when it is usable."""
    if not isinstance(builder, dict):
        return "invalid object: each builder must be an object"
    name = builder.get("name")
    if not isinstance(name, str) or not NAME.fullmatch(name):
        return "invalid name: must match ^[A-Za-z0-9._-]{1,64}$"
    command = builder.get("command")
    if not isinstance(command, str) or not command.strip() or hidden(command):
        return "invalid command: must be a non-empty string with no control, format or separator characters"
    if "timeout_minutes" in builder:
        minutes = builder["timeout_minutes"]
        if isinstance(minutes, bool) or not isinstance(minutes, (int, float)) or not minutes > 0:
            return "invalid timeout_minutes: must be a number above 0"
    return None


def minutes_text(value) -> str:
    """30 for 30 or 30.0, 2.5 for 2.5."""
    return str(int(value)) if float(value).is_integer() else str(value)


def main() -> int:
    ap = Usage(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", required=True)
    ap.add_argument("--root", required=True, help="the project root")
    ap.add_argument("--out", required=True, help="where to write the usable builders")
    args = ap.parse_args()
    try:
        with open(args.profile, encoding="utf-8") as fh:
            profile = json.load(fh)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        print(f"cannot read {args.profile}: {err}", file=sys.stderr)
        return 2
    if not isinstance(profile, dict):
        print(f"{args.profile}: the profile must be a JSON object", file=sys.stderr)
        return 2
    builders = profile.get("builders", [])
    if not isinstance(builders, list):
        print(f"{args.profile}: builders must be a list", file=sys.stderr)
        return 2

    usable, seen = [], set()
    for index, builder in enumerate(builders):
        reason = problem(builder)
        if reason is None and builder["name"] in seen:
            reason = f"duplicate name {builder['name']}"
        if reason is not None:
            print(f"Skipped: builders.{index} ({reason})")
            continue
        seen.add(builder["name"])
        minutes = builder.get("timeout_minutes", DEFAULT_TIMEOUT)
        usable.append({"name": builder["name"], "command": builder["command"], "timeout_minutes": minutes})
        print(f"{builder['name']}: {builder['command']} (timeout {minutes_text(minutes)} min)")

    try:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump({"project_root": os.path.abspath(args.root), "builders": usable}, fh, indent=2)
    except OSError as err:
        print(f"cannot write {args.out}: {err}", file=sys.stderr)
        return 2
    return 0 if usable else 1


if __name__ == "__main__":
    sys.exit(main())
