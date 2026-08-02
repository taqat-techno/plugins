#!/usr/bin/env python3
"""Find the right ragtools service, and prove it is the right one (WP-4).

The problem
-----------
The plugin hardcoded ``127.0.0.1:21420`` in four behavioural sites and ~18
instructional ones. That port is the **packaged** default; ``config
._default_service_port()`` returns ``21421`` for a **source** install, which is
exactly the configuration a developer working on ragtools itself has.

Worse, both can run at once. Measured on 2026-08-01, two services were live and
**both reported version 3.5.1**:

    :21420   installed   managed engine    24 projects    "27 collections (per_project)"
    :21455   source      embedded          2 projects     "2 collections (per_project)"   <- test fixture

A heuristic that picks "the ragtools service" by finding a listener that answers
``/health`` would have had an even chance of selecting a four-chunk test fixture
as the user's knowledge base.

**Version is worth zero.** This is the same lesson ragtools learned at the
engine layer in v3.2.0, where two installations both shipped Qdrant 1.15.5 and
one adopted the other's store. ``service/identity.py`` states the rule for the
service layer: *a port number alone is never trusted*.

How selection works
-------------------
Evidence, weighted by how strongly it ties a service to THIS working directory:

    data_dir contains / equals the workspace      50   highest — which store it owns
    install_mode matches the context              25   source-in-a-checkout, else packaged
    a registered project path matches the cwd     15
    collection label                              10   the discriminator that actually differs
    executable path                                5
    healthy / not degraded                         5   tie-break only
    version                                        0   NEVER a discriminator
    port number                                    0   NEVER a discriminator

An explicit override short-circuits scoring entirely. A single candidate that
clears ``MIN_SCORE`` and leads the runner-up by ``MIN_MARGIN`` is selected;
anything else is reported as ambiguous so the caller can ask. Guessing between
two services means answering from the wrong knowledge base.

Portability
-----------
Discovery uses ``socket.connect_ex`` plus HTTP, which behave identically on
Windows, Linux and macOS — no listener-table parsing, no platform branch. The
OS-specific process lookup in :func:`owning_process` is for **diagnostics only**
and never gates selection.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

__all__ = [
    "ServiceCandidate",
    "DiscoveryResult",
    "discover",
    "score_candidate",
    "probe",
    "open_ports",
    "owning_process",
    "DEFAULT_SCAN_RANGE",
    "ENGINE_PORTS",
]

SCRIPT_VERSION = "1.0.0"

#: The service range. 21500/21501 are the managed Qdrant engine's HTTP/gRPC
#: ports — they answer, they are not the service, and probing them is noise.
DEFAULT_SCAN_RANGE = range(21400, 21500)
ENGINE_PORTS = {21500, 21501}

#: Tried first, so the common case costs one probe rather than a scan.
LIKELY_PORTS = (21420, 21421)

MIN_SCORE = 40
MIN_MARGIN = 15

_CONNECT_TIMEOUT = 0.08
_HTTP_TIMEOUT = 1.0


# --------------------------------------------------------------------------- #
# Probing                                                                      #
# --------------------------------------------------------------------------- #


def _norm(p: str) -> str:
    if not p:
        return ""
    try:
        out = str(Path(p).expanduser().resolve())
    except (OSError, ValueError):
        out = str(p)
    out = out.replace("\\", "/").rstrip("/")
    return out.lower() if os.name == "nt" else out


def _port_open(port: int, host: str = "127.0.0.1",
               timeout: float = _CONNECT_TIMEOUT) -> bool:
    """True if something is listening. Portable: no listener-table parsing."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            return sock.connect_ex((host, port)) == 0
    except OSError:
        return False


def open_ports(ports=DEFAULT_SCAN_RANGE, host: str = "127.0.0.1",
               max_workers: int = 32) -> list[int]:
    """Listening ports from ``ports``, engine ports excluded.

    A closed loopback port refuses immediately, so scanning a hundred of them
    concurrently costs milliseconds.
    """
    targets = [p for p in ports if p not in ENGINE_PORTS]
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        flags = pool.map(lambda p: _port_open(p, host), targets)
    return [p for p, is_open in zip(targets, flags) if is_open]


