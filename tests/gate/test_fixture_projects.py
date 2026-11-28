"""The DDEV fixture projects belong to one checkout, and a failed `ddev start` fails loudly.

The fixture app's DDEV project was named `lcs-fixture-app` on every checkout while its lock
(tests/gate/ddev_lock.py) is keyed on the checkout path, so a second checkout or worktree re-registered the
same project at its own path and the first checkout's `ddev start` then failed. setUpClass ignored that exit
code, so the run showed only an opaque artisan failure later. Contract:

- **Per-checkout names:** each DDEV project the gate makes carries the checkout's digest, the first 10 hex
  characters of the sha1 of the checkout's real path, the same digest the lock file name uses:
  `lcs-fixture-app-<digest>` (`ddev_lock.FIXTURE_PROJECT`) and `lcs-s9b-package-<digest>` (the S9b package).
  `ddev_lock.project(<base>)` returns `<base>-<digest>`.
- **The fixture script:** scripts/make-fixture-app.sh, run from any checkout, seeds `.ddev/config.yaml` with
  `name: lcs-fixture-app-<digest of that checkout>`, passes `--project-name=` with that name, and `--force`
  deletes that project. It never names the bare `lcs-fixture-app`.
- **Loud start:** `ddev_lock.start(<app>)` registers the app under `FIXTURE_PROJECT` and starts it. When
  `ddev config` or `ddev start` exits nonzero it raises RuntimeError with the command and the ddev output.
  test_s5 FixtureAppIntegration and test_s6a RunnerGuidanceSurvivesBoostUpdate start the app with it, and
  test_s6b's `ensure_registered` uses `FIXTURE_PROJECT`. An app whose config still names another project (the
  old `lcs-fixture-app`) is unlisted under that name first (`ddev stop --unlist <old>`), since DDEV refuses a
  second name for one project root; only when `ddev describe -j <old>` places that project at this app
  (`raw.approot`), and a failed unlist is logged on stderr (review round 1, ruling 8).

A fake `ddev` on PATH records every call, so no test here needs DDEV or touches fixtures/. Standard library only.

    python3 -m unittest discover -s tests/gate -p 'test_fixture_projects.py'
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ddev_lock  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/make-fixture-app.sh"
MARKER = "FAKE-DDEV-START-BROKE-4417"
FAKE_DDEV = """#!/bin/sh
printf '%s\\n' "$*" >> "$FAKE_DDEV_LOG"
if [ "$1" = start ] && [ -n "${FAKE_DDEV_FAIL_START:-}" ]; then
    echo "$FAKE_DDEV_FAIL_START" >&2
    exit 1
fi
if [ "$1" = describe ]; then
    if [ -n "${FAKE_DDEV_DESCRIBE:-}" ]; then
        printf '%s\n' "$FAKE_DDEV_DESCRIBE"
    else
        printf '%s\n' '{"level":"fatal","msg":"could not find requested project"}'
    fi
fi
if [ "$1" = stop ] && [ -n "${FAKE_DDEV_FAIL_STOP:-}" ]; then
    echo "$FAKE_DDEV_FAIL_STOP" >&2
    exit 1
