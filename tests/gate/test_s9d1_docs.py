"""Gate test for slice S9d-1 (laravel-layer): README, docs/profile.md, CHANGELOG, the register row and
the CI step, and R7 as amended.

Requirements R1, R2, R7, R8, R9, R13, R23. Skills-gaps rows 12, 15, 16, 41, 51, 124, 127, 128 (docs
parts); owner rulings 2026-11-27 (R7 amended, skills.sh, spatie/guidelines-skills coexistence, the
unused-public-code check). Contract: tests/S9d1/CONTRACT.md sections 13 to 17.
Standard library only; no DDEV, no network.

Each check reads a section by its heading, or one paragraph or bullet (one line), so a phrase in the
wrong place does not count.
"""
from __future__ import annotations

import re
import subprocess
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_s9b_docs import find, sections  # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent
README = REPO / "README.md"
PROFILE_DOCS = REPO / "docs/profile.md"
CHANGELOG = REPO / "CHANGELOG.md"
CORE = REPO / "resources/boost/guidelines/core.blade.php"
SKILLS = REPO / "resources/boost/skills"
REGISTER = SKILLS / "laravel-package-verdicts/references/register.md"
CI_WORKFLOW = REPO / ".github/workflows/ci.yml"
COMPOSER = REPO / "composer.json"
I = re.I

# spatie/guidelines-skills 1.1.0 (2026-08-17), resources/boost/skills/: the four skill names it ships.
# Source: https://github.com/spatie/guidelines-skills/tree/1.1.0/resources/boost/skills
SPATIE_SKILLS = {"spatie-laravel-php", "spatie-javascript", "spatie-version-control", "spatie-security"}

DEAD_CODE = "shipmonk/dead-code-detector"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def line_with(test: unittest.TestCase, text: str, *patterns: str, label: str) -> str:
    for line in text.splitlines():
        if all(re.search(p, line, I) for p in patterns):
            return line
    test.fail(f"no single paragraph or bullet states: {label}")


def section_matching(markdown: str, pattern: str) -> str:
    """The body of the first section (any level) whose title matches."""
    for _, title, body in sections(markdown):
        if re.search(pattern, title, I):
            return body
    return ""


def tracked(prefix: str) -> list:
    try:
        out = subprocess.run(["git", "ls-files", prefix], cwd=REPO, capture_output=True, text=True, check=True).stdout
        return [l for l in out.splitlines() if l]
    except (OSError, subprocess.CalledProcessError):
        return [str(p.relative_to(REPO)) for p in (REPO / prefix).rglob("*") if p.is_file()]