def _get_json(url: str, timeout: float = _HTTP_TIMEOUT) -> Optional[dict]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": f"rag-plugin-discover/{SCRIPT_VERSION}"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8", errors="replace"))
            return body if isinstance(body, dict) else None
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return None


def is_ragtools_health(body: Optional[dict]) -> bool:
    """Anti-impersonation marker.

    ragtools' own ``process._is_ragtools_health`` treats the presence of
    ``collection`` + ``status`` (+ ``version``) as proof the responder is
    ragtools. A 200 from something else on the port is NOT a ragtools service
    and must never be scored, let alone selected.
    """
    if not body:
        return False
    return "collection" in body and "status" in body


@dataclass
class ServiceCandidate:
    """One reachable, ragtools-shaped service."""

    port: int
    host: str = "127.0.0.1"
    health: dict[str, Any] = field(default_factory=dict)
    identity: dict[str, Any] = field(default_factory=dict)
    projects: list[dict[str, Any]] = field(default_factory=list)
    score: int = 0
    reasons: list[str] = field(default_factory=list)

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def bound_port(self) -> int:
        """The port the service says it bound, which can differ from the one
        that answered — the mismatch ``/identity`` exists to catch."""
        try:
            return int(self.identity.get("bound_port") or self.port)
        except (TypeError, ValueError):
            return self.port

    @property
    def data_dir(self) -> str:
        return str(self.identity.get("data_dir") or "")

    @property
    def install_mode(self) -> str:
        """The service's SELF-REPORTED install mode. **Do not score on this.**

        ``routes._install_mode()`` returns ``packaged`` only when
        ``"site-packages"`` appears in ``ragtools.__file__``. A PyInstaller
        bundle puts the package under ``_internal/``, so a genuinely packaged
        installation reports ``source``. Measured 2026-08-01: the installed
        service at :21420 — binary ``…/Programs/RAGTools/rag.exe`` — reported
        ``install_mode: "source"``.

        ``profile`` is unreliable in the opposite direction: it defaults to
        ``"installed"`` when ``RAG_PROFILE`` is unset, which is exactly how a
        developer runs from source. Neither self-report can be trusted alone;
        :attr:`install_kind` infers it from evidence instead. Tracked upstream
        as A-09.
        """
        return str(self.identity.get("install_mode") or "unknown")

    @property
    def install_kind(self) -> str:
        """``packaged`` | ``source`` | ``unknown``, inferred from ``data_dir``.

        A packaged install keeps its data under the platform application-data
        directory; a source checkout keeps it beside the code. That is a
        property of where the bytes actually are, not of a string the process
        computed about itself.
        """
        d = _norm(self.data_dir)
        if not d:
            return "unknown"
        markers = ("/appdata/local/ragtools", "/library/application support/ragtools",
                   "/.local/share/ragtools", "/programs/ragtools")
        if any(m in d for m in markers):
            return "packaged"
        if "/site-packages/" in d:
            return "packaged"
        return "source"

    @property
    def version(self) -> str:
        return str(self.health.get("version") or self.identity.get("version") or "")

    @property
    def collection(self) -> str:
        return str(self.health.get("collection") or "")

    @property
    def degraded(self) -> bool:
        return bool(self.health.get("degraded"))

    @property
    def issues(self) -> list[str]:
        got = self.health.get("issues")
        return [str(i) for i in got] if isinstance(got, list) else []

    def describe(self) -> str:
        bits = [f":{self.bound_port}", self.install_kind or "unknown"]
        if self.collection:
            bits.append(self.collection)
        if self.data_dir:
            bits.append(f"data_dir={self.data_dir}")
        bits.append("degraded" if self.degraded else "healthy")
        return " · ".join(bits)


def probe(port: int, host: str = "127.0.0.1",
          with_projects: bool = False) -> Optional[ServiceCandidate]:
    """Probe one port. ``None`` unless it answers as ragtools."""
    base = f"http://{host}:{port}"
    health = _get_json(f"{base}/health")
    if not is_ragtools_health(health):
        return None
    cand = ServiceCandidate(port=port, host=host, health=health or {})
    cand.identity = _get_json(f"{base}/identity") or {}
    if with_projects:
        body = _get_json(f"{base}/api/projects/configured")
        if isinstance(body, dict) and isinstance(body.get("projects"), list):
            cand.projects = [p for p in body["projects"] if isinstance(p, dict)]
    return cand


