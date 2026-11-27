"""One lock for the shared fixture app's DDEV project (lcs-fixture-app).

Two gate runs started at the same time rebuild and restart the same project and collide
(container names already in use, a project directory deleted under the other run). Each test
class that touches the fixture app takes this lock in setUpClass and releases it as a class
cleanup, so a second run waits for the first instead of colliding with it. The lock is an
flock on a file in the system temp directory, so it dies with its process: a run killed by a
signal never leaves it held.
"""
from __future__ import annotations

import fcntl
import hashlib
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
LOCK = Path(tempfile.gettempdir()) / f"lcs-fixture-app-{hashlib.sha1(str(REPO).encode()).hexdigest()[:10]}.lock"


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
