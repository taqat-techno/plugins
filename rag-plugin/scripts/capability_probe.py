#!/usr/bin/env python3
"""Capability detection for ragtools (rag-plugin, WP-10).

What this replaces
------------------
``rules/state-detection.md`` used to carry one constant::

    KNOWN_SAFE_FLOOR = None   # "no ragtools release is known-safe as of this writing"

Every comparison against ``None`` evaluated to *not-yet-fixed*, so
``set_project_mode`` was **permanently** blocked and every ``secret_audit``
answer carried a redaction caveat forever. That was correct when written and
stopped being correct in ragtools **v3.0.0** — five releases before anyone
noticed. A gate with no expiry is a gate nobody can pass, and its warnings stop
being read.

The redaction fix is real: ``indexing/indexer.py:298`` defines
``apply_source_class_and_redaction`` as "the ONE authoritative indexing hygiene
step", and all three index paths call it — ``index_file`` (CLI, watcher,
rebuild), ``QdrantOwner._flush_window`` (service), and the framework import.
``git describe --contains 7f0f4d3`` → ``v3.0.0-rc.1~8``.

Design
------
**Probe where a probe exists; use a version floor only where none does.**
D-032's own reverse-if clause asked for exactly this: *"A future ragtools
release exposes a clean boolean capability flag (rather than requiring
version-string comparison) — adopt it in place of the version-floor
comparison."*

A probe measures the running service. A version floor infers from a number. One
of those can be wrong about the machine in front of you.

**Unknown is not False.** ``Capability.state`` distinguishes ``present`` /
``absent`` / ``unknown``, and gating treats ``unknown`` as absent (fail closed)
while *saying* which it was. "Could not determine" and "confirmed not present"
lead to different user actions.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional

__all__ = [
    "Capability",
    "CapabilityReport",
    "probe_all",
    "parse_version",
    "meets_floor",
    "PRESENT",
    "ABSENT",
    "UNKNOWN",
    "REDACTION_FLOOR",
]

PRESENT = "present"
ABSENT = "absent"
UNKNOWN = "unknown"

#: The one floor that survives, because no probe for it exists: a client cannot
#: observe whether the service redacts secret VALUES at index time without
#: indexing a secret, which is not an acceptable probe.
REDACTION_FLOOR = (3, 0, 0)

_TIMEOUT = 1.5


@dataclass(frozen=True)
class Capability:
    name: str
    state: str            # present | absent | unknown
    how: str              # "probe" | "version floor" | "probe failed"
    detail: str = ""

    @property
    def usable(self) -> bool:
        """Fail closed: only an affirmative ``present`` permits a gated action."""
        return self.state == PRESENT

    def describe(self) -> str:
        if self.state == PRESENT:
            return f"{self.name}: available ({self.how})"
        if self.state == ABSENT:
            return f"{self.name}: not available ({self.how}) — {self.detail}".rstrip(" —")
        return f"{self.name}: could not be determined ({self.how}) — {self.detail}".rstrip(" —")


@dataclass
class CapabilityReport:
    version: Optional[tuple[int, int, int]] = None
    capabilities: dict[str, Capability] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = {}

    def get(self, name: str) -> Capability:
        return self.capabilities.get(
            name, Capability(name, UNKNOWN, "not probed", "no probe was run")
        )

    def usable(self, name: str) -> bool:
        return self.get(name).usable

    def describe(self) -> str:
        v = ".".join(map(str, self.version)) if self.version else "unknown"
        lines = [f"ragtools version: {v}"]
        lines += [f"  {c.describe()}" for c in self.capabilities.values()]
        return "\n".join(lines)


def parse_version(raw: str) -> Optional[tuple[int, int, int]]:
    """``"3.5.1"`` / ``"v3.5.1-rc.2"`` -> ``(3, 5, 1)``. ``None`` if unparseable.

    Never guesses. An unparseable version means every version-floored capability
    is ``unknown``, which fails closed.
    """
    if not raw:
        return None
    import re

    m = re.search(r"(\d+)\.(\d+)\.(\d+)", str(raw))
    if not m:
        return None
    return tuple(int(g) for g in m.groups())  # type: ignore[return-value]


def meets_floor(version: Optional[tuple[int, int, int]],
                floor: tuple[int, int, int]) -> Optional[bool]:
    """``True`` / ``False`` / ``None`` when the version could not be parsed."""
    if version is None:
        return None
    return version >= floor


# --------------------------------------------------------------------------- #
# Probes                                                                       #
# --------------------------------------------------------------------------- #


def _request(url: str, timeout: float = _TIMEOUT) -> tuple[Optional[int], Optional[dict]]:
    """``(status, body_or_None)``. Status is None when the request never landed."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "rag-plugin-capprobe"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(raw)
            except ValueError:
                return resp.status, None
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8", errors="replace"))
        except (ValueError, OSError):
            return e.code, None
    except (urllib.error.URLError, OSError, TimeoutError, ValueError):
        return None, None


