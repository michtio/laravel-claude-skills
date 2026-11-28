#!/usr/bin/env python3
"""Check that an outside builder's hand-back has every required line (R26).

    python3 scripts/handback_check.py --brief <brief-file> <handback-file>

The brief and hand-back formats are in docs/brief-format.md. Required lines, each
at column 0 and outside code fences:

    Gate flow: locked (<sha>)  or  Gate flow: builder-written (<reason>)
    Lock check (committed): exit <n>      (locked flow only; must be exit 0)
    Lock check (working tree): exit <n>   (locked flow only; must be exit 0)
    R<n>: PASS|FAIL|PENDING               (one per "## R<n>" heading of the brief)
    Builder: <name>

Exit 0: well formed. Exit 1: a required line is missing, bad, duplicated or
unknown, one message per problem (`missing line: ...`, `bad line: ...`,
`bad status: ...`, `duplicate line: ...`, `unknown line: ...`, `gate touched: ...`).
Exit 2: usage error, an unreadable file, a brief with no R ids, or a brief whose
`Gate commit:` is missing or neither a sha nor `none`.

It checks form only: a FAIL or PENDING status is well formed; whether the slice
passed is the gated build's decision. The brief's `Gate commit:` binds the flow: a
sha means locked with a matching sha (one may be a prefix of the other), `none`
means builder-written. Lines inside ``` or ~~~ fences are ignored in both files; a
UTF-8 BOM is tolerated. Proved by tests/gate/test_handback_check.py and, on real
stub output, tests/gate/test_outside_builder_stubs.py.

Protocol ported from craftcms-claude-skills (bin/handback_check.py), so one team
tool serves both packs. Python 3.9+, standard library only.
"""
from __future__ import annotations

import re
import sys

USAGE = "usage: handback_check.py --brief <brief-file> <handback-file>"
FLOW = re.compile(r"^Gate flow: (?:locked \(([0-9a-fA-F]{7,40})\)|builder-written \((\S.*)\))$")
HEADING = re.compile(r"^## +R(\d+)(?:[ \t]*[:\-\u2013\u2014][ \t]*\S.*|[ \t]*)$")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
STATUSES = ("PASS", "FAIL", "PENDING")
LOCK_LABELS = ("committed", "working tree")


def read(path: str) -> str:
    """The file's text, BOM stripped; exit 2 when it cannot be read."""
    try:
        with open(path, encoding="utf-8-sig", newline="") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError) as err:
        print(f"cannot read {path}: {err}", file=sys.stderr)
        sys.exit(2)


def visible_lines(text: str) -> list:
    """Split on real newlines only and drop fenced lines (fenced.md proves a fenced line never counts)."""
    out, fence = [], None
    for line in re.split(r"\r\n|\n|\r", text):
        m = FENCE.match(line)
        if fence is None:
            if m:
                fence = m.group(1)
            else:
                out.append(line)
        elif m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not line.strip(" `~"):
            fence = None
    return out


def requirement_ids(brief_lines: list) -> list:
    """The R ids of the brief's level-2 `## R<n>` headings, in order, without duplicates."""
    ids = []
    for line in brief_lines:
        m = HEADING.match(line)
        if m and m.group(1) not in ids:
            ids.append(m.group(1))
    return ids


def gate_commit(brief_lines: list):
    """The brief's gate commit: a lowercase sha, 'none', or None when the brief binds nothing (a usage error,
    test_handback_flow_binding: BriefMustBindTheFlow)."""
    for line in brief_lines:
        m = re.match(r"^Gate commit:[ \t]*(\S+)", line)
        if not m:
            continue
        value = m.group(1).strip("`")
        if value.lower() == "none":
            return "none"
        if re.fullmatch(r"[0-9a-fA-F]{7,40}", value):
            return value.lower()
        return None
    return None


def check_flow(lines: list, bound) -> tuple:
    """Problems with the Gate flow line, and whether the flow is locked (flow-downgrade.md, wrong-sha.md)."""
    flow_lines = [line for line in lines if line.startswith("Gate flow:")]
    if not flow_lines:
        return ["missing line: Gate flow"], False
    problems = []
    if len(flow_lines) > 1:
        problems.append("duplicate line: Gate flow")
    m = FLOW.match(flow_lines[0])
    if not m:
        return problems + ["bad line: Gate flow"], False
    sha = (m.group(1) or "").lower()
    if bound == "none" and sha:
        problems.append("bad line: Gate flow (the brief has no gate commit, so the flow must be builder-written)")
    elif bound != "none" and (not sha or not (sha.startswith(bound) or bound.startswith(sha))):
        problems.append(f"bad line: Gate flow (must be locked ({bound}) as in the brief)")
    return problems, bool(sha)


def check_locks(lines: list) -> list:
    """Problems with the two lock-check lines of a locked flow (missing-lock-line.md, lock-nonzero.md, dup-lock.md)."""
    problems = []
    for label in LOCK_LABELS:
        pattern = re.compile(r"^Lock check \(%s\): exit (\d+)$" % re.escape(label))
        hits = [m for m in (pattern.match(line) for line in lines) if m]
        if not hits:
            problems.append(f"missing line: Lock check ({label})")
            continue
        if len(hits) > 1:
            problems.append(f"duplicate line: Lock check ({label})")
        nonzero = [h.group(1) for h in hits if h.group(1) != "0"]
        if nonzero:
            problems.append(f"gate touched: Lock check ({label}) exit {nonzero[0]}")
    return problems


def check_requirements(lines: list, ids: list) -> list:
    """Problems with the R lines: one per brief R id, a known status, no unknown ids (missing-r-line.md, unknown-r.md)."""
    problems = []
    for n in ids:
        pattern = re.compile(r"^R%s: (\S+)$" % n)
        hits = [m for m in (pattern.match(line) for line in lines) if m]
        if not hits:
            problems.append(f"missing line: R{n}")
            continue
        if len(hits) > 1:
            problems.append(f"duplicate line: R{n}")
        bad = [h.group(1) for h in hits if h.group(1) not in STATUSES]
        if bad:
            problems.append(f"bad status: R{n}: {bad[0]}")
    seen = set()
    for line in lines:
        m = re.match(r"^R(\d+): ", line)
        if m and m.group(1) not in ids and m.group(1) not in seen:
            seen.add(m.group(1))
            problems.append(f"unknown line: R{m.group(1)}")
    return problems


def check_builder(lines: list) -> list:
    """Problems with the Builder line (missing-builder.md)."""
    builders = [line for line in lines if re.match(r"^Builder: \S.*$", line)]
    if not builders:
        return ["missing line: Builder"]
    if len(builders) > 1:
        return ["duplicate line: Builder"]
    return []


def main(argv: list) -> int:
    args = argv[1:]
    if len(args) != 3 or args[0] != "--brief":
        print(USAGE, file=sys.stderr)
        return 2
    brief = visible_lines(read(args[1]))
    lines = visible_lines(read(args[2]))
    ids = requirement_ids(brief)
    if not ids:
        print(f"{args[1]}: no R ids (## R<n> headings) in the brief", file=sys.stderr)
        return 2

    bound = gate_commit(brief)
    if bound is None:
        print(f"{args[1]}: no Gate commit (sha or none) in the brief", file=sys.stderr)
        return 2

    problems, locked = check_flow(lines, bound)
    if locked:
        problems += check_locks(lines)
    problems += check_requirements(lines, ids)
    problems += check_builder(lines)

    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
