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
character asks again. The user and password of an origin URL with a scheme
(`https://user:password@host/...`, `https://token@host/...`) are stripped first, so no
output or trust file byte holds them and a rotated password keeps the trust.

A command that runs a file of the repository is also keyed on the sha256 of that
file's bytes (read through any symlink), so a commit or edit to it, or a retargeted
symlink, asks again. The repo file of a command, split as a POSIX shell splits words:
its first word when that word holds a `/`; else, when the first word is an
interpreter (sh, bash, zsh, dash, python, python3, php, node, ruby, perl), its first
argument that does not start with `-` (none after `-c`, whose code is the command
text itself). It counts when that path, joined to the project root without resolving
symlinks, is inside the git top-level. A missing repo file cannot be trusted. A
command whose first word is a task runner (make, just, composer, npm, npx, pnpm,
yarn, ddev) runs repository files no key covers: `check` marks it `(runs repo code)`.

The trust file lives outside every repository:
    $LARAVEL_CLAUDE_SKILLS_TRUST_FILE when set, else
    $XDG_CONFIG_HOME/laravel-claude-skills/trusted-builders.json when that is set, else
    ~/.config/laravel-claude-skills/trusted-builders.json
`add` creates it with mode 0600. Nothing in it is trusted when its real path is
inside the project (so a cloned repo cannot approve itself), when its group or other
write bit is set, when another user owns it, or when it is not valid; the reason and
the path go to stderr, and a corrupt file is never overwritten.

check   prints one line per builder of --builders, in order:
        `<name>: <command> (timeout <n> min) (trusted)` for a trusted one
        (`(trusted, runs repo code)` for a task runner), and for the rest
        `<name>: <command> (timeout <n> min)` (plus ` (runs repo code)` for a task
        runner), or with --unattended `Skipped: <name> (not confirmed)`. Writes --out in the --builders format with
        the trusted builders only, so scripts/run_builder.py --builders can run
        nothing else from it. Exit 0; 2 for a usage error, an unreadable --builders
        file or an unwritable --out.
add     records the builder of --builders with that name (never a command from the
        arguments) and prints `Trusted: <name>`; adding it again keeps one entry, and
        an older entry of the same repository and name is replaced. Exit 0; 2, trust
        file untouched, for a name not in --builders, a repo file that does not exist,
        or a trust file that is ignored.
list    prints `<name>: <command> (timeout <n> min)` per entry of this repository.
remove  deletes this repository's entries with that name and prints `Removed: <name>`;
        exit 1 when there is none, 2 when the trust file is ignored. Entries of other
        repositories stay.

The trust file is read through one file descriptor (open, then fstat for its mode and
owner), and add and remove hold an exclusive lock on `<trust file>.lock` from the
read to the write, so concurrent calls never lose an entry.

git runs with argument lists, never through a shell. Proved by
tests/gate/test_builder_trust.py, test_builder_trust_repo_files.py and
test_builder_trust_rules.py. Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile

from builders_check import NAME, minutes_text, problem

TRUST_ENV = "LARAVEL_CLAUDE_SKILLS_TRUST_FILE"
TRUST_NAME = os.path.join("laravel-claude-skills", "trusted-builders.json")
VERSION = 1
INTERPRETERS = ("sh", "bash", "zsh", "dash", "python", "python3", "php", "node", "ruby", "perl")
TASK_RUNNERS = ("make", "just", "composer", "npm", "npx", "pnpm", "yarn", "ddev")


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


def without_credentials(url: str) -> str:
    """The URL with the user and password, the query and the fragment of a scheme URL removed
    (`https://user:pass@host/x?private_token=t#f` and `https://token@host/x` become `https://host/x`); an
    scp-like `git@host:x` has no scheme and stays."""
    scheme, sep, rest = url.partition("://")
    if not sep:
        return url
    rest = re.split(r"[?#]", rest, maxsplit=1)[0]
    authority, slash, tail = rest.partition("/")
    return f"{scheme}://{authority.rpartition('@')[2]}{slash}{tail}"