def probe_scope_mandatory(base_url: str) -> Capability:
    """Does an unscoped retrieval call get refused?

    The single most informative probe available, and it costs one request. A
    422 means ragtools ≥3.0.0 fail-closed scope; a 200 means the legacy
    unscoped-searches-everything behaviour.
    """
    status, body = _request(f"{base_url}/api/search?query=capability+probe&top_k=1")
    if status is None:
        return Capability("scope_mandatory", UNKNOWN, "probe failed",
                          "the service did not answer")
    if status == 422:
        code = ""
        if isinstance(body, dict):
            detail = body.get("detail")
            if isinstance(detail, dict):
                code = str(detail.get("error_code") or "")
        return Capability("scope_mandatory", PRESENT, "probe",
                          f"unscoped search refused ({code or '422'})")
    if status == 200:
        return Capability("scope_mandatory", ABSENT, "probe",
                          "unscoped search succeeded — legacy behaviour")
    return Capability("scope_mandatory", UNKNOWN, "probe",
                      f"unexpected status {status}")


def probe_dependencies(base_url: str) -> Capability:
    """Shared-dependency catalogue (ragtools 3.0.0+)."""
    status, _ = _request(f"{base_url}/api/dependencies")
    if status is None:
        return Capability("dependencies", UNKNOWN, "probe failed",
                          "the service did not answer")
    if status == 200:
        return Capability("dependencies", PRESENT, "probe", "/api/dependencies answered")
    if status == 404:
        return Capability("dependencies", ABSENT, "probe",
                          "no /api/dependencies on this version")
    return Capability("dependencies", UNKNOWN, "probe", f"unexpected status {status}")


def probe_per_project_layout(base_url: str) -> Capability:
    status, body = _request(f"{base_url}/health")
    if status != 200 or not isinstance(body, dict):
        return Capability("per_project_layout", UNKNOWN, "probe failed",
                          "/health did not answer")
    strategy = str(body.get("collection_strategy") or "")
    if strategy == "per_project":
        return Capability("per_project_layout", PRESENT, "probe", strategy)
    if strategy:
        return Capability("per_project_layout", ABSENT, "probe", f"layout is {strategy}")
    return Capability("per_project_layout", UNKNOWN, "probe",
                      "no collection_strategy in /health")


