#!/usr/bin/env python3
"""Keep the outside-builder commands a user confirmed, once per machine (R18, R27).

    python3 scripts/builder_trust.py check  --builders <file> --out <file> [--unattended]
    python3 scripts/builder_trust.py add    --builders <file> --name <name>
    python3 scripts/builder_trust.py list   --root <project-root>
    python3 scripts/builder_trust.py remove --root <project-root> --name <name>

--builders is the file scripts/builders_check.py wrote. A trusted entry is keyed on
the repository (the real path of the git top-level of the project root plus its
remote.origin.url, empty when there is none) and the builder's exact name, command
and timeout_minutes: another clone, a changed origin, or a builder changed by one
character asks again.

The trust file lives outside every repository:
    $LARAVEL_CLAUDE_SKILLS_TRUST_FILE when set, else
    $XDG_CONFIG_HOME/laravel-claude-skills/trusted-builders.json when that is set, else
    ~/.config/laravel-claude-skills/trusted-builders.json
`add` creates it with mode 0600. Nothing in it is trusted when its real path is
inside the project (so a cloned repo cannot approve itself), when its group or other
write bit is set, when another user owns it, or when it is not valid; the reason and
the path go to stderr, and a corrupt file is never overwritten.

check   prints one line per builder of --builders, in order:
        `<name>: <command> (timeout <n> min) (trusted)` for a trusted one, and for
        the rest `<name>: <command> (timeout <n> min)`, or with --unattended
        `Skipped: <name> (not confirmed)`. Writes --out in the --builders format with
        the trusted builders only, so scripts/run_builder.py --builders can run
        nothing else from it. Exit 0; 2 for a usage error, an unreadable --builders
        file or an unwritable --out.
add     records the builder of --builders with that name (never a command from the
        arguments) and prints `Trusted: <name>`; adding it again keeps one entry, and
        an older entry of the same repository and name is replaced. Exit 0; 2, trust
        file untouched, for a name not in --builders or a trust file that is ignored.
list    prints `<name>: <command> (timeout <n> min)` per entry of this repository.
remove  deletes this repository's entries with that name and prints `Removed: <name>`;
        exit 1 when there is none, 2 when the trust file is ignored. Entries of other
        repositories stay.

git runs with argument lists, never through a shell. Proved by
tests/gate/test_builder_trust.py. Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
import tempfile

from builders_check import NAME, minutes_text, problem

TRUST_ENV = "LARAVEL_CLAUDE_SKILLS_TRUST_FILE"
TRUST_NAME = os.path.join("laravel-claude-skills", "trusted-builders.json")
VERSION = 1


class Usage(argparse.ArgumentParser):
    """An argument parser whose errors exit 2."""

    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"builder_trust.py: {message}", file=sys.stderr)
        sys.exit(2)


class Refused(Exception):
    """A trust file that must not be read or written; the message names it and why."""


# Repository identity
# =========================================================================


def git(root: str, *args: str) -> subprocess.CompletedProcess:
    """git in the project root with every inherited GIT_* variable dropped (GIT_DIR, GIT_CONFIG_COUNT and
    GIT_CONFIG_KEY_<n> could point it elsewhere or override remote.origin.url) and no system config, so the
    identity is the root's own (test_builder_trust_rules: Identity)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    return subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, env=env)


def identity(root: str) -> tuple:
    """(real path of the git top-level, origin URL); the root's real path when it is not in a git repository."""
    top = git(root, "rev-parse", "--show-toplevel")
    path = top.stdout.strip() if top.returncode == 0 and top.stdout.strip() else root
    origin = git(root, "config", "--get", "remote.origin.url")
    return os.path.realpath(path), origin.stdout.strip() if origin.returncode == 0 else ""


