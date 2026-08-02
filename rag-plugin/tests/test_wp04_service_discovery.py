"""WP-4 — pick the right ragtools service, on evidence, or ask.

The case this exists for
------------------------
Measured 2026-08-01, two ragtools services were live on one machine and **both
reported version 3.5.1**:

    :21420  installed  managed engine  24 projects  "27 collections (per_project)"
    :21455  source     embedded         2 projects  "2 collections (per_project)"  <- test fixture

The plugin hardcoded :21420 in four behavioural sites. A source install defaults
to :21421 (``config._default_service_port``), so a developer working on ragtools
itself was pointed at the wrong service by every probe.

``TestVersionIsNeverADiscriminator`` is the load-bearing one: it constructs two
candidates identical except for what actually ties them to the workspace, and
requires that the version never breaks the tie.

Everything here runs on synthetic candidates — no live service — so it keeps
testing the same thing on a machine with no ragtools installed.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _tree import PLUGIN_ROOT  # type: ignore[import-not-found]  # noqa: E402

sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from service_discover import (  # type: ignore[import-not-found]  # noqa: E402
    ENGINE_PORTS,
    MIN_MARGIN,
    MIN_SCORE,
    DiscoveryResult,
    ServiceCandidate,
    is_ragtools_health,
    open_ports,
    score_candidate,
)


def candidate(port: int, *, data_dir: str = "", collection: str = "5 collections",
              version: str = "3.5.1", degraded: bool = False,
              projects: list[dict] | None = None,
              install_mode: str = "source") -> ServiceCandidate:
    return ServiceCandidate(
        port=port,
        health={"status": "ready", "collection": collection, "version": version,
                "degraded": degraded, "issues": [] if not degraded else ["storage_unreachable"]},
        identity={"data_dir": data_dir, "install_mode": install_mode,
                  "bound_port": port, "version": version,
                  "storage": {"target": "/some/store"}},
        projects=projects or [],
    )


class TestVersionIsNeverADiscriminator(unittest.TestCase):
    """The measured failure: two services, same version, different knowledge."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name).resolve()
        self.workspace = root / "work" / "myrepo"
        self.workspace.mkdir(parents=True)
        self.installed_data = root / "AppData" / "Local" / "RAGTools" / "data"
        self.installed_data.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_the_service_registering_this_workspace_wins(self):
        real = candidate(21420, data_dir=str(self.installed_data),
                         collection="27 collections (per_project)",
                         projects=[{"id": "myrepo", "path": str(self.workspace)}])
        fixture = candidate(21455, data_dir=str(Path(self._tmp.name) / "checkout" / "data"),
                            collection="2 collections (per_project)",
                            projects=[{"id": "alpha", "path": "/nowhere/alpha"}])
        score_candidate(real, self.workspace)
        score_candidate(fixture, self.workspace)
        self.assertGreater(
            real.score, fixture.score,
            "the service that registers this workspace must outrank a fixture "
            "service of the same version",
        )
        self.assertGreaterEqual(real.score - fixture.score, MIN_MARGIN)

    def test_identical_versions_do_not_contribute(self):
        """Same everything except version -> identical scores."""
        a = candidate(21420, data_dir="/x/data", version="3.5.1")
        b = candidate(21421, data_dir="/x/data", version="2.7.0")
        score_candidate(a, self.workspace)
        score_candidate(b, self.workspace)
        self.assertEqual(a.score, b.score, "version leaked into scoring")

    def test_port_number_does_not_contribute(self):
        a = candidate(21420, data_dir="/x/data")
        b = candidate(21499, data_dir="/x/data")
        score_candidate(a, self.workspace)
        score_candidate(b, self.workspace)
        self.assertEqual(a.score, b.score, "port number leaked into scoring")

    def test_data_dir_covering_the_workspace_is_the_strongest_signal(self):
        inside = candidate(21421, data_dir=str(self.workspace / "data"))
        outside = candidate(21420, data_dir=str(self.installed_data))
        score_candidate(inside, self.workspace)
        score_candidate(outside, self.workspace)
        self.assertGreater(inside.score, outside.score)
        self.assertTrue(any("data_dir" in r for r in inside.reasons))