def probe_path_doubling(base_url: str, project: str) -> Capability:
    """Does the text formatter repeat the project id in cited paths? (A-02)

    ``present`` here means the DEFECT is present, so the plugin should apply its
    citation repair. Needs a project with at least one indexed chunk; without
    one the answer is honestly unknown.
    """
    # A multi-noun query, because the probe needs a hit and ragtools drops
    # anything under score_threshold=0.3. A single short token scores below it
    # in most corpora, which made this probe report "unknown" against a
    # perfectly healthy index.
    q = urllib.parse.urlencode({
        "query": "documentation overview configuration architecture",
        "project": project, "top_k": "1",
        "structured": "true", "compact": "true",
    })
    status, body = _request(f"{base_url}/api/search?{q}")
    if status != 200 or not isinstance(body, dict):
        return Capability("path_doubling", UNKNOWN, "probe failed",
                          f"scoped search against {project!r} did not answer")
    results = body.get("results") or []
    if not results:
        return Capability("path_doubling", UNKNOWN, "probe",
                          f"{project!r} returned no chunks to compare")
    stored = str((results[0] or {}).get("file_path") or "")
    context = str(body.get("context") or "")
    if not stored:
        return Capability("path_doubling", UNKNOWN, "probe", "no file_path in the result")
    first = stored.split("/")[0]
    if f"{first}/{first}/" in context:
        return Capability("path_doubling", PRESENT, "probe",
                          "text output repeats the project segment — apply the repair")
    return Capability("path_doubling", ABSENT, "probe",
                      "text output matches the stored path — repair not needed")


def probe_index_redaction(version: Optional[tuple[int, int, int]]) -> Capability:
    """Version floor. **No probe exists**, deliberately.

    Observing index-time redaction from outside would mean indexing a real
    secret and searching for it. That is not an acceptable diagnostic, so this
    is the one capability that stays version-gated.
    """
    ok = meets_floor(version, REDACTION_FLOOR)
    floor = ".".join(map(str, REDACTION_FLOOR))
    if ok is None:
        return Capability("index_redaction", UNKNOWN, "version floor",
                          f"version could not be parsed; floor is {floor}")
    if ok:
        return Capability("index_redaction", PRESENT, "version floor",
                          f"≥ {floor} (fix shipped in 3.0.0, commit 7f0f4d3)")
    return Capability("index_redaction", ABSENT, "version floor",
                      f"< {floor}: the service indexing path does not redact "
                      "secret values")


def probe_all(base_url: str, version_raw: str = "",
              sample_project: str = "") -> CapabilityReport:
    """Run every probe. Never raises; a failed probe becomes ``unknown``."""
    version = parse_version(version_raw)
    if version is None:
        _, health = _request(f"{base_url}/health")
        if isinstance(health, dict):
            version = parse_version(str(health.get("version") or ""))

    checks: list[Callable[[], Capability]] = [
        lambda: probe_scope_mandatory(base_url),
        lambda: probe_dependencies(base_url),
        lambda: probe_per_project_layout(base_url),
        lambda: probe_index_redaction(version),
    ]
    if sample_project:
        checks.append(lambda: probe_path_doubling(base_url, sample_project))

    report = CapabilityReport(version=version)
    for check in checks:
        try:
            cap = check()
        except Exception as exc:  # noqa: BLE001 — a probe must never break the caller
            cap = Capability("unknown-probe", UNKNOWN, "probe failed", str(exc))
        report.capabilities[cap.name] = cap
    return report


def gate(report: CapabilityReport, capability: str, action: str) -> Optional[str]:
    """``None`` when ``action`` may proceed, else the specific refusal text.

    Specific, never generic: D-032 required that a blocked ``set_project_mode``
    "refuse with a clear, specific reason — not a generic error", and the reason
    is what lets a user decide whether to upgrade.
    """
    cap = report.get(capability)
    if cap.usable:
        return None
    return (
        f"{action} is not available on this ragtools: {cap.describe()}. "
        "Upgrade ragtools, or perform the change from the admin panel."
    )


if __name__ == "__main__":  # pragma: no cover - manual smoke aid
    import argparse

    ap = argparse.ArgumentParser(description="Probe ragtools capabilities")
    ap.add_argument("--base-url", default="http://127.0.0.1:21420")
    ap.add_argument("--project", default="", help="a project with chunks, for the A-02 probe")
    args = ap.parse_args()

    rep = probe_all(args.base_url, sample_project=args.project)
    print(rep.describe())
    print()
    blocked = gate(rep, "index_redaction", "set_project_mode")
    print("set_project_mode:", blocked or "ALLOWED (typed confirmation still required)")