def inside(path: str, folder: str) -> bool:
    """Whether the real path of path is folder or under it. Compared by file identity as well as by string, so
    a differently cased spelling on a case-insensitive volume is still inside (test_builder_trust_rules)."""
    real, base = os.path.realpath(path), os.path.realpath(folder)
    if os.path.commonpath([real, base]) == base:
        return True
    current = real
    while True:
        if os.path.exists(current) and os.path.exists(base) and os.path.samefile(current, base):
            return True
        parent = os.path.dirname(current)
        if parent == current:
            return False
        current = parent


# Trust file
# =========================================================================


def trust_path() -> str:
    """The trust file: the override variable, else under XDG_CONFIG_HOME, else under ~/.config."""
    if os.environ.get(TRUST_ENV):
        return os.environ[TRUST_ENV]
    if os.environ.get("XDG_CONFIG_HOME"):
        return os.path.join(os.environ["XDG_CONFIG_HOME"], TRUST_NAME)
    return os.path.join(os.path.expanduser("~"), ".config", TRUST_NAME)


def valid_entry(entry) -> bool:
    """An entry is an object of strings plus a number timeout."""
    if not isinstance(entry, dict):
        return False
    if not all(isinstance(entry.get(key), str) for key in ("repository", "origin", "name", "command")):
        return False
    minutes = entry.get("timeout_minutes")
    return not isinstance(minutes, bool) and isinstance(minutes, (int, float))


def load(path: str, folders: tuple) -> list:
    """The entries of the trust file; [] when it does not exist. Raises Refused for a file inside one of the
    project folders, one others can write or another user owns, or a corrupt one."""
    for folder in folders:
        if inside(path, folder):
            raise Refused(f"ignored {path}: a trust file inside the project is never read")
    try:
        info = os.stat(path)
    except FileNotFoundError:
        return []
    except OSError as err:
        raise Refused(f"ignored {path}: {err}")
    if info.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise Refused(f"ignored {path}: group or other can write it (chmod 600 it)")
    if hasattr(os, "getuid") and info.st_uid != os.getuid():
        raise Refused(f"ignored {path}: another user owns it")
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        raise Refused(f"ignored {path}: not a valid trust file ({err}); fix or delete it")
    entries = data.get("entries") if isinstance(data, dict) and data.get("version") == VERSION else None
    if not isinstance(entries, list) or not all(valid_entry(e) for e in entries):
        raise Refused(f"ignored {path}: not a valid trust file; fix or delete it")
    return entries


def save(path: str, entries: list) -> None:
    """Write the trust file with mode 0600, atomically, through any symlink to its real path."""
    real = os.path.realpath(path)
    folder = os.path.dirname(real)
    os.makedirs(folder, mode=0o700, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".trusted-builders.", dir=folder)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"version": VERSION, "entries": entries}, fh, indent=2)
            fh.write("\n")
        os.replace(tmp, real)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def same_minutes(a, b) -> bool:
    return float(a) == float(b)


def matches(entry: dict, repo: tuple, builder: dict) -> bool:
    """Whether the entry trusts this exact builder in this repository."""
    return ((entry["repository"], entry["origin"]) == repo and entry["name"] == builder["name"]
            and entry["command"] == builder["command"]
            and same_minutes(entry["timeout_minutes"], builder["timeout_minutes"]))


def line(builder: dict) -> str:
    return f"{builder['name']}: {builder['command']} (timeout {minutes_text(builder['timeout_minutes'])} min)"


# Inputs
# =========================================================================


