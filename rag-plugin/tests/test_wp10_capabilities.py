"""WP-10 — capability gating must expire; a permanent gate is not a gate.

What this replaces
------------------
``rules/state-detection.md`` carried ``KNOWN_SAFE_FLOOR = None`` with the note
"no ragtools release is known-safe as of this writing". Every comparison against
``None`` evaluated to *not-yet-fixed*, so ``set_project_mode`` was permanently
blocked and every ``secret_audit`` answer carried a redaction caveat forever.

The redaction fix shipped in ragtools **v3.0.0** (``git describe --contains
7f0f4d3`` → ``v3.0.0-rc.1~8``): ``indexing/indexer.py:298`` defines
``apply_source_class_and_redaction`` and all three index paths call it. The gate
outlived its cause by five releases.

``TestTheOldGateNeverOpened`` reproduces the old comparison and asserts it
blocked every version — including ones that were fixed. That is the negative
control: a gate that says "no" to 3.5.1 is not protecting anyone.

The other half matters just as much: **unknown must fail closed while still
being distinguishable from a confirmed absence.** "Could not determine" and
"confirmed not present" lead a user to different actions.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _tree import PLUGIN_ROOT  # type: ignore[import-not-found]  # noqa: E402

sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from capability_probe import (  # type: ignore[import-not-found]  # noqa: E402
    ABSENT,
    PRESENT,
    REDACTION_FLOOR,
    UNKNOWN,
    Capability,
    CapabilityReport,
    gate,
    meets_floor,
    parse_version,
    probe_index_redaction,
)


class TestVersionParsing(unittest.TestCase):
    def test_plain_semver(self):
        self.assertEqual(parse_version("3.5.1"), (3, 5, 1))

    def test_prefixed_and_suffixed(self):
        self.assertEqual(parse_version("v3.5.1-rc.2"), (3, 5, 1))
        self.assertEqual(parse_version("ragtools 2.7.0 (packaged)"), (2, 7, 0))

    def test_unparseable_is_none_not_a_guess(self):
        for bad in ("", "unknown", "v3", "3.5", None):
            self.assertIsNone(parse_version(bad))  # type: ignore[arg-type]

    def test_none_version_never_meets_a_floor(self):
        self.assertIsNone(meets_floor(None, (3, 0, 0)))


class TestRedactionFloor(unittest.TestCase):
    """The one capability with no probe, and therefore a real floor."""

    def test_the_floor_is_the_release_that_shipped_the_fix(self):
        self.assertEqual(REDACTION_FLOOR, (3, 0, 0))

    def test_versions_below_the_floor_are_blocked(self):
        for v in ("2.5.0", "2.6.0", "2.7.0"):
            cap = probe_index_redaction(parse_version(v))
            self.assertEqual(cap.state, ABSENT, f"{v} should be blocked")
            self.assertFalse(cap.usable)

    def test_the_floor_release_itself_is_allowed(self):
        cap = probe_index_redaction((3, 0, 0))
        self.assertEqual(cap.state, PRESENT)
        self.assertTrue(cap.usable)

    def test_current_versions_are_allowed(self):
        for v in ("3.0.1", "3.4.0", "3.5.1", "4.0.0"):
            self.assertTrue(probe_index_redaction(parse_version(v)).usable, v)

    def test_an_unparseable_version_is_unknown_not_absent(self):
        """Fail closed, but say WHICH — a user who cannot determine their
        version takes a different action from one who is simply out of date."""
        cap = probe_index_redaction(None)
        self.assertEqual(cap.state, UNKNOWN)
        self.assertFalse(cap.usable, "unknown must not permit a gated write")
        self.assertIn("could not be", cap.describe())
        self.assertNotIn("not available", cap.describe())


class TestTheOldGateNeverOpened(unittest.TestCase):
    """Negative control: the v0.17.0 comparison, reproduced.

    Kept permanently, because the failure mode is subtle — the old code looked
    like a version check and behaved like an unconditional refusal.
    """

    @staticmethod
    def _old_status(version: str, known_safe_floor=None) -> str:
        """Verbatim logic from rules/state-detection.md @ v0.17.0."""
        parsed = parse_version(version)
        if parsed is None:
            return "unknown"
        if known_safe_floor is None:
            return "not-yet-fixed"
        return "fixed" if parsed >= known_safe_floor else "not-yet-fixed"

    def test_the_old_gate_blocked_every_version_including_fixed_ones(self):
        for v in ("2.7.0", "3.0.0", "3.4.0", "3.5.1", "9.9.9"):
            self.assertEqual(
                self._old_status(v), "not-yet-fixed",
                f"the old gate unexpectedly passed {v}; re-derive this control",
            )

    def test_the_new_gate_separates_them(self):
        self.assertFalse(probe_index_redaction(parse_version("2.7.0")).usable)
        self.assertTrue(probe_index_redaction(parse_version("3.5.1")).usable)

    def test_the_shipped_rule_no_longer_carries_the_dead_constant(self):
        text = (PLUGIN_ROOT / "rules" / "state-detection.md").read_text(encoding="utf-8")
        self.assertIn(
            "KNOWN_SAFE_FLOOR", text,
            "the constant's history should stay documented so it is not "
            "reintroduced",
        )
        self.assertIn("capability_probe", text,
                      "state-detection must point at the replacement")
        self.assertIn("3.0.0", text, "the real floor must be stated")


class TestGateMessaging(unittest.TestCase):
    def _report(self, cap: Capability) -> CapabilityReport:
        r = CapabilityReport(version=(2, 7, 0))
        r.capabilities[cap.name] = cap
        return r

    def test_a_usable_capability_does_not_block(self):
        r = self._report(Capability("index_redaction", PRESENT, "version floor"))
        self.assertIsNone(gate(r, "index_redaction", "set_project_mode"))

    def test_a_blocked_capability_gives_a_specific_reason(self):
        """D-032 required refusal 'with a clear, specific reason — not a
        generic error'. The reason is what tells a user to upgrade."""
        r = self._report(Capability("index_redaction", ABSENT, "version floor",
                                    "< 3.0.0: the service indexing path does not redact"))
        msg = gate(r, "index_redaction", "set_project_mode")
        self.assertIsNotNone(msg)
        self.assertIn("set_project_mode", msg)  # type: ignore[arg-type]
        self.assertIn("3.0.0", msg)  # type: ignore[arg-type]

    def test_an_unprobed_capability_fails_closed(self):
        r = CapabilityReport(version=(3, 5, 1))
        self.assertIsNotNone(gate(r, "never_probed", "some action"))


class TestProbePreferenceIsDocumented(unittest.TestCase):
    def test_capabilities_with_probes_are_not_version_gated(self):
        """Probe where a probe exists; a floor only where none does. A probe
        measures the running service; a floor infers from a number."""
        text = (PLUGIN_ROOT / "scripts" / "capability_probe.py").read_text(encoding="utf-8")
        for name in ("probe_scope_mandatory", "probe_dependencies",
                     "probe_per_project_layout", "probe_path_doubling"):
            self.assertIn(name, text, f"{name} probe is missing")

    def test_only_redaction_keeps_a_floor(self):
        text = (PLUGIN_ROOT / "scripts" / "capability_probe.py").read_text(encoding="utf-8")
        self.assertIn("REDACTION_FLOOR", text)
        self.assertIn("No probe exists", text,
                      "the reason redaction stays version-gated must be stated")


if __name__ == "__main__":
    unittest.main(verbosity=2)
