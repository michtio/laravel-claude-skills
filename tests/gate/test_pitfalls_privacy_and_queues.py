"""Pitfalls: content tripwires on audit payloads, queued payloads that carry users or secrets, notification locale.

Requirements R1, R2, R5 (PII in logs and retention). Gaps rows 37, 57, 58, 104, 134 and 149.
Contract: tests/SkillContent/CONTRACT.md, section "Privacy and queues".
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from skill_content import pitfall  # noqa: E402


class ContentTripwires(unittest.TestCase):
    def test_a_content_check_is_a_tripwire_never_the_guarantee(self):
        # Row 37
        pitfall(self, 37, r"tripwire", r"(never|not) the guarantee", r"allowlist",
                label="a content check is a tripwire, never the guarantee; the allowlist is")
        pitfall(self, 37, r"every field", r"\bints?\b|integer",
                label="the tripwire checks every field, ints included")
        pitfall(self, 37, r"false positive", r"user agent", r"::",
                label="false positives (user agents, versions, ::) are tested")
        pitfall(self, 37, r"throw", r"(dev|local|testing)", r"(drop|redact)", r"production",
                label="throw in development, drop or redact in production, so an audit call never breaks the action")

    def test_every_exemption_has_a_paired_case(self):
        # Row 57
        pitfall(self, 57, r"exemption", r"paired", r"(must-still-be-caught|must still be caught)",
                label="every false-positive exemption has a paired must-still-be-caught case built from its own shape")
        pitfall(self, 57, r"dotted domain", r"@",
                label="require a dotted domain after @, never just a letter")

    def test_every_string_the_object_carries_is_checked(self):
        # Row 58
        pitfall(self, 58, r"every string", r"\bname\b", r"emitter",
                label="enumerate every string the object carries, name and emitter included")
        pitfall(self, 58, r"dropped", r"(position|key)", r"\blog",
                label="log only the position or key of a dropped value")


class QueuedPayloads(unittest.TestCase):
    def test_a_queued_listener_serializes_the_full_user(self):
        # Row 104
        pitfall(self, 104, r"queue", r"user", r"(password hash|remember token)",
                label="a queued listener on an event carrying the user serializes the password hash and remember token")
        pitfall(self, 104, r"(never queue|non-serializable|adapter)", r"listener",
                label="never queue listeners on such events, or wrap the user in a non-serializable adapter")

    def test_a_queued_secret_is_encrypted(self):
        # Row 149
        pitfall(self, 149, r"ShouldBeEncrypted", r"queue", r"(secret|token|code)",
                label="a queued job or notification that carries a secret implements ShouldBeEncrypted")
        pitfall(self, 149, r"failed_jobs", r"(hash|payload)",
                label="a hashes-only claim is checked against the queue payload and failed_jobs")
        pitfall(self, 149, r"SensitiveParameter",
                label="mark secret parameters #[\\SensitiveParameter]")

    def test_a_queued_notification_carries_its_locale(self):
        # Row 134
        pitfall(self, 134, r"queued notification", r"(->locale\(\)|locale\(\)|HasLocalePreference)", r"worker",
                label="a queued notification without its locale renders in the worker's locale")
        pitfall(self, 134, r"(NotificationFake|the fake)", r"locale", r"(record|read)",
                label="test the locale by reading the fake's recorded locale")


if __name__ == "__main__":
    unittest.main()
