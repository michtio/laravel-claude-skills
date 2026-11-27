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
  - an agent file needs a --- fenced frontmatter block;
  - startup over 48 KB (checker 16 KB) fails;
  - the Agent tool counts in every form: Agent, Agent(...), Task, Task(...);
    an agent with no `tools:` line inherits it (plan AD3) unless
    `disallowedTools:` names it; an agent without it has cap 0;
  - an agent with the Agent tool declares `At most N agents per <run|review>`,
    N <= 5;
  - a `*-checker` or `*-gate-writer` agent never has the Agent tool, and a
    planner or reviewer without a `tools:` line disallows it;
  - a read-only agent (planner, reviewer, checker or gate-writer) disallows
    mcp__laravel-boost__tinker and mcp__laravel-boost__record-rule (it writes
    .ai/rules);
  - a planner, reviewer or checker also disallows Write, Edit and NotebookEdit
    (the gate writer writes tests, so it is exempt from that one);
  - reviewer and checker agents never use effort: xhigh (quotes stripped).
Role markers match both the file stem and the frontmatter `name:`.

Usage:
    python3 scripts/agent_budget.py              # table; exit 1 on any violation
    python3 scripts/agent_budget.py --root DIR   # check another tree (self-tests)

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
RECORD_RULE = "mcp__laravel-boost__record-rule"  # writes .ai/rules
WRITE_TOOLS = ("Write", "Edit", "NotebookEdit")
READ_ONLY_MARKERS = ("planner", "reviewer", "checker", "gate-writer")
NO_WRITE_MARKERS = ("planner", "reviewer", "checker")


AGENT_TOOLS = ("Agent", "Task")  # Task is the old name of the Agent tool
KEY_LINE = re.compile(r"^([A-Za-z_][\w-]*):[ \t]*(.*)$")
ITEM_LINE = re.compile(r"^\s*-\s*(.*)$")


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1].strip()
    return value


def split_inline(value: str) -> list[str]:
    """Split an inline list on commas outside parentheses: `Read, Agent(a, b)`."""
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    items, depth, current = [], 0, ""
    for ch in value:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(depth - 1, 0)
        if ch == "," and depth == 0:
            items.append(current)
            current = ""
        else:
            current += ch
    items.append(current)
    return [unquote(i) for i in items if unquote(i)]


def parse_frontmatter(agent: Path) -> dict[str, object] | None:
    """Parse the frontmatter into {key: str | list[str]}; None when there is none.

    A file has frontmatter when its first line is `---` and a later line is `---`.
    A key with an inline value keeps it as a string (lists are split later by
    `as_list`); a key with no inline value collects the block list below it.
    Block items may start at column 0; blank lines and comments are skipped.
    """
    lines = agent.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        close = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        return None
    data: dict[str, object] = {}
    key = None
    for line in lines[1:close]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = KEY_LINE.match(line)
        if m:
            key = m.group(1)
            value = m.group(2).strip()
            data[key] = value if value else []
            continue
        item = ITEM_LINE.match(line)
        if item and key is not None and isinstance(data.get(key), list):
            value = unquote(item.group(1))
            if value:
                data[key].append(value)
    return data


def as_list(data: dict[str, object], key: str) -> list[str]:
    value = data.get(key)
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return split_inline(value)


def as_scalar(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    return unquote(value) if isinstance(value, str) else ""


def tool_name(entry: str) -> str:
    """`Agent(a, b)` -> `Agent`."""
    return entry.split("(", 1)[0].strip()


def check(agent: Path, skills_dir: Path) -> tuple[str, list[str]]:
    stem = agent.stem
    data = parse_frontmatter(agent)
    if data is None:
        return f"{stem:26} cap ?", ["no frontmatter (no --- fences around the header)"]

    name = as_scalar(data, "name")
    labels = (stem, name) if name else (stem,)
    tools_declared = "tools" in data
    tools = {tool_name(t) for t in as_list(data, "tools")}
    disallowed_entries = as_list(data, "disallowedTools")
    disallowed_exact = set(disallowed_entries)

    def role(*markers: str) -> bool:
        return any(m in label for label in labels for m in markers)

    def suffix(*suffixes: str) -> bool:
        return any(label.endswith(s) for label in labels for s in suffixes)

    # Agent tool: stated in `tools:` (any form), or inherited when there is no
    # `tools:` line (plan AD3), unless `disallowedTools:` removes it.
    # Only a bare name removes a tool: `Agent(x)` in disallowedTools removes one
    # subagent type, not the Agent tool.
    agent_disallowed = any(t in disallowed_exact for t in AGENT_TOOLS)
    if tools_declared:
        has_agent = any(t in tools for t in AGENT_TOOLS) and not agent_disallowed
    else:
        has_agent = not agent_disallowed

    problems: list[str] = []
    cap_label = "cap 0"
    if has_agent:
        if suffix("-checker", "-gate-writer"):
            cap_label = "cap ?"
            problems.append("must not have the Agent tool"
                            + ("" if tools_declared else " (no tools: line, so it inherits Agent; disallow it)"))
        elif not tools_declared and role("planner", "reviewer"):
            cap_label = "cap ?"
            problems.append("must disallow Agent (no tools: line, so it inherits Agent)")
        else:
            caps = [int(n) for n in CAP_LINE.findall(agent.read_text(encoding="utf-8"))]
            if not caps:
                cap_label = "cap ?"
                problems.append("Agent tool without an 'At most N agents per run|review' line"
                                + ("" if tools_declared else " (no tools: line, so it inherits Agent)"))
            elif max(caps) > MAX_AGENTS:
                cap_label = f"cap {max(caps)}"
                problems.append(f"cap above {MAX_AGENTS}")
            else:
                cap_label = f"cap {max(caps)}"

    sizes = {}
    for skill in as_list(data, "skills"):
        path = skills_dir / skill / "SKILL.md"
        if path.is_file():
            sizes[skill] = path.stat().st_size
        else:
            problems.append(f"preloads unknown skill {skill}")
    total = agent.stat().st_size + sum(sizes.values())
    budget = CHECKER_BUDGET if role("checker") else BUDGET
    if total > budget:
        problems.append(f"over {budget // 1024} KB")

    if role(*READ_ONLY_MARKERS) and TINKER not in disallowed_exact:
        problems.append(f"read-only agent must disallow {TINKER}")
    if role(*READ_ONLY_MARKERS) and RECORD_RULE not in disallowed_exact:
        problems.append(f"read-only agent must disallow {RECORD_RULE}")
    if role(*NO_WRITE_MARKERS) and not all(t in disallowed_exact for t in WRITE_TOOLS):
        problems.append("read-only agent must disallow Write, Edit, NotebookEdit")
    if role("reviewer", "checker") and as_scalar(data, "effort") == "xhigh":
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
