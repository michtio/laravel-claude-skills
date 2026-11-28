"""Revoking a remember-me device: the corrected refusal rule and the opt-in middleware trace.

Builder tests (G3) for skills-gaps rows 178 and 179, which arrived after the S9d-2 gate was written.
Row 178 corrects row 170: a Login listener can refuse a remember-me sign-in by calling
logoutCurrentDevice() (SessionGuard::user() sets the user before it fires Login and returns the
property afterwards; logoutCurrentDevice() nulls it). Row 179: an opt-in middleware that records state
when it finds none is bypassed by one request on an uncovered route; the security lens traces it.
Requirements R1, R2, R5 (authorization parity), R15.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from skill_content import agent, files, first_line, line_in, pitfall, read  # noqa: E402


class LoginListenerRefusal(unittest.TestCase):
    def test_a_login_listener_refuses_a_revoked_device_with_logout_current_device(self):
        # Row 178
        pitfall(self, 178, r"Login. listener", r"logoutCurrentDevice\(\)", r"viaRemember\(\)", r"middleware", r"second line",
                label="refuse a revoked device in the Login listener with logoutCurrentDevice(), the middleware as the second line")

    def test_no_pitfall_claims_a_login_listener_cannot_refuse(self):
        # Row 178: the false claim of row 170 never ships
        found = first_line(files("pitfalls"), (r"Login. listener", r"(cannot|can't) refuse"))
        self.assertIsNone(found, f"a pitfall still claims a Login listener cannot refuse: {found}")


class OptInMiddleware(unittest.TestCase):
    def test_the_pitfall_traces_an_uncovered_route_then_a_covered_one(self):
        # Row 179, pitfall half
        pitfall(self, 179, r"uncovered route", r"covered one", r"record when missing|records? state",
                label="trace an uncovered route first, then a covered one; a record-when-missing branch is fail-open")

    def test_the_security_lenses_trace_opt_in_middleware(self):
        # Row 179, agent half: the security checker and the deep reviewer
        for stem in ("laravel-review-checker", "laravel-reviewer-deep"):
            with self.subTest(agent=stem):
                line_in(self, agent(self, stem), r"opt-in", r"middleware", r"uncovered route", r"covered one",
                        r"fail-open",
                        label=f"{stem}: trace an uncovered route first, then a covered one, for any opt-in middleware")


if __name__ == "__main__":
    unittest.main()
