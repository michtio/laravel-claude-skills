"""Gate tests for slice S5 (laravel-layer): house style guideline and package-verdicts register.

Requirements R12, R13 (this slice's part), R3 via AC4, AC16 (the switch part).
Standard library only. Run: python3 -m unittest discover -s tests/gate
The integration class needs ddev and skips with a reason without it; it never runs php on the host.

Contracts the builder implements:

* Guideline: resources/boost/guidelines/core.blade.php. Installed into CLAUDE.md under
  the heading "House PHP style". It states the four rules (PHPDocs on every class and
  method; @author on classes and methods, never on properties; ========= section headers;
  declare(strict_types=1)) and names the skill `laravel-package-verdicts`.
* Switch: `.ai/skills-profile.json`, key `laravel.house_style` (boolean, default true).
  The shared schema leaves `laravel` an open object, so the key is pinned here, not by
  the schema. When false, `boost:update` leaves the "House PHP style" heading out.
* Register: resources/boost/skills/laravel-package-verdicts/ with SKILL.md (frontmatter
  name, description, when_to_use) and references/register.md. The table header is exactly
  `| Package | Use | Reason | Conditions | Checked |`; Use is use, avoid or depends;
  Checked is an ISO date; at least 5 rows. The register says profile verdicts, under the
  top-level `verdicts` key of `.ai/skills-profile.json` (the shared schema's key, "used by
  the Laravel pack"), take precedence over the register.
* Boost flags: `php artisan boost:install --guidelines --skills --mcp --no-interaction`
  (boost.json already lists claude_code and this package, written by
  scripts/make-fixture-app.sh) and `php artisan boost:update --no-discover --no-interaction`.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from datetime import date
from pathlib import Path

import ddev_lock

REPO = Path(__file__).resolve().parent.parent.parent
GUIDELINE = REPO / "resources/boost/guidelines/core.blade.php"
SKILL_DIR = REPO / "resources/boost/skills/laravel-package-verdicts"
REGISTER = SKILL_DIR / "references/register.md"
APP = REPO / "fixtures/app"
MARKER = "House PHP style"
HEADER = ["Package", "Use", "Reason", "Conditions", "Checked"]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def register_rows() -> tuple[list[str], list[list[str]]]:
    header: list[str] = []
    rows: list[list[str]] = []
    for line in read(REGISTER).splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
            continue
        if not header:
            header = cells
        else:
            rows.append(cells)
    return header, rows


class HouseStyleGuideline(unittest.TestCase):
    def setUp(self):
        self.text = read(GUIDELINE)

    def test_guideline_exists_with_marker_heading(self):
        self.assertTrue(GUIDELINE.is_file(), "resources/boost/guidelines/core.blade.php missing")
        self.assertIn(MARKER, self.text)

    def test_states_phpdocs_on_every_class_and_method(self):
        self.assertRegex(self.text, r"(?is)phpdoc.{0,80}(every|all).{0,40}(class|method)")

    def test_states_author_on_classes_and_methods_not_properties(self):
        self.assertIn("@author", self.text)
        self.assertRegex(self.text, r"(?is)@author.{0,200}propert")
        self.assertRegex(self.text, r"(?i)never.{0,40}propert|not.{0,40}propert")

    def test_states_section_headers(self):
        self.assertIn("=========", self.text)
        self.assertRegex(self.text, r"(?i)section header")

    def test_states_strict_types(self):
        self.assertIn("declare(strict_types=1)", self.text)

    def test_points_to_verdicts_skill(self):
        self.assertIn("laravel-package-verdicts", self.text)


class VerdictsRegister(unittest.TestCase):
    def test_skill_frontmatter(self):
        text = read(SKILL_DIR / "SKILL.md")
        self.assertTrue(text, "laravel-package-verdicts/SKILL.md missing")
        m = re.match(r"---\n(.*?)\n---\n", text, re.S)
        self.assertIsNotNone(m, "no frontmatter")
        fm = m.group(1)
        self.assertRegex(fm, r"(?m)^name: laravel-package-verdicts\s*$")
        self.assertRegex(fm, r"(?m)^description: \S")
        self.assertRegex(fm, r"(?m)^when_to_use: \S")

    def test_skill_links_register(self):
        self.assertIn("references/register.md", read(SKILL_DIR / "SKILL.md"))

    def test_register_header_is_exact(self):
        self.assertTrue(REGISTER.is_file(), "references/register.md missing")
        header, _ = register_rows()
        self.assertEqual(header, HEADER)

    def test_register_has_five_rows_with_valid_use_and_date(self):
        _, rows = register_rows()
        self.assertGreaterEqual(len(rows), 5)
        for row in rows:
            with self.subTest(package=row[0] if row else "?"):
                self.assertEqual(len(row), 5)
                self.assertRegex(row[0], r"\S")
                self.assertIn(row[1], ("use", "avoid", "depends"))
                self.assertRegex(row[2], r"\S")
                self.assertRegex(row[3], r"\S")
                self.assertRegex(row[4], r"^\d{4}-\d{2}-\d{2}$")
                date.fromisoformat(row[4])

    def test_register_states_profile_precedence(self):
        text = read(REGISTER)
        self.assertIn(".ai/skills-profile.json", text)
        self.assertIn("`verdicts`", text)
        self.assertRegex(text, r"(?i)precedence|take priority|override")
        self.assertRegex(text, r"(?i)profile")


@unittest.skipUnless(shutil.which("ddev"), "needs ddev: Boost runs inside the fixture app's DDEV project, never on the host")
class FixtureAppIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._ddev_lock = ddev_lock.acquire()
        cls.addClassCleanup(ddev_lock.release, cls._ddev_lock)
        if not (APP / ".ddev/config.yaml").is_file():
            r = subprocess.run(["bash", str(REPO / "scripts/make-fixture-app.sh")],
                               cwd=REPO, capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError("make-fixture-app.sh failed: " + (r.stdout + r.stderr)[-2000:])
        subprocess.run(["ddev", "config", "--project-name=lcs-fixture-app"], cwd=APP, capture_output=True, text=True)  # keep the project registered
        subprocess.run(["ddev", "start"], cwd=APP, capture_output=True, text=True)
        cls.profile = APP / ".ai/skills-profile.json"

    def boost(self, args: str):
        r = subprocess.run(["ddev", "exec", "bash", "-c", f"php artisan {args}"],
                           cwd=APP, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, f"artisan {args} failed:\n" + (r.stdout + r.stderr)[-2000:])

    def tearDown(self):
        if self.profile.exists():
            self.profile.unlink()

    def test_install_then_switch_off_then_update(self):
        claude = APP / "CLAUDE.md"
        skill = APP / ".claude/skills/laravel-package-verdicts"
        if self.profile.exists():
            self.profile.unlink()
        shutil.rmtree(skill, ignore_errors=True)

        self.boost("boost:install --guidelines --skills --mcp --no-interaction")
        self.assertIn(MARKER, read(claude), "house style missing from CLAUDE.md after boost:install")
        self.assertTrue((skill / "SKILL.md").is_file(), "laravel-package-verdicts skill not installed")
        self.assertTrue((skill / "references/register.md").is_file(), "register not installed")
        self.assertTrue((APP / ".claude/skills/laravel-pitfalls/SKILL.md").is_file())

        self.profile.parent.mkdir(parents=True, exist_ok=True)
        self.profile.write_text(json.dumps({"version": 1, "laravel": {"house_style": False}}), encoding="utf-8")
        self.boost("boost:update --no-discover --no-interaction")
        self.assertNotIn(MARKER, read(claude), "house_style false must remove the section on boost:update")
        self.assertTrue((skill / "SKILL.md").is_file(), "the register stays installed with house style off")


if __name__ == "__main__":
    unittest.main()