class Readme(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = read(README)

    # Owner ruling: skills.sh as a second channel next to Composer and Boost
    def test_skills_sh_install_is_documented(self):
        body = section_matching(self.text, r"skills\.sh")
        self.assertTrue(body, "README has no section whose heading names skills.sh")
        self.assertIn("npx skills add michtio/laravel-claude-skills", body)

    # Owner ruling: coexistence with spatie/guidelines-skills under house_style false
    def test_spatie_coexistence_section(self):
        body = section_matching(self.text, r"spatie")
        self.assertTrue(body, "README has no section whose heading names Spatie")
        self.assertIn("spatie/guidelines-skills", body)
        self.assertRegex(body, r'"house_style":\s*false')
        self.assertIn("boost:install", body)

    # Row 15: boost.enforce_tests in a package
    def test_package_section_documents_enforce_tests(self):
        found = find(self.text, 3, r"testbench package")
        self.assertIsNotNone(found, "README has no level-3 Testbench package section")
        self.assertIn("enforce_tests", found[1])


class ProfileDocs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = read(PROFILE_DOCS)

    # Rows 41, 51: taking PHPStan over
    def test_taking_phpstan_over_deletes_the_setup_file_in_the_same_change(self):
        body = section_matching(self.text, r"^phpstan$")
        line_with(self, body, r"phpstan\.neon\.dist", r"delete", r"same (change|commit)",
                  label="to take PHPStan over, create phpstan.neon.dist and delete phpstan.neon in the same change")

    def test_the_shadow_rule_is_explained(self):
        body = section_matching(self.text, r"^phpstan$")
        line_with(self, body, r"shadow", r"phpstan\.neon\.dist", r"first",
                  label="PHPStan reads phpstan.neon first, so a leftover copy shadows phpstan.neon.dist")

    # Row 128: moving an existing suite to test_database ddev
    def test_moving_an_existing_suite_to_the_ddev_database(self):
        body = section_matching(self.text, r"test database")
        for needle in ("already exists", "Too many connections", "beforeApplicationDestroyed", "_test"):
            self.assertIn(needle, body, f"Test database section: `{needle}` is missing (moving an existing suite)")

    # Rows 12, 124, 127: the secret scan
    def test_secret_scan_section(self):
        body = section_matching(self.text, r"secret scan")
        self.assertTrue(body, "docs/profile.md has no section whose heading names the secret scan")
        self.assertIn(".ddev/web-build/Dockerfile.gitleaks", body)
        self.assertIn("ddev restart", body)
        line_with(self, body, r"histor", r"(fetch-depth|last commit|latest commit|one commit|HEAD)",
                  label="the local scan covers the git history, CI only the checked-out commit")
        line_with(self, body, r"\.gitleaksignore", r"fingerprint",
                  label="a historical false positive goes into .gitleaksignore by its fingerprint")

    # Row 16: suggested settings, never written
    def test_suggested_settings_are_documented(self):
        line_with(self, self.text, r"\.claude/settings\.json", r"(print|suggest)", r"never (write|writes|written)",
                  label="the setup prints suggested .claude/settings.json permissions and never writes the file")

    # Row 4: the boost.json seed
    def test_boost_json_seed_is_a_created_once_file(self):
        body = section_matching(self.text, r"files created once")
        self.assertIn("boost.json", body)
        self.assertIn('"cloud": false', body)


class ReadmesNeverCiteTests(unittest.TestCase):
    """R7 as amended 2026-11-27: user-facing docs describe behavior and never cite the pack's tests."""

    def user_docs(self) -> list:
        files = ["README.md", "CHANGELOG.md"] + [f for f in tracked("docs") if f.endswith(".md")] \
            + [f for f in tracked("resources/boost") if f.endswith(".md")]
        return [f for f in files if (REPO / f).is_file()]

    def test_no_user_doc_names_a_test_of_the_pack(self):
        tests = [t for t in tracked("tests") if re.search(r"(Test\.php|test_[a-z0-9_]+\.py)$", t)]
        self.assertTrue(tests, "no test files found to check against")
        self.assertTrue(self.user_docs(), "no user-facing docs found")
        hits = []
        for doc in self.user_docs():
            text = read(REPO / doc)
            for t in tests:
                if t in text or Path(t).name in text:
                    hits.append(f"{doc}: {t}")
        self.assertEqual(hits, [], "user-facing docs cite the pack's own tests")

    def test_an_example_test_path_of_a_consumer_project_still_passes(self):
        # Paired case: a path that is not a test of the pack (docs-claims shows a consumer's docblock) is allowed.
        tests = set(tracked("tests"))
        self.assertNotIn("tests/Feature/Payments/PaymentWebhookTest.php", tests)


class Coexistence(unittest.TestCase):
    """Owner ruling: the pack and spatie/guidelines-skills install side by side under house_style false."""

    def test_skill_names_do_not_collide(self):
        ours = {p.parent.name for p in SKILLS.glob("*/SKILL.md")}
        self.assertTrue(ours)
        self.assertEqual(ours & SPATIE_SKILLS, set())

    def test_house_style_off_leaves_no_rule_that_contradicts_spatie(self):
        text = read(CORE)
        m = re.search(r"@if \(\$houseStyle\)(.*?)@endif", text, re.S)
        self.assertIsNotNone(m, "the house style block is missing")
        outside = text.replace(m.group(0), "")
        for rule in ("PHPDocs on every", "@author", "========="):
            self.assertNotIn(rule, outside, f"with house_style false the guideline still says {rule!r}")


class Changelog(unittest.TestCase):
    def test_unreleased_names_the_new_setup_pieces(self):
        text = read(CHANGELOG)
        m = re.search(r"^## \[Unreleased\]\s*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
        self.assertIsNotNone(m, "CHANGELOG has no [Unreleased] section")
        for needle in ("Dockerfile.gitleaks", "boost.json", ".claude/settings.json", "BCRYPT_ROUNDS", "skills.sh", "consolidation"):
            self.assertIn(needle, m.group(1), f"CHANGELOG [Unreleased]: `{needle}` is missing")

    def test_no_em_dashes(self):
        for path in (README, PROFILE_DOCS, CHANGELOG):
            self.assertNotIn("—", read(path), f"{path.name} has an em dash")


class UnusedPublicCodeVerdict(unittest.TestCase):
    """Owner ruling: the unused-public-code check is chosen through the verdict register."""

    def row(self) -> list:
        for line in read(REGISTER).splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells and cells[0].strip("`") == DEAD_CODE:
                return cells
        return []

    def test_register_has_a_row_with_its_source(self):
        cells = self.row()
        self.assertTrue(cells, f"register.md has no row for {DEAD_CODE}")
        self.assertEqual(len(cells), 5)
        self.assertIn(cells[1], ("use", "depends"))
        self.assertIn("https://github.com/shipmonk-rnd/dead-code-detector", cells[2] + cells[3])
        self.assertIn("@api", cells[2] + cells[3], "a library marks its public API with @api so it is not reported")
        self.assertGreaterEqual(date.fromisoformat(cells[4]), date(2026, 11, 27))

    def test_the_pack_requires_it_for_development(self):
        self.assertIn(f'"{DEAD_CODE}"', read(COMPOSER))

    def test_ci_runs_it(self):
        text = read(CI_WORKFLOW)
        runs = [m.group(1) for m in re.finditer(r"(?m)^\s*run:\s*(.+)$", text)]
        configs = [m.group(1) for r in runs if "phpstan" in r for m in [re.search(r"(?:-c\s+|--configuration[ =])(\S+)", r)] if m]
        self.assertTrue(any("vendor/shipmonk/dead-code-detector/rules.neon" in read(REPO / c) for c in configs),
                        "ci.yml runs no vendor/bin/phpstan -c <config> whose config includes the dead-code rules")


if __name__ == "__main__":
    unittest.main()
