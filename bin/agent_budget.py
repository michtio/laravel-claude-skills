#!/usr/bin/env python3
"""Startup budget and tool rules for the package's agents (R15, R25).

Ported from craftcms-claude-skills (bin/agent_budget.py, 1.31.0) and adapted to
this package's layout: agents in agents/*.md, skills in
resources/boost/skills/<name>/SKILL.md (Boost installs them into the app).

An agent starts with its own file plus every skill in its `skills:` frontmatter
preloaded in full. Startup bytes = agents/<agent>.md + the SKILL.md of each
preloaded skill; the budget is 48 KB (~12K tokens at ~4 bytes per token), and a
checker starts under 16 KB because it runs once per lens. Skills that are not
preloaded load on demand with the Skill tool.

Rules (tests/gate/CONTRACT.md section 1):
  - startup over 48 KB (checker 16 KB) fails;
  - an agent without Agent in `tools:` has cap 0;
  - an agent with Agent declares `At most N agents per <run|review>`, N <= 5;
  - a `*-checker` or `*-gate-writer` agent never has Agent;
  - a read-only agent (name contains planner, reviewer, checker or gate-writer)
    disallows mcp__laravel-boost__tinker in `disallowedTools:`;
  - a planner, reviewer or checker also disallows Write, Edit and NotebookEdit
    (the gate writer writes tests, so it is exempt from that one);
  - reviewer and checker agents never use effort: xhigh.

Usage:
    python3 bin/agent_budget.py              # table; exit 1 on any violation
    python3 bin/agent_budget.py --root DIR   # check another tree (self-tests)

Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BUDGET = 48 * 1024
CHECKER_BUDGET = 16 * 1024
MAX_AGENTS = 5
CAP_LINE = re.compile(r"At most (\d+) agents per (?:run|review)\b")
TINKER = "mcp__laravel-boost__tinker"
WRITE_TOOLS = ("Write", "Edit", "NotebookEdit")
READ_ONLY_MARKERS = ("planner", "reviewer", "checker", "gate-writer")
NO_WRITE_MARKERS = ("planner", "reviewer", "checker")


def frontmatter(agent: Path) -> str:
    """Return the frontmatter block of an agent file, or '' when it has none."""
    text = agent.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return ""
    parts = text.split("\n---", 1)
    return parts[0] if len(parts) == 2 else ""


def field_list(head: str, key: str) -> list[str]:
    """Read a list field, written inline (`a, b`, `[a, b]`) or as a YAML block list."""
    m = re.search(rf"^{key}:[ \t]*(.*)$", head, re.M)
    if not m:
        return []
    inline = m.group(1).strip()
    if inline:
        inline = inline.strip("[]")
        return [t.strip().strip("'\"") for t in inline.split(",") if t.strip()]
    items = []
    for line in head[m.end():].splitlines()[1:]:
        item = re.match(r"^\s+-\s*(.+)$", line)
        if not item:
            break
        items.append(item.group(1).strip().strip("'\""))
    return items


def field(head: str, key: str) -> str:
    m = re.search(rf"^{key}:\s*(\S+)", head, re.M)
    return m.group(1) if m else ""


def agent_cap(agent: Path, tools: list[str]) -> tuple[str, list[str]]:
    """Return (cap label, problems) for the agent-start rules."""
    if "Agent" not in tools:
        return "cap 0", []
    if agent.stem.endswith("-checker") or agent.stem.endswith("-gate-writer"):
        return "cap ?", ["must not have the Agent tool"]
    caps = [int(n) for n in CAP_LINE.findall(agent.read_text(encoding="utf-8"))]
    if not caps:
        return "cap ?", ["Agent tool without an 'At most N agents per run|review' line"]
    if max(caps) > MAX_AGENTS:
        return f"cap {max(caps)}", [f"cap above {MAX_AGENTS}"]
    return f"cap {max(caps)}", []


def check(agent: Path, skills_dir: Path) -> tuple[str, list[str]]:
    head = frontmatter(agent)
    tools = field_list(head, "tools")
    disallowed = set(field_list(head, "disallowedTools"))
    cap_label, problems = agent_cap(agent, tools)

    sizes = {}
    for skill in field_list(head, "skills"):
        path = skills_dir / skill / "SKILL.md"
        if path.is_file():
            sizes[skill] = path.stat().st_size
        else:
            problems.append(f"preloads unknown skill {skill}")
    total = agent.stat().st_size + sum(sizes.values())
    budget = CHECKER_BUDGET if "checker" in agent.stem else BUDGET
    if total > budget:
        problems.append(f"over {budget // 1024} KB")

    stem = agent.stem
    if any(m in stem for m in READ_ONLY_MARKERS) and TINKER not in disallowed:
        problems.append(f"read-only agent must disallow {TINKER}")
    if any(m in stem for m in NO_WRITE_MARKERS) and not all(t in disallowed for t in WRITE_TOOLS):
        problems.append("read-only agent must disallow Write, Edit, NotebookEdit")
    if ("reviewer" in stem or "checker" in stem) and field(head, "effort") == "xhigh":
        problems.append("reviewer agents use effort high, not xhigh")

    parts = ", ".join(f"{s} {b / 1024:.1f}" for s, b in sizes.items())
    line = (f"{stem:26} {cap_label}  {total / 1024:5.1f} KB (~{total // 4 // 1000}K tokens) = "
            f"agent {agent.stat().st_size / 1024:.1f} + {parts or 'no preloads'}")
    return line, problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=str(REPO), help="tree holding agents/ and resources/boost/skills/")
    args = parser.parse_args()
    root = Path(args.root)
    if not root.is_absolute():
        root = Path.cwd() / root
    agents_dir = root / "agents"
    skills_dir = root / "resources" / "boost" / "skills"

    failing = 0
    agents = sorted(agents_dir.glob("*.md")) if agents_dir.is_dir() else []
    for agent in agents:
        line, problems = check(agent, skills_dir)
        failing += bool(problems)
        flag = "ok  " if not problems else "FAIL"
        print(f"{flag} {line}" + (f"  <- {'; '.join(problems)}" if problems else ""))
    print(f"budget {BUDGET // 1024} KB per agent (checker {CHECKER_BUDGET // 1024} KB); "
          f"at most {MAX_AGENTS} agents started; {len(agents)} agents, {failing} failing")
    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main())