def identity(root: str) -> tuple:
    """(real path of the git top-level, origin URL without credentials); the root's real path when it is not in
    a git repository."""
    top = git(root, "rev-parse", "--show-toplevel")
    path = top.stdout.strip() if top.returncode == 0 and top.stdout.strip() else root
    origin = git(root, "config", "--get", "remote.origin.url")
    return os.path.realpath(path), without_credentials(origin.stdout.strip()) if origin.returncode == 0 else ""


# Repo code
# =========================================================================


def words(command: str) -> list:
    """The command split as a POSIX shell splits words; [] when it does not split (an open quote)."""
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return []


ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
# Wrapper -> its options that take a value (as a separate word); every other `-` word is a flag.
WRAPPERS = {
    "env": ("-u", "--unset", "-C", "--chdir", "-S", "--split-string"),
    "nice": ("-n", "--adjustment"),
    "timeout": ("-s", "--signal", "-k", "--kill-after"),
    "nohup": (),
    "exec": ("-a",),
    "command": (),
}


def name_of(word: str) -> str:
    """The case-folded basename of a command word or path, for matching interpreters, wrappers and runners."""
    return os.path.basename(word).casefold()


def lookup(word: str, root: str):
    """Where the shell finds the word: a word with a `/` joined to the project root (not resolved), a bare word
    through PATH, relative PATH entries taken from the project root; None when PATH has no such executable."""
    if "/" in word:
        return os.path.normpath(os.path.join(os.path.realpath(root), word))
    dirs = [os.path.join(os.path.realpath(root), d) for d in os.environ.get("PATH", "").split(os.pathsep) if d]
    found = shutil.which(word, path=os.pathsep.join(dirs))
    return os.path.normpath(found) if found else None


def unwrap(parts: list) -> tuple:
    """(the words after leading VAR=value words and the wrappers env, nice, timeout, nohup, exec and command
    with their options and values, whether a wrapper was skipped)."""
    wrapped = False
    while parts and ASSIGNMENT.match(parts[0]):
        parts = parts[1:]
    while parts and name_of(parts[0]) in WRAPPERS:
        wrapper, parts, wrapped = name_of(parts[0]), parts[1:], True
        while parts and parts[0].startswith("-") and parts[0] != "-":
            option, parts = parts[0], parts[1:]
            if option == "--":
                break
            if option in WRAPPERS[wrapper] and parts:
                parts = parts[1:]
        if wrapper == "env":
            while parts and ASSIGNMENT.match(parts[0]):
                parts = parts[1:]
        if wrapper == "timeout" and parts:
            parts = parts[1:]  # the duration
    return parts, wrapped


def inside_top(path: str, top: str) -> bool:
    """Whether the path, as joined or resolved through symlinks, is inside the git top-level."""
    return any(os.path.commonpath([candidate, top]) == top for candidate in (path, os.path.realpath(path)))


def file_digest(path: str):
    """sha256 of the file's bytes, read through any symlink; None when it cannot be read."""
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return None


