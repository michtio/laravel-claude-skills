"""Gate test for slice S6b (laravel-layer): isolation, gate script, hooks, package skeleton.

Requirements R8 (rest), R9, R10. Acceptance criteria AC9, AC10, AC12. The Pest half
(tests/Setup/SetupIsolationTest.php) pins the files and rules; this file runs the result
for real. Standard library only. Run: python3 -m unittest discover -s tests/gate
Needs ddev; skips with a reason without it. Never runs php on the host.

Contract: see the header of tests/Setup/SetupIsolationTest.php. In short, after
`php artisan claude-skills:setup --yes` in a DDEV app:
  - phpunit.xml forces APP_ENV, CACHE_STORE, QUEUE_CONNECTION, MAIL_MAILER, SESSION_DRIVER,
    DB_URL, DB_CONNECTION, DB_DATABASE=<composer name slug>_test and every *_LIVE /
    *_LIVE_MODE key from .env / .env.example set to false, as <env ... force="true"/>;
  - .ddev/config.claude-skills.yaml has a post-start hook (service db) that creates that database;
  - composer.json scripts.test is the one gate command;
  - a Testbench package gets testbench.yaml `laravel: ./` plus bootstrap/ and storage/ so Boost
    reads the package's own .ai/guidelines (hand-verified with Boost 2.5 / Testbench 11).

Not covered here: "CI calls the same command" (the workflow is S7, AC32) and the Linux
container half of AC12 (run `docker run` against the same suite in CI).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
APP = REPO / "fixtures/app"
PACKAGE_FIXTURE = REPO / "tests/Fixtures/package"
TOUCHED = [
    ".env", "phpunit.xml", "phpunit.xml.dist", "composer.json", ".mcp.json", ".gitleaks.toml",
    ".ddev/config.claude-skills.yaml", ".ai/claude-skills-setup.json", ".ai/guidelines",
    ".githooks", "tests/Feature/ZzIsolationTest.php",
]


def slug(composer_name: str) -> str:
    tail = composer_name.split("/")[-1].lower()
    return re.sub(r"[^a-z0-9]+", "_", tail).strip("_") + "_test"


def plain(text: str) -> str:
    """Strip ANSI escape codes: Collision colours output even without a TTY inside `ddev exec`."""
    return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text)


def ddev(args: list[str], cwd: Path = REPO) -> subprocess.CompletedProcess:
    return subprocess.run(["ddev", *args], cwd=cwd, capture_output=True, text=True)


@unittest.skipUnless(shutil.which("ddev"), "needs ddev: the suite runs inside the fixture app's DDEV project, never on the host")
class AppIsolationInDdev(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (APP / ".ddev/config.yaml").is_file():
            r = subprocess.run(["bash", str(REPO / "scripts/make-fixture-app.sh")], cwd=REPO, capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError("make-fixture-app.sh failed: " + (r.stdout + r.stderr)[-2000:])
        # A clean app: the generated one may hold files no tracked script creates.
        r = subprocess.run(["bash", str(REPO / "scripts/make-fixture-app.sh"), "--force"], cwd=REPO, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError("make-fixture-app.sh --force failed: " + (r.stdout + r.stderr)[-2000:])
        ddev(["start"], APP)
        cls.saved: dict[str, bytes | None] = {}
        for rel in TOUCHED:
            p = APP / rel
            if p.is_file():
                cls.saved[rel] = p.read_bytes()
            elif p.is_dir():
                shutil.copytree(p, REPO / f"fixtures/.s6b-save-{rel.replace('/', '_')}", dirs_exist_ok=True)
                cls.saved[rel] = None
            else:
                cls.saved[rel] = b""  # absent
        cls.dbname = slug(json.loads((APP / "composer.json").read_text())["name"])

    @classmethod
    def tearDownClass(cls):
        for rel, content in cls.saved.items():
            p = APP / rel
            saved_dir = REPO / f"fixtures/.s6b-save-{rel.replace('/', '_')}"
            if p.is_dir():
                shutil.rmtree(p)
            elif p.is_file() or p.is_symlink():
                p.unlink()
            if content is None:
                shutil.copytree(saved_dir, p)
                shutil.rmtree(saved_dir)
            elif content:
                p.write_bytes(content)

    def sh(self, command: str, expect: int | None = 0) -> subprocess.CompletedProcess:
        r = subprocess.run(["ddev", "exec", "bash", "-c", command], cwd=APP, capture_output=True, text=True)
        if expect is not None:
            self.assertEqual(r.returncode, expect, f"`{command}` exited {r.returncode}:\n" + (r.stdout + r.stderr)[-3000:])
        return r

    def test_live_flag_is_off_and_suite_runs_on_its_own_database(self):
        env = APP / ".env"
        base = env.read_text() if env.is_file() else (APP / ".env.example").read_text()
        lines = [l for l in base.splitlines() if not re.match(r"(DB_CONNECTION|DB_HOST|DB_PORT|DB_DATABASE|DB_USERNAME|DB_PASSWORD|PAYMENTS_LIVE)=", l)]
        lines += ["DB_CONNECTION=mariadb", "DB_HOST=db", "DB_PORT=3306", "DB_DATABASE=db", "DB_USERNAME=db", "DB_PASSWORD=db", "PAYMENTS_LIVE=true"]
        env.write_text("\n".join(lines) + "\n")
        (APP / "tests/Feature").mkdir(parents=True, exist_ok=True)
        (APP / "tests/Feature/ZzIsolationTest.php").write_text(
            "<?php\n\nnamespace Tests\\Feature;\n\nuse Illuminate\\Support\\Facades\\DB;\nuse Tests\\TestCase;\n\n"
            "class ZzIsolationTest extends TestCase\n{\n"
            "    public function test_live_flag_is_off(): void\n    {\n"
            "        $this->assertFalse(filter_var(env('PAYMENTS_LIVE'), FILTER_VALIDATE_BOOLEAN));\n    }\n\n"
            "    public function test_own_database(): void\n    {\n"
            f"        $this->assertSame('{self.dbname}', DB::connection()->getDatabaseName());\n"
            "        $this->assertSame('testing', app()->environment());\n    }\n}\n"
        )

        self.sh("php artisan claude-skills:setup --yes")
        self.assertIn("create database if not exists " + self.dbname, (APP / ".ddev/config.claude-skills.yaml").read_text().lower())

        # The post-start hook creates the database on the next start (AC9: its own database).
        r = ddev(["restart"], APP)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = ddev(["mysql", "-e", "SHOW DATABASES"], APP)
        self.assertIn(self.dbname, plain(r.stdout), "post-start hook did not create the test database")

        # AC10: the flag is true in .env and off inside the tests.
        self.assertIn("PAYMENTS_LIVE=true", env.read_text())
        self.sh("php artisan test --filter=ZzIsolationTest")

        # AC9: one gate command, composer test, runs the same steps.
        composer = json.loads((APP / "composer.json").read_text())
        self.assertIn("scripts", composer)
        self.assertEqual(composer["scripts"]["test"][-1], "bash .githooks/gitleaks-check")
        self.sh("composer test")

        # AC9: Boost starts through the runner, and a rerun changes nothing.
        mcp = json.loads((APP / ".mcp.json").read_text())["mcpServers"]["laravel-boost"]
        self.assertEqual(mcp, {"command": "ddev", "args": ["exec", "php", "artisan", "boost:mcp"]})
        self.sh("php artisan claude-skills:setup --check")


@unittest.skipUnless(shutil.which("ddev"), "needs ddev: the package suite runs inside DDEV, never on the host")
class PackageGateInDdev(unittest.TestCase):
    """AC12 (macOS half) and the package-local skeleton.

    The package is a temp copy of tests/Fixtures/package under fixtures/, which the repo's
    DDEV project mounts, with this repo's vendor/ symlinked in (it has Testbench, Boost and
    Symfony YAML). testbench.yaml lists this package's provider so the setup command can run
    through `vendor/bin/testbench`; the setup must keep that entry.
    If package-local Boost cannot work this way, this test is the place that says so: the
    mechanism (testbench.yaml laravel: ./ with bootstrap/ and storage/) was verified by hand.
    """

    def setUp(self):
        self.name = f".s6b-pkg-{uuid.uuid4().hex[:8]}"
        self.pkg = REPO / "fixtures" / self.name
        shutil.copytree(PACKAGE_FIXTURE, self.pkg)
        (self.pkg / "vendor").symlink_to("../../vendor")
        (self.pkg / ".ddev").mkdir()
        (self.pkg / ".ddev/config.yaml").write_text("name: s6b-package\ntype: php\n")
        (self.pkg / "testbench.yaml").write_text(
            'laravel: "@testbench"\nproviders:\n  - Michtio\\LaravelClaudeSkills\\LaravelClaudeSkillsServiceProvider\n'
        )
        (self.pkg / "tests").mkdir()
        (self.pkg / "tests/SmokeTest.php").write_text(
            "<?php\n\nnamespace Example\\Package\\Tests;\n\nuse Orchestra\\Testbench\\TestCase;\n\n"
            "class SmokeTest extends TestCase\n{\n"
            "    public function test_forced_pins(): void\n    {\n"
            "        $this->assertSame('testing', app()->environment());\n"
            "        $this->assertSame('array', config('mail.default'));\n"
            "        $this->assertFalse(filter_var(env('PAYMENTS_LIVE'), FILTER_VALIDATE_BOOLEAN));\n    }\n}\n"
        )
        (self.pkg / ".env").write_text("PAYMENTS_LIVE=true\n")

    def tearDown(self):
        shutil.rmtree(self.pkg, ignore_errors=True)

    def sh(self, command: str, expect: int | None = 0) -> subprocess.CompletedProcess:
        r = subprocess.run(["ddev", "exec", "bash", "-c", f"cd fixtures/{self.name} && {command}"], cwd=REPO, capture_output=True, text=True)
        if expect is not None:
            self.assertEqual(r.returncode, expect, f"`{command}` exited {r.returncode}:\n" + (r.stdout + r.stderr)[-3000:])
        return r

    def test_gate_runs_the_package_suite_and_boost_reads_the_package_guidelines(self):
        self.sh("php vendor/bin/testbench claude-skills:setup --yes --path=.")

        composer = json.loads((self.pkg / "composer.json").read_text())
        self.assertEqual(composer["scripts"]["test"][0], "@php vendor/bin/testbench package:test")
        self.assertTrue((self.pkg / "phpunit.xml.dist").is_file())
        self.assertIn("MAIL_MAILER", (self.pkg / "phpunit.xml.dist").read_text())

        # AC12 / AC10 on a package: the gate command runs the package suite, the live flag is off.
        out = self.sh("composer test")  # exit code 0 asserted by sh()
        self.assertRegex(plain(out.stdout + out.stderr), r"Tests:\s+1 passed", "the package suite did not run")

        # Package-local skeleton: Boost renders this package's own guidelines, runner text included.
        self.sh("php vendor/bin/testbench boost:update --no-interaction")
        claude = (self.pkg / "CLAUDE.md").read_text()
        self.assertIn("ddev exec php vendor/bin/testbench", claude, "Boost did not read the package's .ai/guidelines")
        self.assertTrue((self.pkg / ".ai/guidelines/claude-skills-runner.md").is_file())

        self.sh("php vendor/bin/testbench claude-skills:setup --check --path=.")


if __name__ == "__main__":
    unittest.main()
