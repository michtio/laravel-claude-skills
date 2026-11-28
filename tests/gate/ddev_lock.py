"""One lock for the shared fixture app's DDEV project (lcs-fixture-app).

Two gate runs started at the same time rebuild and restart the same project and collide
(container names already in use, a project directory deleted under the other run). Each test
class that touches the fixture app takes this lock in setUpClass and releases it as a class
cleanup, so a second run waits for the first instead of colliding with it. The lock is an
flock on a file in the system temp directory, so it dies with its process: a run killed by a
signal never leaves it held.

The DDEV projects carry the same checkout digest as the lock (FIXTURE_PROJECT, project()), so two
checkouts or worktrees never share a project, and start() fails loudly with the ddev output.
"""
from __future__ import annotations

import fcntl
import hashlib
import subprocess
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
DIGEST = hashlib.sha1(str(REPO).encode()).hexdigest()[:10]
LOCK = Path(tempfile.gettempdir()) / f"lcs-fixture-app-{DIGEST}.lock"
FIXTURE_PROJECT = f"lcs-fixture-app-{DIGEST}"


def project(base: str) -> str:
    """A DDEV project name for this checkout: `<base>-<digest>`."""
    return f"{base}-{DIGEST}"


def start(app: Path, name: str = FIXTURE_PROJECT) -> None:
    """Register the app under this checkout's project name and start it; RuntimeError with the ddev output
    when either command fails, so a DDEV failure is never reported later as an artisan failure. An app still
    registered under another name (the old machine-wide `lcs-fixture-app`) is unlisted first: DDEV refuses a
    second name for one project root."""
    config = Path(app) / ".ddev/config.yaml"
    old = next((l.split(":", 1)[1].strip() for l in config.read_text(encoding="utf-8").splitlines()
                if l.startswith("name:")), "") if config.is_file() else ""
    if old and old != name:
        subprocess.run(["ddev", "stop", "--unlist", old], cwd=app, capture_output=True, text=True)
    for args in (["config", f"--project-name={name}"], ["start"]):
        r = subprocess.run(["ddev", *args], cwd=app, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"ddev {' '.join(args)} failed in {app} (exit {r.returncode}):\n" + (r.stdout + r.stderr)[-3000:])


def acquire(timeout: float = 1800.0, poll: float = 1.0):
    """Take the lock, waiting up to `timeout` seconds; returns the open handle."""
    handle = open(LOCK, "a")
    deadline = time.monotonic() + timeout
    while True:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return handle
        except BlockingIOError:
            if time.monotonic() >= deadline:
                handle.close()
                raise TimeoutError(f"another gate run holds {LOCK}")
            time.sleep(poll)


def release(handle) -> None:
    try:
        fcntl.flock(handle, fcntl.LOCK_UN)
    finally:
        handle.close()