def resolve(command: str, root: str, top: str) -> dict:
    """What the command runs, resolved as the shell does (test_builder_trust_resolution):

    kind `runner`        a task runner (make, composer, npm and the rest, `php artisan`, `python -m`): repo code
                         no key covers, marked `(runs repo code)`;
    kind `file`          a repository file, with its real path and sha256 (None when it cannot be read);
    kind `unresolvable`  the command after a wrapper is not found: it cannot be trusted;
    kind `plain`         anything else (a tool outside the repository, a shell builtin, inline code).
    Interpreters and runners match on the case-folded word or on the resolved file name, since a PATH tool can
    be a link to a versioned file (python3 -> python3.13, npm -> npm-cli.js)."""
    parts, wrapped = unwrap(words(command))
    if not parts:
        return {"kind": "unresolvable" if wrapped else "plain"}
    found = lookup(parts[0], root)
    if found is None and wrapped:
        return {"kind": "unresolvable"}
    names = {name_of(parts[0])} | ({name_of(os.path.realpath(found))} if found else set())
    if names & set(TASK_RUNNERS):
        return {"kind": "runner"}
    interpreter = next((n for n in names if n in INTERPRETERS), None)
    if interpreter is None and found and os.path.exists(found):
        base = name_of(os.path.realpath(found))
        interpreter = next((i for i in INTERPRETERS if base.startswith(i) and base[len(i):].lstrip(".0123456789") == ""), None)
    if interpreter is not None:
        target = None
        for arg in parts[1:]:
            if arg == "-c":
                return {"kind": "plain"}
            if arg == "-m" and interpreter.startswith("python"):
                return {"kind": "runner"}
            if not arg.startswith("-"):
                target = arg
                break
        if target is None:
            return {"kind": "plain"}
        if interpreter == "php" and target == "artisan":
            return {"kind": "runner"}
        path = os.path.normpath(os.path.join(os.path.realpath(root), target))
    elif found is not None:
        path = found
    else:
        return {"kind": "plain"}
    if not inside_top(path, top):
        return {"kind": "plain"}
    return {"kind": "file", "file": os.path.realpath(path), "sha256": file_digest(path)}


def fingerprint(builder: dict, root: str, repo: tuple) -> dict:
    """The resolution of this builder's command in this repository."""
    return resolve(builder["command"], root, repo[0])


def inside(path: str, folder: str) -> bool:
    """Whether the real path of path is folder or under it. Compared by file identity as well as by string, so
    a differently cased spelling on a case-insensitive volume is still inside (test_builder_trust_rules)."""
    real, base = os.path.realpath(path), os.path.realpath(folder)
    if os.path.commonpath([real, base]) == base:
        return True
    current = os.path.dirname(real)
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
    if any(key in entry and not isinstance(entry[key], str) for key in ("sha256", "file")):
        return False
    minutes = entry.get("timeout_minutes")
    return not isinstance(minutes, bool) and isinstance(minutes, (int, float))


def work_tree(path: str):
    """The git work tree that holds the trust file's folder (its nearest existing folder), or None. A trust file
    in any work tree (a dotfiles repository, another project), tracked, untracked or ignored, could be committed
    or changed by a pull, so it is refused (test_builder_trust_resolution: TrustFileInAGitTree)."""
    folder = os.path.dirname(os.path.realpath(path))
    while not os.path.isdir(folder):
        parent = os.path.dirname(folder)
        if parent == folder:
            return None
        folder = parent
    top = git(folder, "rev-parse", "--show-toplevel")
    return top.stdout.strip() or folder if top.returncode == 0 else None


def refusal(path: str, folders: tuple):
    """Why the trust file location is refused before anything is read or written, or None."""
    for folder in folders:
        if inside(path, folder):
            return f"ignored {path}: a trust file inside the project is never read"
    tree = work_tree(path)
    if tree is not None:
        return f"ignored {path}: a trust file inside a git work tree ({tree}) is never read"
    return None


