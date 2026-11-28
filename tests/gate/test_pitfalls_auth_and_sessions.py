"""Pitfalls: sign-in events, password confirmation, session keys, address lookups, derived secrets, passkeys.

Requirements R1, R2, R5 (authorization parity, edge validation). Gaps rows 38, 102, 105, 106, 145, 148,
150 and 170.
Contract: tests/SkillContent/CONTRACT.md, section "Auth and sessions".
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from skill_content import agent, files, first_line, line_in, pitfall  # noqa: E402


class SignInEvents(unittest.TestCase):
    def test_login_fires_for_remember_me_cookies(self):
        # Row 102
        pitfall(self, 102, r"`?Login`?", r"viaRemember\(\)", r"(remember|cookie)", r"(skip|return early|returns early|fresh sign-in)",
                label="Login also fires for a remember-me cookie; a fresh-sign-in listener skips viaRemember()")

    def test_a_remembered_sign_in_keeps_the_guest_session(self):
        # Row 150
        pitfall(self, 150, r"remember", r"guest session", r"(Login|clear)",
                label="a remember-cookie sign-in keeps the guest session's data; clear a member-bound value on every Login")
        pitfall(self, 150, r"second member", r"remember",
                label="test it with a second member's remember cookie on the stamped session")


class RevokingOneDevice(unittest.TestCase):
    def test_logout_cycles_the_remember_token_on_every_device(self):
        # Row 170
        pitfall(self, 170, r"logout\(\)", r"remember_token", r"(every device|all devices)",
                label="SessionGuard::logout() cycles the single remember_token, which kills remember-me on every device")
        pitfall(self, 170, r"logoutCurrentDevice\(\)", r"(does not|doesn't|never) cycle",
                label="logoutCurrentDevice() does not cycle the remember token")
        pitfall(self, 170, r"companion cookie", r"getRecallerName\(\)",
                label="per-device revocation needs its own binding: a companion cookie named after getRecallerName()")
        # Rows 170 and 178: SessionGuard::user() sets $this->user before it fires Login and returns the property after
        # (SessionGuard.php:195-205), and logoutCurrentDevice() nulls it (:702-721), so the listener can refuse.
        pitfall(self, 170, r"Login.{0,3} listener", r"viaRemember\(\)", r"logoutCurrentDevice\(\)", r"refuse",
                label="refuse a revoked device's remember-me sign-in in the Login listener: on viaRemember(), call logoutCurrentDevice()")
        pitfall(self, 170, r"middleware", r"second line", r"(opt-in|uncovered|every route)",
                label="keep the middleware as the second line: an opt-in middleware leaves uncovered routes open")
        claims = first_line(files("pitfalls"), (r"listener", r"(cannot|can't|can not|unable to) (refuse|veto|reject)"))
        self.assertIsNone(claims, f"a pitfall still says a Login listener cannot refuse a remember-me login: {claims}")
        pitfall(self, 170, r"viaRemember\(\)", r"getUser\(\)", r"failed recaller|stays true",
                label="tell the remember path apart with viaRemember() && getUser() === $event->user (viaRemember stays true after a failed recaller)")


class PasswordConfirmation(unittest.TestCase):
    def test_password_confirm_honours_the_global_timeout(self):
        # Row 105
        pitfall(self, 105, r"password\.confirm", r"password_timeout", r"(3 h|three hours|10800)",
                label="password.confirm honors auth.password_timeout (3 hours by default)")
        pitfall(self, 105, r"password_confirmed_at", r"(silenc|skip|for that long|not for)",
                label="setting auth.password_confirmed_at silences confirmation for the global timeout, not the caller's window")

    def test_a_framework_session_key_is_guarded_by_who_is_signed_in(self):
        # Row 145
        pitfall(self, 145, r"session key", r"(signed in|signed-in)", r"(writ|write)",
                label="guard the write of a framework session key by who is signed in")
        pitfall(self, 145, r"Login", r"(previous user|account switch|still hold)",
                label="during a Login event the guard may still hold the previous user")


class LookupsByAddress(unittest.TestCase):
    def test_collation_matches_a_different_address(self):
        # Row 148, pitfall half
        pitfall(self, 148, r"collation", r"(case|accent).{0,20}insensitive",
                label="MySQL's default collations are case- and accent-insensitive")
        pitfall(self, 148, r"stored address", r"(mail|send)",
                label="after a lookup by address, mail the stored address")
        pitfall(self, 148, r"(hash_equals|utf8mb4_bin|binary collation)", r"strict",
                label="compare strict identifiers in PHP with hash_equals or give the column a binary collation")

    def test_the_security_lens_checks_lookups_by_address(self):
        # Row 148, checker half
        line_in(self, agent(self, "laravel-review-checker"), r"stored address", r"collation",
                label="security lens: after a lookup by address, mail the stored address (collation matches others)")


class DerivedSecrets(unittest.TestCase):
    def test_a_secret_derived_from_app_key(self):
        # Row 38
        pitfall(self, 38, r"APP_KEY", r"HMAC", r"(label|domain.separat|prefix)",
                label="derive a secret from APP_KEY with HMAC and a fixed label")
        pitfall(self, 38, r"(length-prefix|length prefix|JSON-encode|json_encode)", r"collid|collision",
                label="length-prefix or JSON-encode the inputs, so a:b + c never collides with a + b:c")
        pitfall(self, 38, r"APP_PREVIOUS_KEYS", r"rotat",
                label="APP_PREVIOUS_KEYS rotation ignores the previous keys for a derived value")
        pitfall(self, 38, r"morph map", r"(chang|derived)",
                label="a changed morph map changes the derived value")


class Passkeys(unittest.TestCase):
    def test_laravel_passkeys_pre_release_facts(self):
        # Row 106, pitfall half
        pitfall(self, 106, r"PasskeyUser",
                label="laravel/passkeys actions need the PasskeyUser contract")
        pitfall(self, 106, r"Passkeys::userModel\(\)", r"(migration|foreign key|\bFK\b)",
                label="Passkeys::userModel() drives the migration's foreign key")
        pitfall(self, 106, r"counter", r"\b0\b", r"(synced|replay)",
                label="synced passkeys report counter 0, so the counter check cannot catch a replay")
        pitfall(self, 106, r"challenge", r"single.use", r"(consumer|your|the app)",
                label="laravel/passkeys stores no challenge; single use of the options is the consumer's job")
        # laravel/passkeys v0.3.0 (laravel/passkeys-server, src/Events/PasskeyVerified.php and PasskeyRegistered.php):
        # both events `use SerializesModels`, so a queued listener's payload holds the model's class and key only.
        claim = first_line(files("pitfalls"), (r"Passkey(Verified|Registered)", r"full user"))
        self.assertIsNone(claim, f"a pitfall says the passkey events carry the full user: {claim}")
        pitfall(self, 106, r"passkey", r"password\.confirm",
                label="its management routes use password.confirm")
        pitfall(self, 106, r"Passkey(Verified|Registered)", r"user model", r"SerializesModels",
                label="its events carry the user model with SerializesModels, so a queued listener carries only the class and key")


if __name__ == "__main__":
    unittest.main()
