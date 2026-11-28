"""More call forms of the database-wiping artisan commands (R18; skills-gaps row 240, item 2).

Builder-added tests (G3), beside tests/gate/test_wiping_commands.py: `suite_guard.py wipers` also names
`Artisan::callSilently(...)`, Pest's `artisan(...)` function and a command with its options inside the string,
and does not flag a longer command that only starts with a wiping name. A file naming a wiping trait reports
the trait, as before. Standard library only.

    python3 -m unittest discover -s tests/gate -p 'test_wiping_command_forms.py'
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_wiping_commands import project, wipers  # noqa: E402


class MoreForms(unittest.TestCase):
    def test_more_call_forms_are_named(self):
        forms = {
            "Artisan::callSilently": ("Artisan::callSilently('db:wipe');", "db:wipe"),
            "Pest artisan() function": ("artisan('migrate:fresh');", "migrate:fresh"),
            "options inside the string": ("$this->artisan('migrate:refresh --seed');", "migrate:refresh"),
            "space after the parenthesis": ("Artisan::call( \"migrate:reset\" );", "migrate:reset"),
        }
        for label, (body, command) in forms.items():
            with self.subTest(form=label), tempfile.TemporaryDirectory() as raw:
                proc = wipers(project(Path(raw), body))
                self.assertEqual((proc.returncode, proc.stdout.strip()), (1, f"tests/Feature/NewTest.php: {command}"), proc.stderr)

    def test_a_longer_command_that_only_starts_with_a_wiping_name_is_not_flagged(self):
        for body in ("$this->artisan('migrate:freshen');", "Artisan::call('db:wipeout');", "$log->info('migrate:fresh');"):
            with self.subTest(body=body), tempfile.TemporaryDirectory() as raw:
                proc = wipers(project(Path(raw), body))
                self.assertEqual((proc.returncode, proc.stdout), (0, ""), proc.stderr)

    def test_a_wiping_trait_is_reported_before_a_wiping_command(self):
        with tempfile.TemporaryDirectory() as raw:
            proc = wipers(project(Path(raw), "uses(RefreshDatabase::class); $this->artisan('db:wipe');"))
            self.assertEqual((proc.returncode, proc.stdout.strip()), (1, "tests/Feature/NewTest.php: RefreshDatabase"))


if __name__ == "__main__":
    unittest.main()
