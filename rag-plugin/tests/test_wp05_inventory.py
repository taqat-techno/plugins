"""WP-5 — the documented MCP inventory must match the live one.

Negative control
----------------
``TestBaselineEnvelopeIsRejected`` runs the same gate against
``tests/baseline_v0.17.0/rules/mcp-envelope.md`` and requires it to be
rejected. That file documented 21 of 30 tools, filed three unconditional core
tools under "optional", omitted the four shared-dependency tools, and called
``add_project`` an unresolved contradiction two releases after it shipped —
so a gate that accepts it is not a gate.

The drift check against real ragtools source is skipped when no checkout is
reachable, and the skip is asserted to be *visible*: ragtools itself shipped two
E2E suites that had never executed because a skip and a pass look identical from
outside.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _tree import PLUGIN_ROOT, is_baseline  # type: ignore[import-not-found]  # noqa: E402

sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from verify_tool_inventory import (  # type: ignore[import-not-found]  # noqa: E402
    InventoryFormatError,
    documented_tools,
    live_tools_from_source,
)

EXPECTED_TIERS = {
    "core": 6,
    "inspection": 5,
    "writes": 6,
    "dependencies": 4,
    "diagnostics": 9,
}

#: Where a ragtools checkout might be. First hit wins; absent -> visible skip.
_SOURCE_CANDIDATES = [
    Path(os.environ.get("RAGTOOLS_SOURCE", "")) if os.environ.get("RAGTOOLS_SOURCE") else None,
    Path(r"C:/MY-WorkSpace/rag/.claude/worktrees/v3.5.0"),
    Path(r"C:/MY-WorkSpace/rag"),
    Path.home() / "rag",
]


def _find_source() -> Path | None:
    for cand in _SOURCE_CANDIDATES:
        if cand and (cand / "src" / "ragtools" / "integration" / "mcp_server.py").is_file():
            return cand
    return None


class TestDocumentedInventoryShape(unittest.TestCase):
    """Self-check: the envelope parses and claims the tier shape it should."""

    def setUp(self):
        self.envelope = PLUGIN_ROOT / "rules" / "mcp-envelope.md"
        self.documented = documented_tools(self.envelope.read_text(encoding="utf-8"))

    def test_total_is_thirty(self):
        self.assertEqual(
            len(self.documented), 30,
            f"documented {len(self.documented)} tools; the live surface has 30",
        )

    def test_each_tier_has_the_expected_count(self):
        by_tier: dict[str, list[str]] = {}
        for name, tier in self.documented.items():
            by_tier.setdefault(tier, []).append(name)
        for tier, expected in EXPECTED_TIERS.items():
            self.assertEqual(
                len(by_tier.get(tier, [])), expected,
                f"tier {tier!r}: documented {len(by_tier.get(tier, []))}, expected {expected}",
            )

    def test_the_three_promoted_core_tools_are_in_core(self):
        """v0.17.0 filed these under an 'optional' Code Knowledge Index tier.
        They carry @mcp_app.tool() and no configuration can disable them."""
        for name in ("search_project_context", "find_definition", "secret_audit"):
            self.assertEqual(
                self.documented.get(name), "core",
                f"{name} is unconditional in ragtools but documented as "
                f"{self.documented.get(name)!r}",
            )

    def test_the_dependency_family_is_documented(self):
        for name in ("list_dependencies", "add_dependency",
                     "set_project_dependencies", "remove_dependency"):
            self.assertEqual(self.documented.get(name), "dependencies", f"{name} missing")

    def test_add_project_is_a_normal_write_with_stated_provenance(self):
        """v0.17.0 listed add_project as excluded-by-design and called its
        presence in the registry an unresolved contradiction. It is not one: it
        shipped deliberately in ragtools v2.5.1, superseding the v2.5.0
        changelog line the plugin was still comparing against.

        Asserted positively — on the provenance — rather than by banning the
        old phrase, because the corrected text legitimately quotes that phrase
        while explaining why it was wrong.
        """
        self.assertEqual(self.documented.get("add_project"), "writes")
        text = (PLUGIN_ROOT / "rules" / "mcp-envelope.md").read_text(encoding="utf-8")
        self.assertIn(
            "v2.5.1", text,
            "add_project's provenance is not stated; without it a future "
            "reader re-derives the contradiction narrative",
        )
        self.assertNotIn(
            "Do not treat its presence as permission", text,
            "the v0.17.0 prohibition on wiring add_project is still present",
        )


class TestErrorContractCompleteness(unittest.TestCase):
    """§3 is binding — it must name every code Claude can actually receive."""

    def setUp(self):
        self.text = (PLUGIN_ROOT / "rules" / "mcp-envelope.md").read_text(encoding="utf-8")

    def test_all_fourteen_mcp_codes_are_documented(self):
        for code in (
            "SERVICE_DOWN", "DEGRADED_MODE", "STARTUP_FAILED", "INVALID_ARG",
            "CONFIRM_TOKEN_MISMATCH", "SCOPE_UNRESOLVED", "CAPABILITY_DENIED",
            "UNAUTHORIZED", "COOLDOWN", "PROXY_CONNECT_FAILED",
            "PROXY_HTTP_4XX", "PROXY_HTTP_5XX", "BACKEND_ERROR", "UNKNOWN",
        ):
            self.assertIn(code, self.text, f"MCP error code {code} is undocumented")

    def test_the_http_domain_codes_are_documented(self):
        """These never enter the MCP enum — they arrive inside stringified
        prose, which is exactly why they need naming."""
        for code in ("UNKNOWN_PROJECT", "MIGRATION_IN_PROGRESS",
                     "STORAGE_UNAVAILABLE", "MODEL_UNAVAILABLE",
                     "OPERATION_CONFLICT", "MIGRATION_BLOCKED"):
            self.assertIn(code, self.text, f"HTTP domain code {code} is undocumented")

    def test_the_missing_cooldown_is_called_out(self):
        self.assertIn("set_project_mode", self.text)
        self.assertIn("NONE", self.text,
                      "set_project_mode's absent cooldown must be explicit — the "
                      "typed gate is its only rate limit")

    def test_client_profiles_are_not_claimed_to_isolate_retrieval(self):
        """A-04: the plugin does not sit in the request path and cannot
        mitigate proxy-mode scope enforcement, so it must never imply it does.
        """
        self.assertIn("A-04", self.text, "the A-04 dependency is not referenced")
        section = self.text.split("## 9.", 1)
        self.assertEqual(len(section), 2, "the client-profile section is missing")
        body = section[1]
        self.assertIn("does not enforce retrieval scope in proxy mode", body)
        self.assertIn("cannot", body, "the section must state the plugin cannot mitigate this")


class TestBaselineEnvelopeIsRejected(unittest.TestCase):
    def test_the_v0_17_0_envelope_does_not_pass_the_gate(self):
        baseline = PLUGIN_ROOT / "tests" / "baseline_v0.17.0" / "rules" / "mcp-envelope.md"
        if not baseline.is_file():
            self.skipTest("baseline snapshot missing")
        with self.assertRaises(
            InventoryFormatError,
            msg="the v0.17.0 envelope was accepted — the gate is not a gate",
        ):
            documented_tools(baseline.read_text(encoding="utf-8"))


class TestDriftAgainstRealSource(unittest.TestCase):
    def test_documented_equals_live(self):
        if is_baseline():
            self.skipTest("baseline tree: inventory is expected to differ")
        source = _find_source()
        if source is None:
            self.skipTest(
                "SKIPPED-VISIBLY: no ragtools checkout found; set RAGTOOLS_SOURCE "
                "to gate on real drift. This suite passing WITHOUT this test is "
                "not evidence the inventory is current."
            )
        live = live_tools_from_source(source)
        documented = set(documented_tools(
            (PLUGIN_ROOT / "rules" / "mcp-envelope.md").read_text(encoding="utf-8")
        ))
        self.assertEqual(
            live - documented, set(),
            f"live tools missing from the envelope: {sorted(live - documented)}",
        )
        self.assertEqual(
            documented - live, set(),
            f"envelope documents tools that are not live: {sorted(documented - live)}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