# --------------------------------------------------------------------------- #
# Scoring                                                                      #
# --------------------------------------------------------------------------- #


def score_candidate(cand: ServiceCandidate, workspace: Optional[Path] = None,
                    prefer_source: Optional[bool] = None) -> ServiceCandidate:
    """Score one candidate against the working directory. Mutates and returns it.

    ``prefer_source`` expresses the context: True inside a source checkout of
    ragtools itself, False otherwise. ``None`` means unknown, and contributes
    nothing rather than guessing.
    """
    score = 0
    reasons: list[str] = []
    ws = _norm(str(workspace)) if workspace else ""

    data_dir = _norm(cand.data_dir)
    if ws and data_dir:
        if data_dir == ws or ws.startswith(data_dir + "/") or data_dir.startswith(ws + "/"):
            score += 50
            reasons.append("data_dir covers the workspace (+50)")

    # Inferred from where the data actually lives — NOT from the service's
    # self-report. `install_mode` is inverted for PyInstaller bundles and
    # `profile` defaults to "installed" for source runs, so both self-reports
    # are wrong in opposite directions (A-09). Neither is scored.
    if prefer_source is not None and cand.install_kind in ("source", "packaged"):
        wanted = "source" if prefer_source else "packaged"
        if cand.install_kind == wanted:
            score += 20
            reasons.append(
                f"install_kind={cand.install_kind} (inferred from data_dir) "
                "matches the context (+20)"
            )

    if ws and cand.projects:
        for proj in cand.projects:
            ppath = _norm(str(proj.get("path") or ""))
            if not ppath:
                continue
            if ppath == ws or ws.startswith(ppath + "/") or ppath.startswith(ws + "/"):
                score += 15
                reasons.append(
                    f"registered project {proj.get('id')!r} matches the workspace (+15)"
                )
                break

    if cand.collection:
        score += 10
        reasons.append(f"reports a collection: {cand.collection} (+10)")

    exe = str(cand.identity.get("storage", {}).get("target") or "") if isinstance(
        cand.identity.get("storage"), dict) else ""
    if exe:
        score += 5
        reasons.append("declares a storage target (+5)")

    if not cand.degraded:
        score += 5
        reasons.append("healthy (+5)")
    else:
        reasons.append(f"degraded: {', '.join(cand.issues) or 'unspecified'} (+0)")

    # Deliberately absent: version and port. Two services reported 3.5.1 on the
    # same machine while serving completely different knowledge bases.
    cand.score = score
    cand.reasons = reasons
    return cand


@dataclass
class DiscoveryResult:
    selected: Optional[ServiceCandidate] = None
    candidates: list[ServiceCandidate] = field(default_factory=list)
    ambiguous: bool = False
    source: str = "none"           # override | probe | scan | none
    reason: str = ""

    @property
    def base_url(self) -> Optional[str]:
        return self.selected.base_url if self.selected else None

    def describe(self) -> str:
        if self.selected and not self.ambiguous:
            return f"{self.selected.describe()} ({self.source})"
        if self.ambiguous:
            return ("ambiguous: " +
                    " | ".join(c.describe() for c in self.candidates) +
                    " — name one")
        return f"no ragtools service found ({self.reason})"


def _override_port() -> Optional[int]:
    for var in ("RAG_PLUGIN_SERVICE_PORT", "RAG_SERVICE_PORT"):
        raw = os.environ.get(var, "").strip()
        if raw.isdigit():
            return int(raw)
    return None