fi
exit 0
"""


def digest(path: Path) -> str:
    return hashlib.sha1(str(path.resolve()).encode()).hexdigest()[:10]


class FakeDdev:
    """A temp folder with a fake `ddev` first on PATH, for subprocesses and for code run in this process."""

    def __init__(self, fail_start: bool = False, describe: str | None = None, fail_stop: bool = False):
        self.fail_start = fail_start
        self.describe = describe
        self.fail_stop = fail_stop

    def __enter__(self) -> "FakeDdev":
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name).resolve()
        (self.tmp / "bin").mkdir()
        fake = self.tmp / "bin/ddev"
        fake.write_text(FAKE_DDEV, encoding="utf-8")
        fake.chmod(0o755)
        self.log = self.tmp / "ddev.log"
        self.log.write_text("", encoding="utf-8")
        values = {"PATH": f"{self.tmp / 'bin'}{os.pathsep}{os.environ.get('PATH', '')}", "FAKE_DDEV_LOG": str(self.log)}
        if self.fail_start:
            values["FAKE_DDEV_FAIL_START"] = MARKER
        if self.describe is not None:
            values["FAKE_DDEV_DESCRIBE"] = self.describe
        if self.fail_stop:
            values["FAKE_DDEV_FAIL_STOP"] = "FAKE-DDEV-STOP-BROKE"
        self._env = mock.patch.dict(os.environ, values)
        self._env.start()
        return self

    def __exit__(self, *exc) -> None:
        self._env.stop()
        self._tmp.cleanup()

    def calls(self) -> list:
        return [l.split() for l in self.log.read_text(encoding="utf-8").splitlines()]

    def app(self) -> Path:
        app = self.tmp / "app"
        (app / ".ddev").mkdir(parents=True)
        (app / ".ddev/config.yaml").write_text("name: x\ntype: laravel\n", encoding="utf-8")
        return app


class PerCheckoutNames(unittest.TestCase):
    def test_the_fixture_projects_carry_the_checkout_digest(self):
        self.assertEqual(ddev_lock.FIXTURE_PROJECT, f"lcs-fixture-app-{digest(REPO)}")
        self.assertEqual(ddev_lock.project("lcs-s9b-package"), f"lcs-s9b-package-{digest(REPO)}")
        self.assertIn(digest(REPO), ddev_lock.LOCK.name, "the lock and the projects share one digest")
        import test_s9b_ddev
        self.assertEqual(test_s9b_ddev.PROJECT, f"lcs-s9b-package-{digest(REPO)}")

    def test_make_fixture_app_names_the_project_after_its_own_checkout(self):
        with FakeDdev() as fake:
            checkout = fake.tmp / "checkout"
            (checkout / "scripts").mkdir(parents=True)
            shutil.copy2(SCRIPT, checkout / "scripts/make-fixture-app.sh")
            expected = f"lcs-fixture-app-{digest(checkout)}"
            run = subprocess.run(["bash", str(checkout / "scripts/make-fixture-app.sh")], cwd=checkout,
                                 capture_output=True, text=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            seed = (checkout / "fixtures/app/.ddev/config.yaml").read_text(encoding="utf-8")
            self.assertIn(f"name: {expected}\n", seed)
            configs = [c for c in fake.calls() if c and c[0] == "config"]
            self.assertTrue(configs, "make-fixture-app.sh ran no ddev config")
            self.assertTrue(all(f"--project-name={expected}" in c for c in configs), configs)

            fake.log.write_text("", encoding="utf-8")
            run = subprocess.run(["bash", str(checkout / "scripts/make-fixture-app.sh"), "--force"], cwd=checkout,
                                 capture_output=True, text=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            calls = fake.calls()
            self.assertTrue(any(c[0] == "delete" and expected in c for c in calls), calls)
            for call in calls:
                self.assertNotIn("lcs-fixture-app", call, f"bare project name in ddev {' '.join(call)}")
                self.assertNotIn("--project-name=lcs-fixture-app", call)


class LoudStart(unittest.TestCase):
    """setUpClass raises with the ddev output when `ddev start` fails, instead of failing later in artisan."""

    def run_setup(self, module, cls_name: str) -> str:
        cls = getattr(module, cls_name)
        handle = open(os.devnull, "a")
        with FakeDdev(fail_start=True) as fake, \
                mock.patch.object(module, "APP", fake.app()), \
                mock.patch.object(module.ddev_lock, "acquire", return_value=handle), \
                mock.patch.object(module.ddev_lock, "release", side_effect=lambda h: h.close()):
            try:
                with self.assertRaises(RuntimeError) as caught:
                    cls.setUpClass()
            finally:
                cls.doClassCleanups()
            self.assertIn(["start"], fake.calls())
        return str(caught.exception)

    def test_the_boost_integration_class_fails_loudly(self):
        import test_s5
        message = self.run_setup(test_s5, "FixtureAppIntegration")
        self.assertIn(MARKER, message)
        self.assertIn("ddev start", message)

    def test_the_runner_guidance_class_fails_loudly(self):
        import test_s6a
        message = self.run_setup(test_s6a, "RunnerGuidanceSurvivesBoostUpdate")
        self.assertIn(MARKER, message)
        self.assertIn("ddev start", message)

    def test_start_registers_the_per_checkout_project_and_raises_on_failure(self):
        with FakeDdev(fail_start=True) as fake:
            with self.assertRaises(RuntimeError) as caught:
                ddev_lock.start(fake.app())
            self.assertIn(MARKER, str(caught.exception))
            self.assertIn(["config", f"--project-name={ddev_lock.FIXTURE_PROJECT}"], fake.calls())

    def run_start(self, approot: str | None, fail_stop: bool = False, name: str = "lcs-fixture-app") -> tuple:
        """ddev_lock.start on an app whose config names `name`; `ddev describe -j` reports approot (None: unknown)."""
        import contextlib
        import io
        import json as json_module
        with tempfile.TemporaryDirectory() as raw:
            app_dir = Path(raw).resolve() / "app"
            describe = None if approot is None else json_module.dumps(
                {"level": "info", "raw": {"name": "lcs-fixture-app", "approot": approot.replace("<app>", str(app_dir))}})
            with FakeDdev(describe=describe, fail_stop=fail_stop) as fake:
                (app_dir / ".ddev").mkdir(parents=True)
                (app_dir / ".ddev/config.yaml").write_text(f"name: {name}\ntype: laravel\n", encoding="utf-8")
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    ddev_lock.start(app_dir)
                return fake.calls(), err.getvalue()

    def test_start_unlists_the_old_name_only_when_ddev_places_it_at_this_app(self):
        unlist = ["stop", "--unlist", "lcs-fixture-app"]
        tail = [["config", f"--project-name={ddev_lock.FIXTURE_PROJECT}"], ["start"]]
        for label, approot, expect_unlist in (("approot is this app", "<app>", True),
                                              ("approot is another checkout", "/elsewhere/fixtures/app", False),
                                              ("ddev does not know the project", None, False)):
            with self.subTest(case=label):
                calls, _ = self.run_start(approot)
                self.assertTrue(any(c[:1] == ["describe"] and "-j" in c and "lcs-fixture-app" in c for c in calls), calls)
                self.assertEqual(unlist in calls, expect_unlist, calls)
                self.assertEqual(calls[-2:], tail)
        calls, _ = self.run_start("<app>", name=ddev_lock.FIXTURE_PROJECT)
        self.assertEqual(calls, tail, "an app already under the per-checkout name is neither described nor unlisted")

    def test_a_failed_unlist_is_logged_and_the_start_goes_on(self):
        calls, err = self.run_start("<app>", fail_stop=True)
        self.assertIn(["stop", "--unlist", "lcs-fixture-app"], calls)
        self.assertIn("lcs-fixture-app", err)
        self.assertIn("unlist", err)
        self.assertEqual(calls[-1], ["start"])

    def test_s6b_registers_the_per_checkout_project(self):
        import test_s6b
        with FakeDdev() as fake:
            test_s6b.ensure_registered(fake.app())
            self.assertEqual(fake.calls(), [["config", f"--project-name={ddev_lock.FIXTURE_PROJECT}"]])


if __name__ == "__main__":
    unittest.main()
