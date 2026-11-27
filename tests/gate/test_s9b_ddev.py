"""Gate test for slice S9b (laravel-layer): a fresh Testbench package, set up end to end on real MySQL.

Requirements R8, R10, R11, R23. Skills-gaps rows 3, 6, 8, 9, 10, 13, 16.
Contract: tests/S9b/CONTRACT.md section 9. Standard library only. Needs ddev (and docker for the
actionlint check); skips with a reason without them. Never runs php or composer on the host.

The package is tests/Fixtures/s9b-package: example/s9b-package, an empty src, no tests directory,
no CLAUDE.md, a profile with `test_database: ddev`, `ci: true` and `php_matrix: [8.3, 8.4]`. It
gets its own DDEV project (lcs-s9b-package, MySQL 8.0, PHP 8.4) in fixtures/.s9b-package, requiring
this package through a path repository, as scripts/make-fixture-app.sh does for the app. The run:

  1. `testbench claude-skills:setup --yes` exits 0: the DDEV hook and credentials, the forced
     <slug>_test pins, tests/Pest.php, CLAUDE.md (empty, no AGENTS.md), phpstan paths that exist,
     the matrix workflow with a MySQL service; the output lists the options and the agent step;
  2. after `ddev restart` the database s9b_package_test exists on the db service;
  3. a rerun says No changes and --check exits 0;
  4. `composer test` is green, and its Pest test asserts it runs on MySQL database s9b_package_test
     (not sqlite, not the dev database `db`);
  5. the profile's `test_pins: {"SESSION_DRIVER": "env", "QUEUE_CONNECTION": "env"}` lets a shell value
     through: a fixture test sees `config('session.driver')` as `file` and `config('queue.default')` as
     `database` under `ddev exec env SESSION_DRIVER=file QUEUE_CONNECTION=database ...`, and `array` and
     `sync` (the phpunit defaults) without them (row 7, round 1b). The queue case is the sharper one: on
     the base commit a forced pin also writes a `<server>` twin that beats the shell, while SESSION_DRIVER
     has no twin and already passes through, so only its unforced element is red there.

The DDEV project is deleted afterwards (`ddev delete -Oy`) and the directory removed, whatever
the result. The shared lock (ddev_lock) keeps two gate runs from colliding.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
import uuid
from pathlib import Path

import ddev_lock

REPO = Path(__file__).resolve().parent.parent.parent
FIXTURE = REPO / "tests/Fixtures/s9b-package"
PROJECT = "lcs-s9b-package"
DIR = REPO / "fixtures/.s9b-package"
DATABASE = "s9b_package_test"
IMAGE = "rhysd/actionlint:1.7.7"
WORKFLOW = ".github/workflows/claude-skills-gate.yml"
SETUP = ["php", "vendor/bin/testbench", "claude-skills:setup"]


def plain(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text)


def ddev(args: list, cwd: Path = DIR) -> subprocess.CompletedProcess:
    return subprocess.run(["ddev", *args], cwd=cwd, capture_output=True, text=True)


def tail(r: subprocess.CompletedProcess, n: int = 3000) -> str:
    return plain(r.stdout + r.stderr)[-n:]


@unittest.skipUnless(shutil.which("ddev"), "needs ddev: the package runs in its own DDEV project, never on the host")
class FreshPackageOnMysql(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._lock = ddev_lock.acquire()
        cls.addClassCleanup(ddev_lock.release, cls._lock)
        cls.addClassCleanup(cls.destroy)
        cls.destroy()
        shutil.copytree(FIXTURE, DIR)
        (DIR / ".ddev").mkdir()
        (DIR / ".ddev/config.yaml").write_text(f"name: {PROJECT}\ntype: php\n")
        (DIR / ".ddev/docker-compose.package.yaml").write_text("services:\n  web:\n    volumes:\n      - ../../..:/var/www/package:ro\n")
        for command in (
            ["config", f"--project-name={PROJECT}", "--project-type=php", "--php-version=8.4", "--docroot=.", "--database=mysql:8.0"],
            ["start"],
        ):
            r = ddev(command)
            if r.returncode != 0:
                raise RuntimeError(f"ddev {' '.join(command)} failed: " + tail(r))
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=DIR, check=True)
        r = ddev(["composer", "update", "--no-interaction", "--no-progress", "-W"])
        if r.returncode != 0:
            raise RuntimeError("composer update failed: " + tail(r))
        (DIR / "tests").mkdir(exist_ok=True)

    @classmethod
    def destroy(cls):
        if DIR.exists():
            ddev(["delete", "-Oy", PROJECT], cwd=DIR)
            shutil.rmtree(DIR, ignore_errors=True)

    def exec(self, command: list, expect: int | None = 0) -> subprocess.CompletedProcess:
        r = ddev(["exec", *command])
        if expect is not None:
            self.assertEqual(r.returncode, expect, f"`{' '.join(command)}` exited {r.returncode}:\n" + tail(r))
        return r

    def file(self, rel: str) -> str:
        return (DIR / rel).read_text()

    # 1
    def test_1_setup_gives_a_fresh_package_what_its_gate_needs(self):
        r = self.exec([*SETUP, "--yes"])
        out = plain(r.stdout)
        # Each group is its own sub-test, so one red reason does not hide the others.
        with self.subTest("the options and the agent step are printed (rows 13, 16)"):
            self.assertIn("Detected: package", out)
            self.assertRegex(out, r"(?m)^  test_database: ddev \(profile\)$")
            self.assertRegex(out, r"(?m)^  php_matrix: 8\.3, 8\.4 \(profile\)$")
            self.assertIn("/plugin install laravel-claude-skills@laravel-claude-skills", out)
        with self.subTest("CLAUDE.md exists before Boost, empty, and there is no AGENTS.md (row 3)"):
            self.assertTrue((DIR / "CLAUDE.md").is_file())
            self.assertEqual(self.file("CLAUDE.md").strip(), "")
            self.assertFalse((DIR / "AGENTS.md").exists())
        with self.subTest("tests/Pest.php (row 10)"):
            self.assertTrue((DIR / "tests/Pest.php").is_file())
            self.assertIn("Orchestra\\Testbench\\TestCase", self.file("tests/Pest.php"))
        with self.subTest("the DDEV database hook and credentials (row 6)"):
            hook = self.file(".ddev/config.claude-skills.yaml")
            self.assertIn(f"CREATE DATABASE IF NOT EXISTS {DATABASE}", hook)
            for line in ("DB_HOST=db", "DB_USERNAME=db", "DB_PASSWORD=db"):
                self.assertIn(line, hook)
        with self.subTest("the forced pins name MySQL and <slug>_test (row 6)"):
            phpunit = self.file("phpunit.xml.dist")
            self.assertIn('<env name="DB_CONNECTION" value="mysql" force="true"/>', phpunit)
            self.assertIn(f'<env name="DB_DATABASE" value="{DATABASE}" force="true"/>', phpunit)
        with self.subTest("phpstan paths all exist or are created in the run (row 9)"):
            neon = self.file("phpstan.neon")
            self.assertRegex(neon, r"(?m)^\s+- src$")
            self.assertRegex(neon, r"(?m)^\s+- tests$")
        with self.subTest("the matrix workflow with a MySQL service (rows 6, 8)"):
            workflow = self.file(WORKFLOW)
            self.assertRegex(workflow, r"['\"]8\.3['\"]")
            self.assertRegex(workflow, r"['\"]8\.4['\"]")
            self.assertIn("${{ matrix.php }}", workflow)
            self.assertRegex(workflow, r"MYSQL_DATABASE: ['\"]" + DATABASE + r"['\"]")

    # 2
    def test_2_the_hook_creates_the_database_on_restart(self):
        r = ddev(["restart"])
        self.assertEqual(r.returncode, 0, tail(r))
        r = ddev(["mysql", "-e", "SHOW DATABASES"])
        self.assertIn(DATABASE, plain(r.stdout), "the post-start hook did not create the test database")

    # 3
    def test_3_a_rerun_changes_nothing(self):
        r = self.exec([*SETUP, "--check"])
        self.assertIn("No changes", plain(r.stdout))

    # 4
    def test_4_composer_test_passes_against_the_real_database(self):
        shutil.copy(FIXTURE / "tests/DatabaseTest.php", DIR / "tests/DatabaseTest.php")
        r = self.exec(["composer", "test"], expect=None)
        out = plain(r.stdout + r.stderr)

        self.assertEqual(r.returncode, 0, "composer test failed on a fresh package:\n" + out[-3000:])
        self.assertIn("DatabaseTest", out)
        self.assertRegex(out, r"Tests:\s+\d+ passed")
        self.assertNotRegex(out, r"\d+ failed")
        # the dev database was never touched
        r = ddev(["mysql", "-e", "SHOW TABLES FROM db"])
        self.assertNotIn("s9b_probe", plain(r.stdout))

    # 5
    def test_5_the_state_is_still_clean_after_composer_test(self):
        r = self.exec([*SETUP, "--check"])
        self.assertIn("No changes", plain(r.stdout))


    # 6
    def test_6_an_env_pin_lets_the_shell_choose_the_session_driver(self):
        with self.subTest("the env pin is written without force, with the phpunit default"):
            self.assertIn('<env name="SESSION_DRIVER" value="array"/>', self.file("phpunit.xml.dist"))
        shutil.copy(FIXTURE / "tests/SessionDriverTest.php", DIR / "tests/SessionDriverTest.php")
        shell = self.exec(["env", "SESSION_DRIVER=file", "QUEUE_CONNECTION=database", "S9B_EXPECT_SESSION=file", "S9B_EXPECT_QUEUE=database", "vendor/bin/pest", "--filter=SessionDriver"], expect=None)
        with self.subTest("shell SESSION_DRIVER and QUEUE_CONNECTION reach the suite"):
            self.assertEqual(shell.returncode, 0, "shell values did not reach the suite:\n" + tail(shell))
            self.assertRegex(plain(shell.stdout), r"2 passed")
        default = self.exec(["vendor/bin/pest", "--filter=SessionDriver"], expect=None)
        with self.subTest("without the shell value the suite sees the phpunit default, array"):
            self.assertEqual(default.returncode, 0, "without the shell value the suite must see array:\n" + tail(default))
            self.assertRegex(plain(default.stdout), r"2 passed")


@unittest.skipUnless(shutil.which("ddev") and shutil.which("docker"), "needs ddev and docker")
class MatrixWorkflowPassesActionlint(unittest.TestCase):
    """The package matrix workflow with the MySQL service, on a copy of the plain package fixture."""

    def test_generated_workflow_passes_actionlint(self):
        name = ".lint-s9b-" + uuid.uuid4().hex[:8]
        project = REPO / name
        shutil.copytree(REPO / "tests/Fixtures/package", project)
        self.addCleanup(shutil.rmtree, project, True)
        (project / ".ddev").mkdir()
        (project / ".ddev/config.yaml").write_text("name: fixture\ntype: php\ndatabase:\n    type: mysql\n    version: \"8.0\"\n")
        (project / ".ai").mkdir(exist_ok=True)
        (project / ".ai/skills-profile.json").write_text(json.dumps({"version": 1, "laravel": {"ci": True, "test_database": "ddev", "php_matrix": ["8.3", "8.4", "8.5"]}}))

        run = subprocess.run(
            ["ddev", "exec", "vendor/bin/testbench", "claude-skills:setup", f"--path=/var/www/html/{name}", "--yes"],
            cwd=REPO, capture_output=True, text=True,
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertTrue((project / WORKFLOW).is_file(), "the setup wrote no workflow")
        text = (project / WORKFLOW).read_text()
        self.assertIn("matrix", text)
        self.assertIn("MYSQL_DATABASE", text)

        pull = subprocess.run(["docker", "pull", IMAGE], capture_output=True, text=True)
        if pull.returncode != 0:
            self.skipTest("cannot pull " + IMAGE + ": " + pull.stderr.strip()[-200:])
        lint = subprocess.run(
            ["docker", "run", "--rm", "-v", f"{project}:/repo", "-w", "/repo", IMAGE, "-color=false", WORKFLOW],
            capture_output=True, text=True,
        )
        self.assertEqual(lint.returncode, 0, lint.stdout + lint.stderr)


if __name__ == "__main__":
    unittest.main()
