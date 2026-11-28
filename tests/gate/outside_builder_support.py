"""Shared paths and helpers for the outside-builder gate tests (gated builds run by builders the profile names).

Contract: tests/OutsideBuilders/CONTRACT.md. Standard library only.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests/Fixtures/outside-builders"
PROJECT = FIXTURES / "gated-build"
HANDBACKS = FIXTURES / "handback"
RELEASE_CASES = FIXTURES / "release-cases.json"
SAMPLES = FIXTURES / "release-samples"
CHECKER = REPO / "scripts/handback_check.py"
SKILL = REPO / "resources/boost/skills/laravel-gated-build/SKILL.md"
BRIEF_DOC = REPO / "docs/brief-format.md"
BUILDERS_DOC = REPO / "docs/outside-builders.md"
PROFILE_DOC = REPO / "docs/profile.md"
CHECK_SH = REPO / "scripts/check.sh"

CALL_FORM = "<command> <brief-file> <handback-file>"
LOCK_COMMITTED = "git diff --quiet <gate commit> HEAD -- <gate files>"
LOCK_TREE = "git diff --quiet <gate commit> -- <gate files>"
GATE_FILE = "tests/Feature/GreetingTest.php"
# Decisions log 2026-11-27: the package says "local AI", never a named model or tool.
NAMED_MODELS = ("qwen", "mistral", "ollama", "gemini", "glm", "vibe", "vllm", "bc-build")
CLAUDE_ONLY_TOOLING = ("Skill tool", "Agent tool", "subagent", "CLAUDE_PLUGIN_ROOT", "TodoWrite")


def rel(path: Path) -> str:
    return str(path.relative_to(REPO))


def read_new(test: unittest.TestCase, path: Path) -> str:
    """The text of a file the slice adds; a clear failure when it does not exist yet."""
    test.assertTrue(path.is_file(), f"{rel(path)} is missing")
    return path.read_text(encoding="utf-8")


def require_checker(test: unittest.TestCase) -> None:
    test.assertTrue(CHECKER.is_file(), "scripts/handback_check.py is missing")


def run_checker(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CHECKER), *args], capture_output=True, text=True, cwd=REPO)


def check(brief: Path, handback: Path) -> subprocess.CompletedProcess:
    return run_checker("--brief", str(brief), str(handback))


def paragraphs(text: str) -> list:
    """One entry per line of the file: a rule counts only when one paragraph or bullet carries it."""
    return [line for line in text.splitlines() if line.strip()]


def has_line(text: str, *patterns: str) -> bool:
    return any(all(re.search(p, line, re.I) for p in patterns) for line in paragraphs(text))


def assert_line(test: unittest.TestCase, text: str, *patterns: str, label: str) -> None:
    test.assertTrue(has_line(text, *patterns), f"no single line states: {label} (patterns {patterns})")


def git(cwd: Path, *args: str, check_rc: bool = True) -> subprocess.CompletedProcess:
    env = dict(os.environ, GIT_AUTHOR_NAME="fixture", GIT_AUTHOR_EMAIL="fixture@example.com",
               GIT_COMMITTER_NAME="fixture", GIT_COMMITTER_EMAIL="fixture@example.com")
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        env.pop(key, None)
    proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, env=env)
    if check_rc and proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {proc.stderr}")
    return proc


GATE_TEST = """<?php

use App\\Services\\GreetingService;

it('greets a name', function () {
    // expect-file: app/Services/GreetingService.php
    // expect-contains: app/Services/GreetingService.php function greet(string $name): string
    expect((new GreetingService())->greet('Ada'))->toBe('Hello, Ada!');
});

it('greets the world for an empty name', function () {
    // expect-contains: app/Services/GreetingService.php Hello, world!
    expect((new GreetingService())->greet(''))->toBe('Hello, world!');
});
"""

BRIEF = """# Brief: S1 greeting service

Slice: S1
Project root: {root}
Laravel version: 13.0
Gate commit: {gate}
Gate files: {gate_file}
Pest command: vendor/bin/pest

## R1

The app MUST have a `GreetingService` with a `greet(string $name): string` method that returns a greeting for the name.
AC1: Given the name `Ada`, when `App\\Services\\GreetingService::greet('Ada')` is called, then it returns `Hello, Ada!`.
AC2: Given an empty name, when `App\\Services\\GreetingService::greet('')` is called, then it returns `Hello, world!`.

## Pointers

- CLAUDE.md

## Rules

- Never edit a gate file.
- Stop at a passing gate.
- At most 3 rounds.
- Commit your work before writing the hand-back.
"""


class GatedCopy:
    """A throwaway git copy of the fixture project with a gate commit, a brief outside the tree and a hand-back path.

    The stubs are run from the temp root, not from the project, so a commit in the project proves the stub
    read the brief's Project root.
    """

    def __enter__(self) -> "GatedCopy":
        self.tmp = Path(tempfile.mkdtemp(prefix="outside-builder-"))
        self.root = self.tmp / "project"
        shutil.copytree(PROJECT, self.root, symlinks=True,
                        ignore=shutil.ignore_patterns(".claude", "michtio"))
        git(self.root, "init", "-q")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "chore: fixture")
        (self.root / GATE_FILE).write_text(GATE_TEST, encoding="utf-8")
        git(self.root, "add", "--", GATE_FILE)
        git(self.root, "commit", "-q", "-m", "test(gate): S1")
        self.gate = git(self.root, "rev-parse", "HEAD").stdout.strip()
        self.brief = self.tmp / "brief.md"
        self.brief.write_text(BRIEF.format(root=self.root, gate=self.gate, gate_file=GATE_FILE), encoding="utf-8")
        self.handback = self.tmp / "handback.md"
        return self

    def __exit__(self, *exc) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_stub(self, name: str) -> subprocess.CompletedProcess:
        stub = PROJECT / "bin" / name
        env = {k: v for k, v in os.environ.items() if k not in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")}
        return subprocess.run([str(stub), str(self.brief), str(self.handback)], cwd=self.tmp,
                              capture_output=True, text=True, env=env, timeout=120)

    def subjects_after_gate(self) -> list:
        out = git(self.root, "log", "--reverse", "--format=%s", f"{self.gate}..HEAD").stdout
        return [s for s in out.splitlines() if s]

    def head(self) -> str:
        return git(self.root, "rev-parse", "HEAD").stdout.strip()

    def status(self) -> str:
        return git(self.root, "status", "--porcelain", "--untracked-files=all").stdout

    def lock_committed(self) -> int:
        return git(self.root, "diff", "--quiet", self.gate, "HEAD", "--", GATE_FILE, check_rc=False).returncode
