"""Gate test for slice S9b (laravel-layer): the agent-file rules the field test asked for.

Requirements R15, R17. Skills-gaps rows 17, 23, 29, 67, 69, and the merge rule.
Contract: tests/S9b/CONTRACT.md section 8. Standard library only; no DDEV, no network.

Each test states a behavior a real agent follows and checks that the agent's own text carries it,
all of it in ONE paragraph or bullet (a line of the file): a keyword somewhere in the file does not
count. The checks use the operative words (what to do, when, what never), not a fixed sentence.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_s8 as s8  # noqa: E402

I = re.I


def lines(text: str) -> list:
    return text.splitlines()


def one_line(test: unittest.TestCase, text: str, *patterns: str, label: str) -> str:
    """The first line of the file that matches every pattern; fails with the label when none does."""
    for line in lines(text):
        if all(re.search(p, line, I) for p in patterns):
            return line
    test.fail(f"no single paragraph or bullet states: {label}")


def fenced_blocks(text: str) -> list:
    return re.findall(r"```[a-z]*\n(.*?)```", text, re.S)


def section(text: str, heading: str) -> str:
    m = re.search(rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1) if m else ""


class GateWriter(unittest.TestCase):
    def text(self):
        return s8.read_agent(self, "laravel-gate-writer")

    # Row 69, 65: format its own files
    def test_formats_only_its_own_test_files_before_the_commit_and_reruns(self):
        step = one_line(self, section(self.text(), "Method"), r"\bpint\b|formatter", r"git add", r"(own|your) (test )?files?|only (on )?your",
                        label="before git add, run the project's formatter on its own test files only")
        self.assertRegex(step, r"(?is)before[^.]{0,200}git add")
        self.assertRegex(step, r"(?is)(rerun|run again|re-run)[^.]{0,120}tests")

    def test_never_formats_the_whole_project_or_a_locked_file(self):
        self.assertRegex(self.text(), r"(?is)never[^.]{0,160}(bare|whole|entire|all files)[^.]{0,200}(pint|formatter)|(pint|formatter)[^.]{0,200}never[^.]{0,120}(bare|whole|entire|every)",
                         "a bare pint run rewrites files that are not the writer's")

    def test_hand_back_reports_the_format_check_next_to_the_commit(self):
        blocks = [b for b in fenced_blocks(self.text()) if "Gate commit:" in b]
        self.assertTrue(blocks)
        self.assertRegex(blocks[0], r"(?m)^Format:", "the hand-back has a Format: line (the format check, with the command it ran)")

    # Row 17: chosen names
    def test_every_public_name_it_chose_goes_under_open(self):
        line = one_line(self, self.text(), r"\bOpen\b", r"names?", r"chose|chosen|invent",
                        label="every public name the writer chose is reported under Open")
        for kind in ("class", "method", "config key", "env"):
            self.assertRegex(line + "\n" + "\n".join(lines(self.text())), kind)

    def test_the_open_line_of_the_hand_back_carries_the_names(self):
        blocks = [b for b in fenced_blocks(self.text()) if "Gate commit:" in b]
        open_line = next((l for l in lines(blocks[0]) if l.startswith("Open:")), "")
        self.assertRegex(open_line, r"(?i)names?", "the Open: line of the hand-back template names the chosen names")


class Builder(unittest.TestCase):
    def text(self):
        return s8.read_agent(self, "laravel-builder")

    # Row 23: no todo tool
    def test_without_a_todo_tool_the_steps_go_in_the_first_message_and_the_hand_back(self):
        body = section(self.text(), "Todo list")
        line = one_line(self, body, r"(no|without|neither|lack)[^.]{0,80}(todo|task)[^.]{0,40}tool|(todo|task)[^.]{0,40}tool[^.]{0,80}(missing|absent|not available|not there)",
                        label="the case where no todo tool exists")
        self.assertRegex(line, r"(?i)first message")
        self.assertRegex(line, r"(?i)hand-back")

    def test_the_hand_back_has_a_todo_line(self):
        block = next(b for b in fenced_blocks(self.text()) if "Gate flow:" in b and "Built:" in b)
        self.assertRegex(block, r"(?m)^Todo:", "the hand-back template has a Todo: line (the steps, marked, or `no todo tool`)")

    def test_skipping_the_todo_list_silently_is_not_allowed(self):
        self.assertRegex(section(self.text(), "Todo list"), r"(?is)never[^.]{0,120}(skip|omit|drop)[^.]{0,80}(todo|list)|(skip|omit)[^.]{0,80}silently")

    # Row 29: push follows the brief
    def test_push_and_pr_follow_the_brief_on_the_slice_branch_never_main(self):
        git = one_line(self, self.text(), r"\*\*Git\.\*\*", label="the Git bullet")
        self.assertRegex(git, r"(?is)push[^.]{0,200}(pull request|\bPR\b)[^.]{0,200}brief|brief[^.]{0,200}push",
                         "the brief can ask for a push and a PR")
        self.assertRegex(git, r"(?is)slice branch")
        self.assertRegex(git, r"(?is)never[^.]{0,200}(main|default branch|base branch)")
        self.assertRegex(git, r"(?is)never[^.]{0,200}force")

    def test_without_the_brief_asking_the_builder_does_not_push(self):
        git = one_line(self, self.text(), r"\*\*Git\.\*\*", label="the Git bullet")
        self.assertRegex(git, r"(?is)(unless|only when|only if|without)[^.]{0,200}brief[^.]{0,200}(push|ask)|(push|pull request)[^.]{0,200}(unless|only when|only if)[^.]{0,80}brief",
                         "no push or PR unless the brief asks for it")
        self.assertNotRegex(git, r"(?i)you never push, rebase", "the unconditional 'never push' contradicts a brief that asks for one")

    def test_the_hand_back_has_a_pr_line(self):
        block = next(b for b in fenced_blocks(self.text()) if "Gate flow:" in b and "Built:" in b)
        self.assertRegex(block, r"(?m)^PR:", "the hand-back has a PR: line (url, or none)")

    # Row 67: tripwire stopping rule
    def test_a_tripwire_check_stops_after_one_row_per_bypass_and_documents_the_rest(self):
        line = one_line(self, self.text(), r"tripwire", r"(one|single)[^.]{0,40}(test )?row", r"(false negative|false positive)", r"(docblock|document)",
                        label="a tripwire check: fix what one test row closes, document the rest as false negatives or positives")
        self.assertRegex(line, r"(?i)reopen[^.]{0,60}design|design[^.]{0,60}(not|never)[^.]{0,40}reopen")

    def test_tripwire_rounds_count_against_the_briefs_cap(self):
        one_line(self, self.text(), r"tripwire", r"round", r"(cap|3|three)",
                 label="tripwire rounds count against the cap of 3 rounds")

    def test_a_tripwire_is_recognised_by_what_it_is(self):
        one_line(self, self.text(), r"tripwire", r"(heuristic|regex|pattern|content check)", r"(no fixed point|cannot be complete|never complete|every bypass|by design)",
                 label="what makes a check a tripwire (a heuristic that can always be bypassed), so the rule applies")

    # The merge rule
    def test_a_gated_pr_merges_with_a_merge_commit_never_a_squash(self):
        line = one_line(self, self.text(), r"merge commit", r"squash", r"gate commit",
                        label="a gated PR merges with a merge commit, never a squash, because a squash removes the gate commit")
        self.assertRegex(line, r"(?is)never[^.]{0,80}squash|not[^.]{0,40}squash")

    def test_the_hand_back_pr_line_names_the_merge_method(self):
        block = next(b for b in fenced_blocks(self.text()) if "Gate flow:" in b and "Built:" in b)
        pr = next((l for l in lines(block) if l.startswith("PR:")), "")
        self.assertRegex(pr, r"(?i)merge commit", "the PR: line says the PR is to be merged with a merge commit")


class Budgets(unittest.TestCase):
    def test_the_two_files_stay_inside_the_startup_budget(self):
        for stem in ("laravel-builder", "laravel-gate-writer"):
            size = s8.agent_path(stem).stat().st_size
            self.assertLess(size, 48 * 1024, f"{stem} is {size} bytes")


if __name__ == "__main__":
    unittest.main()