def discover(workspace: Optional[Path] = None,
             prefer_source: Optional[bool] = None,
             host: str = "127.0.0.1",
             scan: bool = True,
             ports=DEFAULT_SCAN_RANGE) -> DiscoveryResult:
    """Find and select the ragtools service for ``workspace``.

    Order: explicit override → likely ports → bounded scan. Scoring only ever
    runs on responders that pass :func:`is_ragtools_health`.
    """
    forced = _override_port()
    if forced:
        cand = probe(forced, host, with_projects=True)
        if cand:
            score_candidate(cand, workspace, prefer_source)
            return DiscoveryResult(selected=cand, candidates=[cand], source="override",
                                   reason=f"RAG_SERVICE_PORT={forced}")
        return DiscoveryResult(source="override",
                               reason=f"port {forced} was named explicitly but did not "
                                      "answer as ragtools")

    found: list[ServiceCandidate] = []
    for port in LIKELY_PORTS:
        cand = probe(port, host, with_projects=True)
        if cand:
            found.append(cand)

    source = "probe"
    if not found and scan:
        source = "scan"
        for port in open_ports(ports, host):
            if port in LIKELY_PORTS:
                continue
            cand = probe(port, host, with_projects=True)
            if cand:
                found.append(cand)

    if not found:
        return DiscoveryResult(source="none",
                               reason="nothing on the loopback service range "
                                      "answered as ragtools")

    for cand in found:
        score_candidate(cand, workspace, prefer_source)
    found.sort(key=lambda c: -c.score)

    if len(found) == 1:
        return DiscoveryResult(selected=found[0], candidates=found, source=source,
                               reason="only one ragtools service is running")

    top, runner_up = found[0], found[1]
    if top.score >= MIN_SCORE and (top.score - runner_up.score) >= MIN_MARGIN:
        return DiscoveryResult(selected=top, candidates=found, source=source,
                               reason="; ".join(top.reasons))
    return DiscoveryResult(
        candidates=found, ambiguous=True, source=source,
        reason=(
            f"{len(found)} ragtools services are running and the evidence does not "
            f"separate them (top {top.score} vs {runner_up.score}); version is not a "
            "discriminator — ask which one to use"
        ),
    )


# --------------------------------------------------------------------------- #
# Diagnostics only — never gates selection                                     #
# --------------------------------------------------------------------------- #


def owning_process(port: int) -> dict[str, Any]:
    """Best-effort owner of a listening port, for `/doctor` output.

    Platform-specific by necessity, and deliberately quarantined here: selection
    never depends on it, so a platform whose command is missing degrades to an
    empty dict rather than an unselectable service.
    """
    try:
        if sys.platform == "win32":
            cmd = ["powershell", "-NoProfile", "-Command",
                   f"$c = Get-NetTCPConnection -State Listen -LocalPort {port} "
                   "-ErrorAction SilentlyContinue | Select-Object -First 1; "
                   "if ($c) { $p = Get-Process -Id $c.OwningProcess "
                   "-ErrorAction SilentlyContinue; "
                   "if ($p) { \"$($p.Id)|$($p.ProcessName)|$($p.Path)\" } }"]
        elif sys.platform == "darwin":
            cmd = ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-Fpcn"]
        else:
            cmd = ["ss", "-ltnp", f"sport = :{port}"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
        out = (r.stdout or "").strip()
        if not out:
            return {}
        if sys.platform == "win32" and "|" in out:
            pid, name, path = (out.split("|") + ["", ""])[:3]
            return {"pid": pid.strip(), "name": name.strip(), "path": path.strip()}
        return {"raw": out}
    except (OSError, subprocess.SubprocessError):
        return {}


if __name__ == "__main__":  # pragma: no cover - manual smoke aid
    import argparse

    ap = argparse.ArgumentParser(description="Discover and select a ragtools service")
    ap.add_argument("--workspace", default=os.getcwd())
    ap.add_argument("--prefer-source", action="store_true")
    ap.add_argument("--with-owner", action="store_true",
                    help="also show the owning process (diagnostics)")
    args = ap.parse_args()

    result = discover(Path(args.workspace),
                      prefer_source=True if args.prefer_source else None)
    print(f"workspace : {args.workspace}")
    print(f"decision  : {result.describe()}")
    print(f"reason    : {result.reason}")
    for c in result.candidates:
        marker = "->" if result.selected is c else "  "
        print(f" {marker} :{c.bound_port:<6} score={c.score:<4} v{c.version:<8} "
              f"{c.install_kind:<9} {c.collection}")
        if c.install_mode not in ("unknown", c.install_kind):
            print(f"        · note: service self-reports install_mode="
                  f"{c.install_mode!r} — unreliable, see A-09")
        for r in c.reasons:
            print(f"        · {r}")
        if args.with_owner:
            print(f"        · owner: {owning_process(c.port) or 'unknown'}")