class TestSelfReportedInstallModeIsNotTrusted(unittest.TestCase):
    """A-09 — ``routes._install_mode()`` tests for 'site-packages' in
    ``ragtools.__file__``. A PyInstaller bundle has no such path, so a genuinely
    packaged install reports ``source``. Measured on the live :21420 service.
    """

    def test_a_packaged_data_dir_is_inferred_as_packaged(self):
        for data_dir in (
            r"C:\Users\x\AppData\Local\RAGTools\data",
            "/home/x/.local/share/RAGTools/data",
            "/Users/x/Library/Application Support/RAGTools/data",
        ):
            c = candidate(21420, data_dir=data_dir, install_mode="source")
            self.assertEqual(
                c.install_kind, "packaged",
                f"{data_dir} is a packaged data dir but was inferred "
                f"{c.install_kind!r}",
            )

    def test_a_checkout_data_dir_is_inferred_as_source(self):
        c = candidate(21421, data_dir="/home/x/code/rag/data", install_mode="packaged")
        self.assertEqual(c.install_kind, "source")

    def test_the_self_report_is_ignored_even_when_it_contradicts(self):
        c = candidate(21420, data_dir=r"C:\Users\x\AppData\Local\RAGTools\data",
                      install_mode="source")
        self.assertEqual(c.install_mode, "source")      # what it claims
        self.assertEqual(c.install_kind, "packaged")    # what is true

    def test_missing_data_dir_is_unknown_not_a_guess(self):
        self.assertEqual(candidate(21420, data_dir="").install_kind, "unknown")


class TestAmbiguityIsSurfaced(unittest.TestCase):
    def test_two_indistinguishable_services_are_ambiguous(self):
        a = candidate(21420, data_dir="/a/data")
        b = candidate(21421, data_dir="/b/data")
        for c in (a, b):
            score_candidate(c, Path("/unrelated"))
        self.assertEqual(a.score, b.score)
        ranked = sorted([a, b], key=lambda c: -c.score)
        ambiguous = not (ranked[0].score >= MIN_SCORE
                         and ranked[0].score - ranked[1].score >= MIN_MARGIN)
        self.assertTrue(ambiguous, "two tied candidates must not be silently separated")

    def test_result_describes_both_candidates_when_ambiguous(self):
        a, b = candidate(21420, data_dir="/a"), candidate(21421, data_dir="/b")
        result = DiscoveryResult(candidates=[a, b], ambiguous=True, reason="tied")
        text = result.describe()
        self.assertIn("21420", text)
        self.assertIn("21421", text)
        self.assertIn("ambiguous", text)


class TestImpersonationGuard(unittest.TestCase):
    """A 200 on the port is not proof the responder is ragtools."""

    def test_a_ragtools_health_body_is_recognised(self):
        self.assertTrue(is_ragtools_health(
            {"status": "ready", "collection": "markdown_kb", "version": "3.5.1"}))

    def test_a_foreign_200_is_rejected(self):
        for body in ({}, None, {"status": "ok"}, {"message": "hello"},
                     {"version": "3.5.1"}):
            self.assertFalse(is_ragtools_health(body),  # type: ignore[arg-type]
                             f"{body!r} was accepted as a ragtools service")

    def test_collection_alone_is_not_enough(self):
        self.assertFalse(is_ragtools_health({"collection": "x"}))


class TestScanRange(unittest.TestCase):
    def test_engine_ports_are_never_scanned(self):
        """21500/21501 are the managed Qdrant engine. They answer, they are not
        the service, and probing them is noise."""
        self.assertEqual(ENGINE_PORTS, {21500, 21501})
        found = open_ports(range(21500, 21502))
        self.assertEqual(found, [], "engine ports were included in a scan")

    def test_scanning_a_closed_range_is_fast_and_empty(self):
        self.assertEqual(open_ports(range(21470, 21476)), [])


class TestDegradedIsATieBreakNotAGate(unittest.TestCase):
    def test_a_degraded_service_still_scores(self):
        """Degraded means 'trust the results less', not 'this is not the
        service'. Excluding it would leave the user with nothing to diagnose."""
        c = candidate(21420, data_dir="/x", degraded=True)
        score_candidate(c, Path("/x"))
        self.assertGreater(c.score, 0)
        self.assertTrue(any("degraded" in r for r in c.reasons))


if __name__ == "__main__":
    unittest.main(verbosity=2)