def load(path: str, folders: tuple) -> list:
    """The entries of the trust file; [] when it does not exist. Raises Refused for a file inside one of the
    project folders, one others can write or another user owns, or a corrupt one."""
    reason = refusal(path, folders)
    if reason:
        raise Refused(reason)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    except FileNotFoundError:
        return []
    except OSError as err:
        raise Refused(f"ignored {path}: {err}")
    with os.fdopen(fd, "rb") as fh:
        info = os.fstat(fh.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise Refused(f"ignored {path}: not a regular file")
        if info.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise Refused(f"ignored {path}: group or other can write it (chmod 600 it)")
        if hasattr(os, "getuid") and info.st_uid != os.getuid():
            raise Refused(f"ignored {path}: another user owns it")
        try:
            data = json.loads(fh.read().decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as err:
            raise Refused(f"ignored {path}: not a valid trust file ({err}); fix or delete it")
    entries = data.get("entries") if isinstance(data, dict) and data.get("version") == VERSION else None
    if not isinstance(entries, list) or not all(valid_entry(e) for e in entries):
        raise Refused(f"ignored {path}: not a valid trust file; fix or delete it")
    return entries


class Locked:
    """An exclusive flock on `<real trust file>.lock` (mode 0600), held from the read to the write of add and
    remove, so two concurrent calls never lose an entry (test_builder_trust_rules: Locking)."""

    def __init__(self, path: str):
        real = os.path.realpath(path)
        os.makedirs(os.path.dirname(real), mode=0o700, exist_ok=True)
        self.lock = real + ".lock"

    def __enter__(self) -> "Locked":
        self.fd = os.open(self.lock, os.O_RDWR | os.O_CREAT, 0o600)
        fcntl.flock(self.fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc) -> None:
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        os.close(self.fd)


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
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, real)
        folder_fd = os.open(folder, os.O_RDONLY)
        try:
            os.fsync(folder_fd)
        finally:
            os.close(folder_fd)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def same_minutes(a, b) -> bool:
    return float(a) == float(b)


def matches(entry: dict, repo: tuple, builder: dict, resolved: dict) -> bool:
    """Whether the entry trusts this exact builder in this repository. An unresolvable command is never trusted;
    one that runs a repo file also needs the entry's file and sha256 to equal the file's real path and bytes (an
    entry without them, from before the key, never matches it)."""
    if resolved["kind"] == "unresolvable":
        return False
    if resolved["kind"] == "file" and (resolved["sha256"] is None or entry.get("sha256") != resolved["sha256"]
                                       or entry.get("file") != resolved["file"]):
        return False
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
        resolved = fingerprint(builder, root, repo)
        runner = resolved["kind"] == "runner"
        if any(matches(e, repo, builder, resolved) for e in entries):
            trusted.append(builder)
            print(f"{line(builder)} (trusted, runs repo code)" if runner else f"{line(builder)} (trusted)")
        elif args.unattended:
            print(f"Skipped: {builder['name']} (not confirmed)")
        else:
            print(f"{line(builder)} (runs repo code)" if runner else line(builder))
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
    resolved = fingerprint(builder, root, repo)
    if resolved["kind"] == "unresolvable":
        print(f"{args.name}: the command after a wrapper cannot be found; nothing written", file=sys.stderr)
        return 2
    if resolved["kind"] == "file" and resolved["sha256"] is None:
        print(f"{args.name} runs a repository file that does not exist or cannot be read; nothing written",
              file=sys.stderr)
        return 2
    path = trust_path()
    reason = refusal(path, folders(root, repo))
    if reason:
        print(f"{reason}; nothing written", file=sys.stderr)
        return 2
    entry = {"repository": repo[0], "origin": repo[1], "name": builder["name"],
             "command": builder["command"], "timeout_minutes": builder["timeout_minutes"]}
    if resolved["kind"] == "file":
        entry["file"], entry["sha256"] = resolved["file"], resolved["sha256"]
    try:
        with Locked(path):
            entries = load(path, folders(root, repo))
            kept = [e for e in entries if not ((e["repository"], e["origin"]) == repo and e["name"] == builder["name"])]
            save(path, kept + [entry])
    except Refused as err:
        print(f"{err}; nothing written", file=sys.stderr)
        return 2
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
    reason = refusal(path, folders(args.root, repo))
    if reason:
        print(f"{reason}; nothing removed", file=sys.stderr)
        return 2
    if not os.path.exists(path):
        print(f"no trusted builder {args.name} for {repo[0]}", file=sys.stderr)
        return 1
    try:
        with Locked(path):
            entries = load(path, folders(args.root, repo))
            kept = [e for e in entries if not ((e["repository"], e["origin"]) == repo and e["name"] == args.name)]
            if len(kept) == len(entries):
                print(f"no trusted builder {args.name} for {repo[0]}", file=sys.stderr)
                return 1
            save(path, kept)
    except Refused as err:
        print(f"{err}; nothing removed", file=sys.stderr)
        return 2
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