def read_builders(path: str) -> dict:
    """The --builders file, each builder checked again by builders_check.problem; exits 2 when it is not one."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
        print(f"cannot read {path}: {err}", file=sys.stderr)
        sys.exit(2)
    builders = data.get("builders") if isinstance(data, dict) else None
    root = data.get("project_root") if isinstance(data, dict) else None
    if not isinstance(root, str) or not os.path.isdir(root) or not isinstance(builders, list) \
            or any(problem(b) is not None or "timeout_minutes" not in b for b in builders):
        print(f"{path}: not a file written by builders_check.py", file=sys.stderr)
        sys.exit(2)
    return data


def folders(root: str, repo: tuple) -> tuple:
    """The folders a trust file must not be in: the project root and its git top-level."""
    return (root, repo[0])


# Actions
# =========================================================================


def check(args) -> int:
    data = read_builders(args.builders)
    root = data["project_root"]
    repo = identity(root)
    try:
        entries = load(trust_path(), folders(root, repo))
    except Refused as err:
        print(err, file=sys.stderr)
        entries = []
    trusted = []
    for builder in data["builders"]:
        if any(matches(e, repo, builder) for e in entries):
            trusted.append(builder)
            print(f"{line(builder)} (trusted)")
        elif args.unattended:
            print(f"Skipped: {builder['name']} (not confirmed)")
        else:
            print(line(builder))
    try:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump({"project_root": root, "builders": trusted}, fh, indent=2)
    except OSError as err:
        print(f"cannot write {args.out}: {err}", file=sys.stderr)
        return 2
    return 0


def add(args) -> int:
    data = read_builders(args.builders)
    builder = next((b for b in data["builders"] if b["name"] == args.name), None)
    if builder is None:
        print(f"{args.name} is not a checked builder in {args.builders}", file=sys.stderr)
        return 2
    root = data["project_root"]
    repo = identity(root)
    path = trust_path()
    try:
        entries = load(path, folders(root, repo))
    except Refused as err:
        print(f"{err}; nothing written", file=sys.stderr)
        return 2
    kept = [e for e in entries if not ((e["repository"], e["origin"]) == repo and e["name"] == builder["name"])]
    kept.append({"repository": repo[0], "origin": repo[1], "name": builder["name"],
                 "command": builder["command"], "timeout_minutes": builder["timeout_minutes"]})
    try:
        save(path, kept)
    except OSError as err:
        print(f"cannot write {path}: {err}", file=sys.stderr)
        return 2
    print(f"Trusted: {builder['name']}")
    return 0


def listing(args) -> int:
    repo = identity(args.root)
    try:
        entries = load(trust_path(), folders(args.root, repo))
    except Refused as err:
        print(err, file=sys.stderr)
        return 0
    for entry in entries:
        if (entry["repository"], entry["origin"]) == repo:
            print(line(entry))
    return 0


def remove(args) -> int:
    repo = identity(args.root)
    path = trust_path()
    try:
        entries = load(path, folders(args.root, repo))
    except Refused as err:
        print(f"{err}; nothing removed", file=sys.stderr)
        return 2
    kept = [e for e in entries if not ((e["repository"], e["origin"]) == repo and e["name"] == args.name)]
    if len(kept) == len(entries):
        print(f"no trusted builder {args.name} for {repo[0]}", file=sys.stderr)
        return 1
    try:
        save(path, kept)
    except OSError as err:
        print(f"cannot write {path}: {err}", file=sys.stderr)
        return 2
    print(f"Removed: {args.name}")
    return 0


def main() -> int:
    ap = Usage(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="action", required=True, parser_class=Usage)
    p = sub.add_parser("check")
    p.add_argument("--builders", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--unattended", action="store_true", help="print Skipped: <name> (not confirmed) for the rest")
    p = sub.add_parser("add")
    p.add_argument("--builders", required=True)
    p.add_argument("--name", required=True)
    p = sub.add_parser("list")
    p.add_argument("--root", required=True)
    p = sub.add_parser("remove")
    p.add_argument("--root", required=True)
    p.add_argument("--name", required=True)
    args = ap.parse_args()
    if getattr(args, "name", None) is not None and not NAME.fullmatch(args.name):
        ap.error("--name must match ^[A-Za-z0-9._-]{1,64}$")
    if getattr(args, "root", None) is not None and not os.path.isdir(args.root):
        ap.error(f"--root {args.root} is not a directory")
    return {"check": check, "add": add, "list": listing, "remove": remove}[args.action](args)


if __name__ == "__main__":
    sys.exit(main())
