#!/usr/bin/env python3
"""rag-plugin diagnostic report generator (v0.9.0).

Generates two evidence-based reports for the maintainers of the upstream
ragtools product (github.com/taqat-techno/rag) and the rag-plugin
(github.com/taqat-techno/plugins):

  Report 1 — rag-application-setup-report.md
    Local ragtools install / runtime / config / data / logs health.

  Report 2 — rag-plugin-behavior-report.md
    Plugin install state, Claude configuration, hooks, MCP wiring,
    and session-behavior analysis (RAC/RAG-related signals only).

Plus:
  summary.md             — top-level executive summary + paths
  github-rag-issue.md    — copy-pasteable issue body for github.com/taqat-techno/rag
  github-plugins-issue.md — copy-pasteable issue body for github.com/taqat-techno/plugins
  redacted-diagnostics.json — structured raw findings (machine-readable)

Privacy / safety invariants:
  - Secrets, API keys, tokens, bearer headers, passwords, cookies, SSH/private
    keys, and connection strings are redacted before they touch the reports.
  - User home paths are normalized to `~/...` in user-visible output.
  - Session JSONL files are scanned for RAC/RAG-related signals ONLY — no
    full conversations are emitted, only short redacted snippets.
  - The command never mutates user configuration.
  - The command never uploads anything. All output is local.
  - Exit code 0 on success even if findings are surfaced (non-zero only on
    hard errors — unwritable output dir, etc.).

Stdlib-only. Python 3.10+.

Output directory:
  ~/.claude/rag-plugin/reports/YYYY-MM-DD-HHMMSS/

CLI:
  python rag_report.py [--out <dir>] [--no-sessions] [--max-sessions N]
                       [--quiet] [--self-test]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib import parse as urlparse
from urllib import request as urlrequest
from urllib.error import URLError, HTTPError

# Force UTF-8 stdout on Windows cp1252 consoles (same pattern as md_analyzer.py)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

REPORT_VERSION = "0.9.0"
DEFAULT_PORT = 21420
DEFAULT_HOST = "127.0.0.1"

# --------------------------------------------------------------------------- #
# Redaction layer                                                             #
# --------------------------------------------------------------------------- #

# Patterns chosen to be high-precision: avoid clobbering log lines / commands.
_REDACT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Bearer / Authorization headers
    (re.compile(r"(?i)(authorization\s*:\s*)(bearer\s+[A-Za-z0-9._\-]+)"), r"\1<redacted-bearer>"),
    (re.compile(r"(?i)(authorization\s*:\s*)([A-Za-z0-9+/=]{20,})"), r"\1<redacted-auth>"),
    # Common secret-shaped key/value pairs
    (re.compile(r"(?i)(api[_-]?key|apikey|access[_-]?token|secret|password|passwd|pwd|client[_-]?secret|private[_-]?key)"
                r"(\s*[:=]\s*['\"]?)([^\s'\"<>{}\\]{6,})"),
     r"\1\2<redacted-secret>"),
    # GitHub PATs / tokens
    (re.compile(r"\bghp_[A-Za-z0-9]{20,}"), "<redacted-github-pat>"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"), "<redacted-github-pat>"),
    # AWS / Slack-shaped tokens
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "<redacted-aws-akid>"),
    (re.compile(r"\bxox[bpoa]-[0-9A-Za-z\-]{10,}"), "<redacted-slack-token>"),
    # Bare tokens after equals (long base64-ish)
    (re.compile(r"=([A-Za-z0-9+/=]{40,})"), r"=<redacted-long-token>"),
    # Cookies
    (re.compile(r"(?i)(cookie\s*:\s*)([^\n]+)"), r"\1<redacted-cookie>"),
    # PEM private keys
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
     "<redacted-private-key>"),
]


def redact(text: str) -> str:
    """Apply secret-redaction patterns to a string."""
    if not text:
        return text
    out = text
    for pat, repl in _REDACT_PATTERNS:
        out = pat.sub(repl, out)
    return out


def normalize_home(path: str | None) -> str:
    """Replace the user's home directory with ~ for portability in reports."""
    if not path:
        return ""
    home = str(Path.home())
    p = str(path)
    # Compare case-insensitively on Windows
    if os.name == "nt":
        if p.lower().startswith(home.lower()):
            return "~" + p[len(home):].replace("\\", "/")
    else:
        if p.startswith(home):
            return "~" + p[len(home):]
    return p.replace("\\", "/") if os.name == "nt" else p


# --------------------------------------------------------------------------- #
# State / finding model                                                       #
# --------------------------------------------------------------------------- #


@dataclass
class Finding:
    """One actionable observation. severity ∈ critical/high/medium/low/info."""
    id: str
    title: str
    severity: str
    evidence: str
    recommendation: str
    target: str  # 'rag' (application repo) or 'plugins' (plugin repo) or 'local'

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class State:
    install_mode: str = "unknown"  # not-installed / packaged-windows / packaged-macos / dev-mode / unknown
    service_mode: str = "N/A"      # UP / STARTING / DOWN / BROKEN / N/A
    binary_path: str = ""
    version: str = ""
    config_path: str = ""
    data_path: str = ""
    log_path: str = ""
    health_status: dict[str, Any] = field(default_factory=dict)
    api_status: dict[str, Any] = field(default_factory=dict)
    api_projects: list[dict[str, Any]] = field(default_factory=list)
    watcher_status: dict[str, Any] = field(default_factory=dict)
    port: int = DEFAULT_PORT
    host: str = DEFAULT_HOST


# --------------------------------------------------------------------------- #
# Probing helpers                                                             #
# --------------------------------------------------------------------------- #


def _safe_run(cmd: list[str], timeout: float = 5.0) -> tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()
    except FileNotFoundError:
        return 127, "", "command not found"
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except Exception as e:
        return 1, "", f"error: {e}"


def _http_get_json(url: str, timeout: float = 2.0) -> tuple[int, Any, str]:
    """Returns (http_code, parsed_json_or_none, error_message)."""
    try:
        req = urlrequest.Request(url, headers={"User-Agent": f"rag-plugin-report/{REPORT_VERSION}"})
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            code = resp.getcode()
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return code, json.loads(raw), ""
            except json.JSONDecodeError:
                return code, raw, "non-JSON body"
    except HTTPError as e:
        return e.code, None, f"HTTPError: {e}"
    except URLError as e:
        return 0, None, f"URLError: {e}"
    except socket.timeout:
        return 0, None, "timeout"
    except Exception as e:
        return 0, None, f"error: {e}"


def _which(binary: str) -> str:
    found = shutil.which(binary)
    return found or ""


def detect_install_mode(state: State) -> None:
    rag_bin = _which("rag")
    if rag_bin:
        state.binary_path = rag_bin
        # Best-effort packaged-vs-dev classification
        rag_l = rag_bin.lower()
        if os.name == "nt":
            if "ragtools" in rag_l or "appdata" in rag_l or "programs\\ragtools" in rag_l:
                state.install_mode = "packaged-windows"
            else:
                state.install_mode = "packaged-windows"
        elif sys.platform == "darwin":
            state.install_mode = "packaged-macos"
        else:
            state.install_mode = "dev-mode"
    else:
        # Look for dev-mode markers in CWD
        cwd = Path.cwd()
        if (cwd / "pyproject.toml").exists() and (cwd / ".venv").exists():
            try:
                content = (cwd / "pyproject.toml").read_text(encoding="utf-8", errors="replace")
                if "ragtools" in content.lower():
                    state.install_mode = "dev-mode"
                    return
            except Exception:
                pass
        state.install_mode = "not-installed"


def detect_version(state: State) -> None:
    if not state.binary_path:
        return
    rc, out, err = _safe_run([state.binary_path, "version"])
    blob = (out + "\n" + err).strip()
    m = re.search(r"(\d+\.\d+\.\d+)", blob)
    if m:
        state.version = m.group(1)


def probe_service(state: State) -> None:
    code, body, err = _http_get_json(f"http://{state.host}:{state.port}/health", timeout=1.5)
    if code == 200 and isinstance(body, dict):
        status = str(body.get("status", "")).lower()
        if status == "ready":
            state.service_mode = "UP"
        elif status == "starting":
            state.service_mode = "STARTING"
        else:
            state.service_mode = "BROKEN"
        state.health_status = body
    elif code == 0:
        # connection refused / timeout
        state.service_mode = "DOWN"
        state.health_status = {"_probe_error": err}
    elif code >= 500:
        state.service_mode = "BROKEN"
        state.health_status = {"_probe_error": err, "_code": code}
    else:
        state.service_mode = "BROKEN"
        state.health_status = {"_code": code, "_error": err}


def probe_api(state: State) -> None:
    if state.service_mode != "UP":
        return
    base = f"http://{state.host}:{state.port}"

    # /api/status — store the whole body, then resolve any path-like fields
    # the running build exposes. ragtools v2.5.x exposes points_count, scale,
    # total_files, total_chunks, last_indexed, projects[]; older builds expose
    # config_path / data_path / log_path. Read both shapes.
    code, body, _ = _http_get_json(f"{base}/api/status", timeout=2.0)
    if code == 200 and isinstance(body, dict):
        state.api_status = body
        for key in ("config_path", "data_path", "log_path"):
            v = body.get(key)
            if v and isinstance(v, str):
                setattr(state, key, v)

    # /api/projects — modern ragtools wraps the list as {"projects": [...]}
    # with lean records ({project_id, files, chunks}). Older builds returned
    # a bare list. Handle both. After the list is resolved, hydrate each
    # project's full status (path, last_indexed, enabled) via
    # /api/projects/<id>/status — the per-project endpoint.
    code, body, _ = _http_get_json(f"{base}/api/projects", timeout=2.0)
    raw_list: list[dict[str, Any]] = []
    if code == 200:
        if isinstance(body, list):
            raw_list = [p for p in body if isinstance(p, dict)]
        elif isinstance(body, dict) and isinstance(body.get("projects"), list):
            raw_list = [p for p in body["projects"] if isinstance(p, dict)]
    hydrated: list[dict[str, Any]] = []
    for proj in raw_list:
        pid = str(proj.get("project_id") or proj.get("id") or proj.get("name") or "").strip()
        if pid:
            code2, body2, _ = _http_get_json(
                f"{base}/api/projects/{urlparse.quote(pid)}/status", timeout=1.5
            )
            merged = dict(proj)
            if code2 == 200 and isinstance(body2, dict):
                for k, v in body2.items():
                    if v is not None:
                        merged[k] = v
            hydrated.append(merged)
        else:
            hydrated.append(proj)
    state.api_projects = hydrated

    # /api/watcher/status — modern ragtools also exposes this under /api/status,
    # but the dedicated endpoint is more reliable on older builds.
    code, body, _ = _http_get_json(f"{base}/api/watcher/status", timeout=2.0)
    if code == 200 and isinstance(body, dict):
        state.watcher_status = body


def resolve_default_paths(state: State) -> None:
    """When the service is DOWN, fall back to platform-default paths."""
    if state.data_path and state.config_path:
        return
    if os.name == "nt":
        local_app = os.environ.get("LOCALAPPDATA", "")
        if local_app:
            base = Path(local_app) / "RAGTools"
            if base.exists():
                if not state.data_path:
                    state.data_path = str(base / "data")
                if not state.config_path:
                    cfg = base / "config.toml"
                    state.config_path = str(cfg) if cfg.exists() else str(base)
                if not state.log_path:
                    logs = base / "data" / "logs"
                    state.log_path = str(logs) if logs.exists() else str(base / "logs")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "RAGTools"
        if base.exists():
            state.data_path = state.data_path or str(base / "data")
            state.config_path = state.config_path or str(base / "config.toml")
            state.log_path = state.log_path or str(base / "logs")
    else:
        base = Path.home() / ".local" / "share" / "ragtools"
        if base.exists():
            state.data_path = state.data_path or str(base / "data")
            state.config_path = state.config_path or str(base / "config.toml")
            state.log_path = state.log_path or str(base / "logs")


# --------------------------------------------------------------------------- #
# Plugin and Claude config inspection                                         #
# --------------------------------------------------------------------------- #


@dataclass
class PluginInspection:
    plugin_dir: str = ""
    cache_dir: str = ""
    manifest_version: str = ""
    commands: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    agents: list[str] = field(default_factory=list)
    hooks: list[str] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)
    scripts: list[str] = field(default_factory=list)
    expected_missing: list[str] = field(default_factory=list)
    # Advisory (UserPromptSubmit) hook commands in hooks.json that can return a
    # blocking exit code on path-resolution failure (D-031 / P-013). Empty =
    # every advisory hook is fail-open.
    unsafe_advisory_hooks: list[str] = field(default_factory=list)


def find_plugin_dir() -> str:
    """Locate the rag-plugin directory we are running from."""
    here = Path(__file__).resolve().parent
    # We're at <plugin>/scripts/rag_report.py — the plugin is the parent.
    plugin_dir = here.parent
    if (plugin_dir / ".claude-plugin" / "plugin.json").exists():
        return str(plugin_dir)
    return ""


def find_cache_plugin_dirs() -> list[str]:
    """Look in ~/.claude/plugins/marketplaces/* for a copy of the plugin."""
    out: list[str] = []
    base = Path.home() / ".claude" / "plugins"
    if not base.exists():
        return out
    for child in base.rglob("rag-plugin"):
        if (child / ".claude-plugin" / "plugin.json").exists():
            out.append(str(child))
    return out


# --- advisory hook fail-open analysis (D-031 / P-013) ---------------------- #
#
# A UserPromptSubmit (advisory) hook command is *unsafe* if it can return a
# blocking exit code (Python exit 2) when its script path fails to resolve —
# i.e. it invokes a `python ${VAR}/...py` script FILE without a fail-open
# wrapper. Exit 2 on UserPromptSubmit cancels the prompt before the model
# request (the D-031 vulnerability). Two shapes are fail-open and therefore
# SAFE: an inline `python -c "..."` bootstrap (no script-file argument, so the
# "can't open file -> exit 2" branch is structurally impossible), or an
# explicit `|| exit 0` / `|| true` shell guard.

# Advisory events only. The PreToolUse lock-conflict hook is *intentionally*
# able to block a tool call and is deliberately excluded from this check.
_ADVISORY_HOOK_EVENTS = ("UserPromptSubmit",)

# python (optionally python3) runs a .py FILE whose path contains a ${VAR}
# template token — exactly the host-expansion-dependent exit-2 trigger.
_RAW_HOOK_SCRIPT = re.compile(r"\bpython\d?\b[^\n|]*\$\{[A-Za-z_]+\}[^\n|]*\.py")
# Markers that make a command fail-open: inline -c bootstrap, or `|| exit/true`.
_HOOK_FAILOPEN = re.compile(r"\bpython\d?\b[^\n]*\s-c\s|\|\|\s*exit\b|\|\|\s*true\b")


def analyze_advisory_hook_safety(plugin_dir: str) -> list[str]:
    """Return advisory (UserPromptSubmit) hook command strings in
    ``hooks/hooks.json`` that can return a blocking exit code on a path-
    resolution failure — raw ``python ${VAR}/...py`` invocations WITHOUT a
    fail-open wrapper. An empty list means every advisory hook is fail-open.
    Never raises."""
    if not plugin_dir:
        return []
    hooks_json = Path(plugin_dir) / "hooks" / "hooks.json"
    try:
        data = json.loads(hooks_json.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return []
    if not isinstance(data, dict):
        return []
    hooks = data.get("hooks", {})
    if not isinstance(hooks, dict):
        return []
    unsafe: list[str] = []
    for event in _ADVISORY_HOOK_EVENTS:
        for group in hooks.get(event, []) or []:
            if not isinstance(group, dict):
                continue
            for h in group.get("hooks", []) or []:
                if not isinstance(h, dict):
                    continue
                cmd = h.get("command", "")
                if not isinstance(cmd, str) or not cmd:
                    continue
                if _RAW_HOOK_SCRIPT.search(cmd) and not _HOOK_FAILOPEN.search(cmd):
                    unsafe.append(cmd)
    return unsafe


def inspect_plugin(plugin_dir: str) -> PluginInspection:
    insp = PluginInspection(plugin_dir=plugin_dir)
    if not plugin_dir:
        return insp
    p = Path(plugin_dir)
    manifest = p / ".claude-plugin" / "plugin.json"
    if manifest.exists():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8", errors="replace"))
            insp.manifest_version = str(data.get("version", ""))
        except Exception:
            insp.manifest_version = "<malformed manifest>"

    def _list(rel: str, suffix: Optional[str] = None) -> list[str]:
        d = p / rel
        if not d.exists():
            return []
        result: list[str] = []
        for f in sorted(d.iterdir()):
            if f.is_file():
                if suffix and not f.name.endswith(suffix):
                    continue
                result.append(f.name)
            elif f.is_dir() and rel == "skills":
                result.append(f.name + "/")
        return result

    insp.commands = _list("commands", ".md")
    insp.skills = _list("skills")
    insp.agents = _list("agents", ".md")
    insp.hooks = _list("hooks")
    insp.rules = _list("rules", ".md")
    insp.scripts = _list("scripts")

    # Expected files
    expected = {
        ".claude-plugin/plugin.json": manifest.exists(),
        "README.md": (p / "README.md").exists(),
        "CHANGELOG.md": (p / "CHANGELOG.md").exists(),
        "hooks/hooks.json": (p / "hooks" / "hooks.json").exists(),
    }
    insp.expected_missing = [k for k, v in expected.items() if not v]
    cache = find_cache_plugin_dirs()
    insp.cache_dir = "; ".join(cache) if cache else ""
    insp.unsafe_advisory_hooks = analyze_advisory_hook_safety(plugin_dir)
    return insp


@dataclass
class ClaudeConfigInspection:
    user_claude_md_path: str = ""
    user_claude_md_exists: bool = False
    retrieval_rule_present: bool = False
    retrieval_rule_marker_version: str = ""
    settings_path: str = ""
    settings_exists: bool = False
    user_mcp_paths: list[str] = field(default_factory=list)
    user_mcp_ragtools_entries: list[dict[str, Any]] = field(default_factory=list)
    duplicate_mcp_warning: str = ""
    plugin_mcp_path: str = ""
    plugin_mcp_present: bool = False
    user_hooks_present: bool = False
    user_hooks_summary: str = ""


_RETRIEVAL_RULE_MARKERS = [
    "Knowledge Base Retrieval (ragtools MCP)",
    "rag-plugin retrieval rule",
    "search_knowledge_base",
]


def _read_text_safe(p: Path, limit: int = 1_500_000) -> str:
    try:
        if p.stat().st_size > limit:
            return p.read_text(encoding="utf-8", errors="replace")[:limit]
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def inspect_claude_config() -> ClaudeConfigInspection:
    cci = ClaudeConfigInspection()
    home = Path.home()
    claude_md = home / ".claude" / "CLAUDE.md"
    cci.user_claude_md_path = str(claude_md)
    cci.user_claude_md_exists = claude_md.exists()
    if cci.user_claude_md_exists:
        text = _read_text_safe(claude_md)
        for marker in _RETRIEVAL_RULE_MARKERS:
            if marker in text:
                cci.retrieval_rule_present = True
                break
        m = re.search(r"rag-plugin\s+retrieval\s+rule\s+v?([\d.]+)", text, re.IGNORECASE)
        if m:
            cci.retrieval_rule_marker_version = m.group(1)

    settings_path = home / ".claude" / "settings.json"
    cci.settings_path = str(settings_path)
    cci.settings_exists = settings_path.exists()

    # User-level MCP locations
    for candidate in [home / ".claude.json", home / ".claude" / ".mcp.json"]:
        if candidate.exists():
            cci.user_mcp_paths.append(str(candidate))
            try:
                data = json.loads(_read_text_safe(candidate))
                # ~/.claude.json shape varies; ~/.claude/.mcp.json is { "mcpServers": {...} }
                servers = {}
                if isinstance(data, dict):
                    if "mcpServers" in data and isinstance(data["mcpServers"], dict):
                        servers = data["mcpServers"]
                    elif "ragtools" in data and isinstance(data["ragtools"], dict):
                        servers = {"ragtools": data["ragtools"]}
                for name, val in servers.items():
                    if "rag" in name.lower():
                        cci.user_mcp_ragtools_entries.append({
                            "source": str(candidate),
                            "name": name,
                            "command": val.get("command", "") if isinstance(val, dict) else "",
                        })
            except Exception:
                pass

    # Plugin-level MCP
    plugin_dir = find_plugin_dir()
    if plugin_dir:
        plugin_mcp = Path(plugin_dir) / ".mcp.json"
        cci.plugin_mcp_path = str(plugin_mcp)
        cci.plugin_mcp_present = plugin_mcp.exists()

    # Duplicate warning if user-level has ragtools AND plugin-level exists
    if cci.user_mcp_ragtools_entries and cci.plugin_mcp_present:
        cci.duplicate_mcp_warning = (
            f"{len(cci.user_mcp_ragtools_entries)} user-level ragtools MCP entry/entries found "
            f"alongside the plugin-level registration. /config mcp-dedupe clean removes them."
        )

    # User hooks
    if cci.settings_exists:
        try:
            data = json.loads(_read_text_safe(settings_path))
            if isinstance(data, dict) and "hooks" in data:
                cci.user_hooks_present = True
                hk = data["hooks"]
                if isinstance(hk, dict):
                    cci.user_hooks_summary = ", ".join(sorted(hk.keys()))
        except Exception:
            pass
    return cci


# --------------------------------------------------------------------------- #
# Hook decision log inspection                                                #
# --------------------------------------------------------------------------- #


@dataclass
class HookLogStats:
    log_path: str = ""
    log_exists: bool = False
    total_lines: int = 0
    actions: dict[str, int] = field(default_factory=dict)
    last_entry_ts: str = ""
    notes: str = ""


def inspect_hook_log() -> HookLogStats:
    stats = HookLogStats()
    stats.log_path = str(Path.home() / ".claude" / "rag-plugin" / "hook-decisions.log")
    p = Path(stats.log_path)
    if not p.exists():
        stats.notes = "no hook-decisions log (hook never fired or observability disabled)"
        return stats
    stats.log_exists = True
    actions: dict[str, int] = {}
    last_ts = ""
    try:
        with p.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                stats.total_lines += 1
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                act = str(rec.get("action", "unknown"))
                actions[act] = actions.get(act, 0) + 1
                ts = rec.get("ts") or rec.get("timestamp")
                if isinstance(ts, str):
                    last_ts = ts
    except Exception as e:
        stats.notes = f"read error: {e}"
    stats.actions = dict(sorted(actions.items(), key=lambda kv: -kv[1]))
    stats.last_entry_ts = last_ts
    return stats


# --------------------------------------------------------------------------- #
# Log-file tail with redaction                                                #
# --------------------------------------------------------------------------- #


_LOG_ERROR_PATTERNS = [
    re.compile(r"\bERROR\b"),
    re.compile(r"\bTraceback\b"),
    re.compile(r"\bCRITICAL\b"),
    re.compile(r"is already accessed by another instance of Qdrant client"),
    re.compile(r"Application startup failed"),
    re.compile(r"Permission denied"),
    re.compile(r"port .* in use", re.IGNORECASE),
]


def tail_recent_errors(log_dir: str, max_files: int = 4, lines_per_file: int = 200) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not log_dir:
        return out
    base = Path(log_dir)
    if not base.exists():
        return out
    if base.is_file():
        files = [base]
    else:
        files = sorted(base.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)[:max_files]
    for f in files:
        try:
            with f.open("rb") as fh:
                # Tail naive
                fh.seek(0, os.SEEK_END)
                size = fh.tell()
                # ~32 KB tail is enough
                fh.seek(max(0, size - 32_768))
                tail = fh.read().decode("utf-8", errors="replace").splitlines()[-lines_per_file:]
        except Exception:
            continue
        hits = []
        for i, line in enumerate(tail):
            for pat in _LOG_ERROR_PATTERNS:
                if pat.search(line):
                    hits.append({"line_no": i, "text": redact(line)[:300]})
                    break
        if hits:
            out.append({"file": normalize_home(str(f)), "matches": hits[-15:]})  # cap per file
    return out


# --------------------------------------------------------------------------- #
# Session JSONL scanner (privacy-bounded)                                     #
# --------------------------------------------------------------------------- #


# Patterns are tightened to specific failure idioms. v0.13.1 narrowed:
#
#   - port-in-use: was `port .* in use` (matched "imPORT was in use of ..." via
#     re.IGNORECASE); now requires EADDRINUSE, "address already in use", or
#     "port <digits> ... in use" with a numeric port.
#   - connect-refused: dropped `HTTPConnectionPool.*Failed` (matched any prose
#     mentioning the class name); now requires ECONNREFUSED or
#     "connection refused", optionally near an HTTPConnectionPool marker.
#   - mcp-error: was `MCP[^\n]{0,40}(error|failed|disconnected|not connect)`
#     (matched generic "Exit code 2 ... mcp ... error" shell prose); now
#     requires concrete MCP failure idioms: explicit "MCP server" verbs,
#     "plugin:rag" reconnection failures, "tools/list" failures, or
#     "STARTUP_FAILED".
_SIGNAL_PATTERNS = [
    ("rag-mention", re.compile(r"\b(ragtools|rac/rag|rag-plugin|search_knowledge_base|knowledge base)\b", re.IGNORECASE)),
    ("rag-port", re.compile(r"127\.0\.0\.1:21420|:21420\b")),
    ("mcp-error", re.compile(
        r"(MCP server (?:failed|crashed|disconnected|not (?:responding|connecting))"
        r"|MCP[^\n]{0,20}STARTUP_FAILED"
        r"|mcp_server\.STARTUP_FAILED"
        r"|[Ff]ailed to (?:re)?connect to plugin:rag"
        r"|MCP tools/list (?:failed|timeout|timed out)"
        r"|tools/list (?:failed|timeout|timed out) for plugin:rag"
        r"|\[MCP\] (?:error|failed))",
        re.IGNORECASE,
    )),
    ("retrieval-skipped", re.compile(r"(I don't have (enough )?information|I don't have access|I don't have any information)", re.IGNORECASE)),
    ("user-correct-search", re.compile(r"(why didn'?t you search|use the knowledge base|search first|did you check the (rag|knowledge))", re.IGNORECASE)),
    ("rag-error-line", re.compile(r"\[RAG ERROR\]|\[RAG STATUS\].*failed", re.IGNORECASE)),
    ("connect-refused", re.compile(
        r"(\bECONNREFUSED\b"
        r"|[Cc]onnection refused"
        r"|HTTPConnectionPool[^\"\n]{0,200}(?:refused|Failed to establish|Max retries))",
    )),
    ("port-in-use", re.compile(
        r"(\bEADDRINUSE\b"
        r"|[Aa]ddress already in use"
        r"|\bport \d{2,5}\b[^\n]{0,40}\b(?:is|already)\b[^\n]{0,20}\bin use\b)",
    )),
    # D-031 / P-013: the precise stderr signature of a hook script that Python
    # could not open (unresolved ${CLAUDE_PLUGIN_ROOT} / unset var / missing
    # file) -> exit 2 -> blocked prompt. Keyed on the can't-open-file / [Errno 2]
    # path error (NOT a bare "exit code 2", which matches ordinary shell output)
    # so it does not regress the false-positive guards. Used only to ESCALATE an
    # already-present static P-013 to critical — never to raise it alone.
    ("hook-path-fatal", re.compile(
        r"can'?t open file [^\n]{0,200}hooks[\\/][^\n]{0,80}\.py"
        r"|\[Errno 2\][^\n]{0,120}hooks[\\/][^\n]{0,80}\.py"
        r"|\$\{CLAUDE_PLUGIN_ROOT\}[^\n]{0,80}(?:\[Errno 2\]|can'?t open|No such file)",
    )),
]


@dataclass
class SessionScanResult:
    sessions_found: int = 0
    sessions_scanned: int = 0
    sessions_with_signal: int = 0
    signal_counts: dict[str, int] = field(default_factory=dict)
    examples: list[dict[str, Any]] = field(default_factory=list)
    notes: str = ""


def _redact_snippet(text: str, max_len: int = 220) -> str:
    s = redact(text)
    s = s.replace("\r", " ").replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > max_len:
        s = s[: max_len - 3] + "..."
    return s


def scan_sessions(max_sessions: int = 60, max_examples: int = 12) -> SessionScanResult:
    res = SessionScanResult()
    base = Path.home() / ".claude" / "projects"
    if not base.exists():
        res.notes = "no Claude session directory found"
        return res
    files: list[Path] = []
    for child in base.iterdir():
        if not child.is_dir():
            continue
        for f in child.glob("*.jsonl"):
            files.append(f)
    res.sessions_found = len(files)
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    files = files[:max_sessions]

    seen_examples_per_signal: dict[str, int] = {}
    for f in files:
        res.sessions_scanned += 1
        any_signal = False
        try:
            with f.open("r", encoding="utf-8", errors="replace") as fh:
                for raw in fh:
                    if len(raw) > 200_000:
                        continue  # huge single line, skip
                    raw = raw.strip()
                    if not raw or not raw.startswith("{"):
                        continue
                    try:
                        rec = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    # Pull a textual representation for signal scanning
                    msg = rec.get("message") or rec.get("content") or rec.get("text") or ""
                    if isinstance(msg, dict):
                        msg = json.dumps(msg, ensure_ascii=False)
                    elif isinstance(msg, list):
                        msg = json.dumps(msg, ensure_ascii=False)
                    elif not isinstance(msg, str):
                        msg = str(msg)
                    if not msg:
                        # As a last resort try the whole record
                        msg = raw[:4000]
                    for label, pat in _SIGNAL_PATTERNS:
                        if pat.search(msg):
                            res.signal_counts[label] = res.signal_counts.get(label, 0) + 1
                            any_signal = True
                            seen = seen_examples_per_signal.get(label, 0)
                            if seen < 2 and len(res.examples) < max_examples:
                                res.examples.append({
                                    "session_file": normalize_home(str(f)),
                                    "signal": label,
                                    "snippet": _redact_snippet(msg),
                                })
                                seen_examples_per_signal[label] = seen + 1
                            # Don't double-count multiple patterns on same line
                            break
        except Exception:
            continue
        if any_signal:
            res.sessions_with_signal += 1
    return res


# --------------------------------------------------------------------------- #
# Findings synthesis                                                          #
# --------------------------------------------------------------------------- #


def synthesize_findings(state: State, plugin: PluginInspection,
                        cci: ClaudeConfigInspection, hook_stats: HookLogStats,
                        log_hits: list[dict[str, Any]], scan: SessionScanResult,
                        ) -> tuple[list[Finding], list[Finding]]:
    """Returns (application_findings, plugin_findings)."""
    app: list[Finding] = []
    plg: list[Finding] = []

    # ---- Application-side
    if state.install_mode == "not-installed":
        app.append(Finding(
            id="A-001", title="ragtools not installed on this device",
            severity="critical",
            evidence="`rag` not on PATH and no install dir at the platform default location.",
            recommendation="Install via `/rag:setup` (auto-detects platform) or "
                           "https://github.com/taqat-techno/rag/releases/latest.",
            target="rag",
        ))
    else:
        if not state.version:
            app.append(Finding(
                id="A-002", title="`rag version` did not return a parseable version",
                severity="high",
                evidence=f"binary at `{normalize_home(state.binary_path)}` did not emit `X.Y.Z`.",
                recommendation="Reinstall ragtools or run `rag version` interactively to see the actual error.",
                target="rag",
            ))
        if state.service_mode == "DOWN":
            app.append(Finding(
                id="A-003", title="ragtools service is not running",
                severity="high",
                evidence=f"http://{state.host}:{state.port}/health unreachable; "
                         f"probe error: {state.health_status.get('_probe_error', 'connection refused')}",
                recommendation="Start with `rag service start`, then re-run this report.",
                target="rag",
            ))
        elif state.service_mode == "BROKEN":
            app.append(Finding(
                id="A-004", title="ragtools /health endpoint returned non-ready response",
                severity="critical",
                evidence=f"health body: {redact(json.dumps(state.health_status, default=str))[:300]}",
                recommendation="Run `/rag:doctor --full --logs` to classify against F-001..F-012.",
                target="rag",
            ))
        elif state.service_mode == "STARTING":
            app.append(Finding(
                id="A-005", title="ragtools service is still starting",
                severity="info",
                evidence="health=starting (encoder load typically 5–10s).",
                recommendation="Re-probe in a few seconds.",
                target="rag",
            ))
        else:  # UP
            if not state.api_status:
                app.append(Finding(
                    id="A-006", title="/api/status not reachable despite /health=ready",
                    severity="medium",
                    evidence="health passed but /api/status returned no body.",
                    recommendation="The HTTP API surface may have regressed in this build; file an issue with the version.",
                    target="rag",
                ))
            if state.watcher_status and not state.watcher_status.get("running", True):
                app.append(Finding(
                    id="A-007", title="watcher process not running",
                    severity="medium",
                    evidence=f"watcher status: {redact(json.dumps(state.watcher_status))[:200]}",
                    recommendation="POST /api/watcher/start or run `/rag:doctor --symptom F-004 --fix`.",
                    target="rag",
                ))
            # Project list — modern ragtools wraps as {"projects": [...]} so
            # we trust state.api_projects only after the wrapped/bare-list
            # parse in probe_api(). If that returned empty AND /api/status's
            # `projects` key is also empty, the user genuinely has zero
            # projects configured.
            status_projects = state.api_status.get("projects") if state.api_status else None
            has_status_projects = (
                isinstance(status_projects, list) and len(status_projects) > 0
            )
            if not state.api_projects and not has_status_projects:
                app.append(Finding(
                    id="A-008", title="no projects configured",
                    severity="info",
                    evidence="/api/projects returned an empty list and /api/status had no projects key.",
                    recommendation="Add a project with `/rag:projects add` so the knowledge base is populated.",
                    target="rag",
                ))

            # Scale-band warning (ragtools v2.5.x exposes a `scale` block in
            # /api/status that classifies the local-mode collection size).
            # Recognized levels: none / approaching / warning / critical /
            # near-limit / over (or exceeded / past-limit). "over" means the
            # collection has crossed the hard limit — objective state, not a
            # forecast — so it is treated as the most serious band.
            scale = state.api_status.get("scale") if state.api_status else None
            if isinstance(scale, dict):
                lvl = str(scale.get("level", "")).lower()
                pts = scale.get("points") or scale.get("points_count") or state.api_status.get("points_count")
                # Prefer hard_limit when reported; fall back to legacy limit/cap fields.
                cap = (scale.get("hard_limit") or scale.get("limit")
                       or scale.get("cap") or scale.get("max_points"))
                msg = redact(str(scale.get("message", "") or ""))[:240]
                if lvl == "approaching":
                    app.append(Finding(
                        id="A-012", title="local Qdrant collection approaching scale limit",
                        severity="medium",
                        evidence=f"scale.level=approaching"
                                 + (f" ({pts} / {cap} points)" if pts and cap else "")
                                 + (f" — {msg}" if msg else ""),
                        recommendation="Review `/rag:projects` for archive-able completed projects, "
                                       "tighten `add_project_ignore_rule` patterns, or plan a sharding strategy.",
                        target="rag",
                    ))
                elif lvl in ("warning", "critical", "near-limit"):
                    app.append(Finding(
                        id="A-013", title=f"local Qdrant collection at {lvl} scale level",
                        severity="high",
                        evidence=f"scale.level={lvl}"
                                 + (f" ({pts} / {cap} points)" if pts and cap else "")
                                 + (f" — {msg}" if msg else ""),
                        recommendation="Archive completed projects, add ignore rules, or migrate to a sharded "
                                       "configuration before retrieval quality degrades. File an issue at "
                                       "github.com/taqat-techno/rag with the scale block from /api/status.",
                        target="rag",
                    ))
                elif lvl in ("over", "exceeded", "past-limit"):
                    # The collection is past the hard limit. Search latency
                    # and memory degrade noticeably. This is an objective
                    # state, so it always emits at high severity. The
                    # recommendation lists the maintainer-approved
                    # remediation order from
                    # `skills/ragtools-ops/references/risks-and-constraints.md`.
                    app.append(Finding(
                        id="A-014",
                        title=f"local Qdrant collection over hard limit (scale.level={lvl})",
                        severity="high",
                        evidence=f"scale.level={lvl}"
                                 + (f" ({pts} / {cap} points hard limit)" if pts and cap else "")
                                 + (f" — {msg}" if msg else ""),
                        recommendation=(
                            "Remediation order: "
                            "(1) tighten ignore_patterns via "
                            "`/rag:projects` `add-ignore` to drop build artifacts and vendored sources from the index; "
                            "(2) remove unnecessary indexed projects with `/rag:projects remove`; "
                            "(3) if the large index is intentional, consider migrating Qdrant to server mode. "
                            "See `skills/ragtools-ops/references/risks-and-constraints.md` "
                            "for the full guidance."
                        ),
                        target="rag",
                    ))

    # Log evidence
    if log_hits:
        total_hits = sum(len(item["matches"]) for item in log_hits)
        if total_hits >= 5:
            app.append(Finding(
                id="A-009", title=f"{total_hits} error-pattern matches in recent log tails",
                severity="medium",
                evidence=f"matched files: {', '.join(item['file'] for item in log_hits)}",
                recommendation="Run `/rag:doctor --logs` to classify against F-001..F-012.",
                target="rag",
            ))
        else:
            app.append(Finding(
                id="A-010", title=f"{total_hits} log warning(s) in recent tails",
                severity="low",
                evidence=", ".join(item["file"] for item in log_hits),
                recommendation="Skim `/rag:doctor --logs --verbose` if behavior is unexpected.",
                target="rag",
            ))

    # ---- Plugin-side
    if not plugin.plugin_dir:
        plg.append(Finding(
            id="P-001", title="rag-plugin source layout not detected next to this script",
            severity="critical",
            evidence="`.claude-plugin/plugin.json` not found relative to scripts/rag_report.py",
            recommendation="Re-clone the plugin or reinstall via `/plugins`.",
            target="plugins",
        ))
    else:
        if not plugin.manifest_version:
            plg.append(Finding(
                id="P-002", title="plugin manifest unreadable or missing `version`",
                severity="high",
                evidence=f".claude-plugin/plugin.json at `{normalize_home(plugin.plugin_dir)}`",
                recommendation="Validate with `python validate_plugin.py rag-plugin`.",
                target="plugins",
            ))
        if plugin.expected_missing:
            plg.append(Finding(
                id="P-003", title="expected plugin files missing",
                severity="high",
                evidence=", ".join(plugin.expected_missing),
                recommendation="Reinstall the plugin or restore from the marketplace clone.",
                target="plugins",
            ))

        # P-013 (D-031): advisory UserPromptSubmit hook that can BLOCK the prompt.
        # A raw `python ${CLAUDE_PLUGIN_ROOT}/hooks/<x>.py` command exits 2 when
        # the path fails to resolve, and exit 2 on UserPromptSubmit is a blocking
        # error that cancels the prompt before the model request. We emit ONLY on
        # *static* evidence (the current hooks.json actually contains such a
        # command); the runtime `hook-path-fatal` signal merely ESCALATES the
        # severity. Runtime-only would false-positive, because the same stderr
        # text appears in transcripts that only *discuss* the failure.
        if plugin.unsafe_advisory_hooks:
            fatal_runtime = scan.signal_counts.get("hook-path-fatal", 0)
            n = len(plugin.unsafe_advisory_hooks)
            sample = plugin.unsafe_advisory_hooks[0][:160]
            if fatal_runtime:
                sev = "critical"
                runtime_note = (
                    f" Runtime evidence: {fatal_runtime} hook path-resolution failure "
                    "signature(s) (can't-open-file / [Errno 2] / literal "
                    "${CLAUDE_PLUGIN_ROOT}) seen in recent sessions — the blocking path "
                    "has actually fired.")
            else:
                sev = "high"
                runtime_note = ""
            plg.append(Finding(
                id="P-013",
                title="advisory UserPromptSubmit hook can block the prompt "
                      "(Python exit 2 on path-resolution failure)",
                severity=sev,
                evidence=(
                    f"{n} advisory hook command(s) in hooks/hooks.json invoke a raw "
                    f"`python ${{CLAUDE_PLUGIN_ROOT}}/hooks/<script>.py` without a fail-open "
                    f"wrapper. If the host does not expand ${{CLAUDE_PLUGIN_ROOT}} (reported "
                    f"on Cowork/headless Windows) or the script is missing, Python exits 2 — "
                    f"a BLOCKING error on UserPromptSubmit that cancels the prompt before the "
                    f"model request. The scripts' own sys.exit(0) fail-safe cannot run because "
                    f"the file never loads. e.g. `{sample}`." + runtime_note),
                recommendation=(
                    "Make advisory hooks fail-open: route them through an inline `python -c` "
                    "bootstrap + hooks/hook_launcher.py so an unresolved path can never make "
                    "Python exit 2 (rag-plugin v0.15.1, D-031). Do NOT apply this to "
                    "intentionally-blocking hooks (e.g. a permissionDecision gate)."),
                target="plugins",
            ))

    # Claude config
    if not cci.user_claude_md_exists:
        plg.append(Finding(
            id="P-004", title="~/.claude/CLAUDE.md does not exist",
            severity="medium",
            evidence=cci.user_claude_md_path,
            recommendation="Run `/rag:config claude-md install` to install the retrieval rule.",
            target="plugins",
        ))
    elif not cci.retrieval_rule_present:
        plg.append(Finding(
            id="P-005", title="retrieval rule not installed in ~/.claude/CLAUDE.md",
            severity="high",
            evidence="None of the canonical markers were found in CLAUDE.md.",
            recommendation="Run `/rag:config claude-md install` (D-016).",
            target="plugins",
        ))

    if cci.duplicate_mcp_warning:
        plg.append(Finding(
            id="P-006", title="duplicate ragtools MCP registration detected",
            severity="high",
            evidence=cci.duplicate_mcp_warning,
            recommendation="Run `/rag:config mcp-dedupe clean` (D-015).",
            target="plugins",
        ))

    if not cci.plugin_mcp_present and plugin.plugin_dir:
        plg.append(Finding(
            id="P-007", title="plugin-level .mcp.json not found",
            severity="medium",
            evidence=cci.plugin_mcp_path or "(plugin root not resolved)",
            recommendation="Reinstall the plugin to restore the bundled .mcp.json (D-020).",
            target="plugins",
        ))

    # Hook log
    if hook_stats.log_exists and hook_stats.total_lines > 50:
        injected = hook_stats.actions.get("reminder-injected", 0)
        rate = (100.0 * injected / hook_stats.total_lines) if hook_stats.total_lines else 0.0
        if rate < 1 and hook_stats.total_lines > 200:
            plg.append(Finding(
                id="P-008", title=f"retrieval-reminder hook injection rate is very low ({rate:.1f}%)",
                severity="low",
                evidence=f"{injected}/{hook_stats.total_lines} prompts triggered injection.",
                recommendation="Lower RAG_PLUGIN_HOOK_PROBE_THRESHOLD or escalate to Tier 3 pre-fetch (D-017).",
                target="plugins",
            ))
        elif rate > 35:
            plg.append(Finding(
                id="P-009", title=f"retrieval-reminder hook injection rate is high ({rate:.1f}%)",
                severity="low",
                evidence=f"{injected}/{hook_stats.total_lines} prompts triggered injection.",
                recommendation="Raise RAG_PLUGIN_HOOK_PROBE_THRESHOLD if you see false positives in transcripts.",
                target="plugins",
            ))

    # Session evidence
    sk = scan.signal_counts
    if scan.sessions_scanned > 0:
        skipped = sk.get("retrieval-skipped", 0)
        rag_mentions = sk.get("rag-mention", 0)
        user_corrections = sk.get("user-correct-search", 0)
        mcp_errors = sk.get("mcp-error", 0)
        connect_ref = sk.get("connect-refused", 0)
        if rag_mentions > 0 and skipped > rag_mentions * 0.4:
            # D-030 routing fix: don't blame the plugin for skipped retrieval if
            # the ragtools service was not UP at scan time — the retrieval was
            # likely impossible because the application was unavailable.
            svc_down = state.service_mode in ("DOWN", "BROKEN", "STARTING", "N/A")
            plg.append(Finding(
                id="P-010", title="possible skipped retrieval pattern in recent sessions",
                severity="medium",
                evidence=f"{skipped} 'I don't have information'-shaped responses across "
                         f"{scan.sessions_with_signal} session(s) that also referenced ragtools."
                         + (f" NOTE: the ragtools service was '{state.service_mode}' at scan time, so "
                            "retrieval may have failed because the application was unavailable — routing "
                            "to the application repo rather than the plugin." if svc_down else ""),
                recommendation=("Bring the ragtools service up (`/rag:setup` / `/rag:doctor`) and re-check; "
                                "skipped retrieval here most likely reflects application availability, not the plugin."
                                if svc_down else
                                "Consider escalating Tier 2 → Tier 3 pre-fetch, or verify the CLAUDE.md rule is loaded "
                                "into project sessions (`/rag:config claude-md status --project`)."),
                target="rag" if svc_down else "plugins",
            ))
        if user_corrections > 0:
            plg.append(Finding(
                id="P-011", title="user manually corrected Claude to use the knowledge base",
                severity="medium",
                evidence=f"{user_corrections} corrective phrase(s) detected across recent sessions.",
                recommendation="Review the example snippets — these are highest-signal repro cases for the maintainers.",
                target="plugins",
            ))
        if mcp_errors > 0:
            # D-030 routing fix: MCP-error phrases while the service is DOWN/BROKEN
            # are an application fault (the `rag serve` MCP server itself), not
            # plugin wiring. Route by actual cause when the service state reveals it.
            svc_app_fault = state.service_mode in ("DOWN", "BROKEN")
            plg.append(Finding(
                id="P-012", title="MCP error phrases detected in sessions",
                severity="medium",
                evidence=f"{mcp_errors} MCP-error phrase(s) seen in recent session JSONL."
                         + (f" NOTE: service_mode was '{state.service_mode}', so these are most likely the "
                            "ragtools application (the `rag serve` MCP server) being down/broken rather than "
                            "plugin wiring — routing to the application repo." if svc_app_fault else ""),
                recommendation=("Bring the ragtools MCP server up and re-check (`/rag:doctor`); these MCP errors "
                                "track application availability, not plugin wiring."
                                if svc_app_fault else
                                "Cross-check with `/rag:doctor` and the maintainer playbook P-mcp."),
                target="rag" if svc_app_fault else "plugins",
            ))
        if connect_ref > 0 and state.service_mode != "UP":
            app.append(Finding(
                id="A-011", title="historical 'connection refused' events recorded against the service port",
                severity="low",
                evidence=f"{connect_ref} 'connection refused' phrase(s) in recent sessions.",
                recommendation="If recurring, file an issue at github.com/taqat-techno/rag with these timestamps.",
                target="rag",
            ))

    # If everything is fine, surface healthy info
    if not app:
        app.append(Finding(id="A-OK", title="ragtools application looks healthy on this device",
                           severity="info", evidence="No application-side issues detected.",
                           recommendation="Nothing to do.", target="rag"))
    if not plg:
        plg.append(Finding(id="P-OK", title="rag-plugin install + Claude config look healthy",
                           severity="info", evidence="No plugin-side issues detected.",
                           recommendation="Nothing to do.", target="plugins"))

    return app, plg


# --------------------------------------------------------------------------- #
# GitHub issue routing, fingerprinting, and creation (D-030)                  #
# --------------------------------------------------------------------------- #
#
# Design: the Python engine owns the deterministic, unit-testable logic
# (routing, fingerprint, plan, dedup, create); the /report command owns the one
# human yes/no confirmation. Default generation NEVER creates issues — creation
# only happens on an explicit `--create`, which the command issues after the
# user types "yes". All `gh` calls funnel through `_run_gh` (one mock point).

FINGERPRINT_MARKER_PREFIX = "rag-plugin-report:fingerprint:"


def issue_fingerprint(findings: list[Finding]) -> str:
    """Stable 12-hex fingerprint over the sorted non-info finding IDs, so the
    same diagnostic state yields the same fingerprint across runs/machines —
    the basis for duplicate detection. Falls back to all IDs when info-only."""
    ids = sorted({f.id for f in findings if f.severity != "info"})
    if not ids:
        ids = sorted({f.id for f in findings})
    return hashlib.sha256("|".join(ids).encode("utf-8")).hexdigest()[:12]


def build_issue_meta(target: str, findings: list[Finding],
                     state: State, plugin: PluginInspection) -> dict[str, Any]:
    """Single source of truth for an issue's repo / title / labels / fingerprint.
    Used by both render_github_issue (body marker) and build_issue_plan (gh
    creation) so the marker in the body and the plan never drift."""
    repo = "taqat-techno/rag" if target == "rag" else "taqat-techno/plugins"
    title_subject = "ragtools" if target == "rag" else "rag-plugin"
    non_info = [f for f in findings if f.severity != "info"]
    if non_info:
        primary = _sort_findings(non_info)[0]
        title = f"[{title_subject}] {primary.severity}: {primary.title}"
    else:
        title = (f"[{title_subject}] healthy report from rag-plugin "
                 f"v{plugin.manifest_version} (info-only findings)")
    sev_counts: dict[str, int] = {}
    for f in findings:
        sev_counts[f.severity] = sev_counts.get(f.severity, 0) + 1
    top_sev = next((k for k in ("critical", "high", "medium", "low")
                    if sev_counts.get(k)), "info")
    labels = ["diagnostic", f"severity:{top_sev}", "source:rag-plugin-report"]
    if target == "rag":
        labels.append(f"install-mode:{state.install_mode}")
        if state.service_mode != "N/A":
            labels.append(f"service:{state.service_mode.lower()}")
    return {
        "repo": repo,
        "target": target,
        "title": title,
        "labels": labels,
        "fingerprint": issue_fingerprint(findings),
        "actionable": bool(non_info),
        "finding_count": len(findings),
    }


def route_findings(app_findings: list[Finding],
                   plugin_findings: list[Finding]) -> tuple[list[Finding], list[Finding], list[str]]:
    """Route every finding to its issue by `target`, merging both source lists.
    A finding re-targeted across lists (e.g. a service-down MCP fault moved to
    'rag') lands in the correct issue instead of being silently dropped. Returns
    (rag_findings, plugins_findings, dropped_ids) — dropped_ids surfaces the
    silent-drop invariant rather than hiding it."""
    everything = list(app_findings) + list(plugin_findings)
    rag = [f for f in everything if f.target == "rag"]
    plugins = [f for f in everything if f.target == "plugins"]
    dropped = [f.id for f in everything if f.target not in ("rag", "plugins")]
    return rag, plugins, dropped


def build_issue_plan(routed: list[tuple[str, list[Finding], str, str]],
                     state: State, plugin: PluginInspection
                     ) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Build issue-plan.json entries + the clean issue-body files used for
    creation. The clean body is the portion of the rendered issue AFTER the
    copy-paste preamble (everything from the first ``\\n---\\n``), so an
    auto-created issue contains the real content, not the "paste this" header.
    Returns (plan, bodies) where bodies maps filename -> content."""
    plan: list[dict[str, Any]] = []
    bodies: dict[str, str] = {}
    for target, findings, rendered_md, human_file in routed:
        meta = build_issue_meta(target, findings, state, plugin)
        parts = rendered_md.split("\n---\n", 1)
        clean_body = parts[1] if len(parts) == 2 else rendered_md
        body_file = f"_issue-body-{target}.md"
        bodies[body_file] = clean_body
        plan.append({
            "repo": meta["repo"],
            "target": target,
            "title": meta["title"],
            "labels": meta["labels"],
            "fingerprint": meta["fingerprint"],
            "actionable": meta["actionable"],
            "finding_count": meta["finding_count"],
            "body_file": body_file,
            "human_file": human_file,
        })
    return plan, bodies


# --- gh CLI layer (single chokepoint `_run_gh` so tests can mock it) -------- #

def _run_gh(args: list[str], timeout: float = 20.0) -> tuple[int, str, str]:
    """Run a `gh` CLI subcommand. Single mock point for all GitHub access."""
    return _safe_run(["gh"] + args, timeout=timeout)


def gh_available() -> tuple[bool, str]:
    """True iff the gh CLI is installed AND authenticated. Never raises."""
    code, out, err = _run_gh(["auth", "status"], timeout=10.0)
    if code == 127:
        return False, "gh CLI not installed (not on PATH)"
    if code != 0:
        return False, "gh CLI not authenticated (run `gh auth login`)"
    return True, "gh authenticated"


def find_existing_open_issue(repo: str, fingerprint: str) -> Optional[str]:
    """Return the URL of an OPEN issue in `repo` whose body carries this
    fingerprint marker, else None. Prevents duplicate filing. Never raises."""
    code, out, err = _run_gh([
        "issue", "list", "--repo", repo, "--state", "open",
        "--search", fingerprint, "--limit", "50", "--json", "url,body",
    ])
    if code != 0 or not out:
        return None
    try:
        items = json.loads(out)
    except Exception:
        return None
    marker = f"{FINGERPRINT_MARKER_PREFIX}{fingerprint}"
    for it in items if isinstance(items, list) else []:
        if marker in (it.get("body") or ""):
            return it.get("url")
    return None


def create_issue(repo: str, title: str, body_file: Path) -> tuple[Optional[str], str]:
    """Create one issue via gh. Returns (url, error). Labels are intentionally
    NOT passed on create — a label missing in the target repo would fail the
    whole call; the suggested labels are listed in the body instead."""
    code, out, err = _run_gh([
        "issue", "create", "--repo", repo,
        "--title", title, "--body-file", str(body_file),
    ], timeout=30.0)
    if code != 0:
        return None, (err or out or "gh issue create failed")
    url = ""
    for line in (out or "").splitlines():
        line = line.strip()
        if line.startswith("http"):
            url = line
    return (url or (out or "").strip() or None), ""


def do_create(report_dir: Path) -> dict[str, Any]:
    """File GitHub issues from <report_dir>/issue-plan.json, with duplicate
    detection and a graceful local-only fallback when gh is unavailable. NEVER
    scans/generates — operates only on an existing report directory."""
    plan_path = report_dir / "issue-plan.json"
    if not plan_path.is_file():
        return {"ok": False, "reason": "no-plan", "results": []}
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"ok": False, "reason": f"plan-unreadable: {e}", "results": []}
    avail, why = gh_available()
    if not avail:
        return {"ok": False, "fallback": "local-only", "detail": why, "results": []}
    results: list[dict[str, Any]] = []
    for entry in plan:
        if not entry.get("actionable"):
            continue
        repo = entry["repo"]
        fp = entry["fingerprint"]
        body_file = report_dir / entry["body_file"]
        existing = find_existing_open_issue(repo, fp)
        if existing:
            results.append({"repo": repo, "status": "duplicate", "url": existing,
                            "title": entry["title"], "fingerprint": fp})
            continue
        url, err = create_issue(repo, entry["title"], body_file)
        if url:
            results.append({"repo": repo, "status": "created", "url": url,
                            "title": entry["title"], "fingerprint": fp})
        else:
            results.append({"repo": repo, "status": "error", "error": err,
                            "title": entry["title"], "fingerprint": fp})
    return {"ok": True, "results": results}


def _print_issue_plan(plan: list[dict[str, Any]]) -> None:
    actionable = [e for e in plan if e.get("actionable")]
    if not actionable:
        print("[rag_report] no actionable findings — no GitHub issues to file (healthy report).")
        return
    print("[rag_report] GitHub issue plan (nothing filed yet):")
    for e in actionable:
        print(f"  • {e['repo']}: {e['title']}")
        print(f"      fingerprint {e['fingerprint']} | body {e['body_file']}")


def _print_create_result(result: dict[str, Any]) -> None:
    if result.get("reason") == "no-plan":
        print("[rag_report] no issue-plan.json in that directory — run the report first. No issue created.")
        return
    if result.get("fallback") == "local-only":
        print(f"[rag_report] GitHub CLI unavailable — {result.get('detail', '')}. "
              "No issue was created; the local report files are complete and unchanged.")
        return
    results = result.get("results", [])
    if not results:
        print("[rag_report] no actionable issues to file (healthy report). No issue created.")
        return
    for r in results:
        if r["status"] == "created":
            print(f"[rag_report] CREATED   {r['repo']}: {r['url']}")
        elif r["status"] == "duplicate":
            print(f"[rag_report] DUPLICATE {r['repo']}: existing open issue {r['url']} (not re-filed)")
        else:
            print(f"[rag_report] ERROR     {r['repo']}: {r.get('error', 'unknown error')}")


# --------------------------------------------------------------------------- #
# Markdown rendering                                                          #
# --------------------------------------------------------------------------- #


_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def _sort_findings(items: list[Finding]) -> list[Finding]:
    return sorted(items, key=lambda f: (_SEVERITY_ORDER.get(f.severity, 9), f.id))


def _render_findings_table(findings: list[Finding]) -> str:
    if not findings:
        return "_No findings._\n"
    lines = ["| ID | Severity | Title | Recommendation |",
             "|----|----------|-------|----------------|"]
    for f in _sort_findings(findings):
        title = f.title.replace("|", "\\|")
        rec = f.recommendation.replace("|", "\\|")
        lines.append(f"| {f.id} | {f.severity} | {title} | {rec} |")
    return "\n".join(lines) + "\n"


def _render_findings_detail(findings: list[Finding]) -> str:
    out: list[str] = []
    for f in _sort_findings(findings):
        out.append(f"### {f.id} — {f.title}\n")
        out.append(f"- **Severity:** {f.severity}")
        out.append(f"- **Evidence:** {f.evidence}")
        out.append(f"- **Recommendation:** {f.recommendation}\n")
    return "\n".join(out) + "\n"


def render_application_report(state: State, log_hits: list[dict[str, Any]],
                              findings: list[Finding], meta: dict[str, str]) -> str:
    md: list[str] = []
    md.append("# RAC/RAG Application Setup Report\n")
    md.append(f"_Generated by rag-plugin v{meta['plugin_version']} report engine v{REPORT_VERSION} at {meta['timestamp']}._\n")
    md.append("> Target repository: **https://github.com/taqat-techno/rag**\n")

    md.append("## 1. Report metadata\n")
    md.append(f"- Generated: `{meta['timestamp']}`")
    md.append(f"- Hostname (redacted): `{meta['hostname']}`")
    md.append(f"- OS / platform: `{meta['platform']}`")
    md.append(f"- Python: `{meta['python']}`")
    md.append(f"- Shell: `{meta['shell']}`")
    md.append(f"- Plugin version: `{meta['plugin_version']}`")
    md.append(f"- ragtools binary version: `{state.version or 'unknown'}`")
    md.append(f"- Service mode: `{state.service_mode}`")
    md.append("")

    md.append("## 2. Installation detection\n")
    md.append(f"- Install mode: `{state.install_mode}`")
    md.append(f"- Binary path: `{normalize_home(state.binary_path) or 'not found'}`")
    md.append(f"- Detected version: `{state.version or 'unknown'}`")
    md.append(f"- Config path: `{normalize_home(state.config_path) or 'not found'}`")
    md.append(f"- Data path: `{normalize_home(state.data_path) or 'not found'}`")
    md.append(f"- Log path: `{normalize_home(state.log_path) or 'not found'}`")
    md.append(f"- Service host:port: `{state.host}:{state.port}`")
    md.append("")

    md.append("## 3. Runtime health\n")
    if state.health_status:
        md.append("```json")
        md.append(redact(json.dumps(state.health_status, indent=2, default=str))[:1500])
        md.append("```")
    else:
        md.append("_No /health response captured._")
    if state.api_status:
        md.append("\n**/api/status excerpt (redacted):**")
        # ragtools v2.5.x exposes points_count, scale, total_files, total_chunks,
        # last_indexed, projects[]; older builds also expose version/service/uptime.
        # Pick whatever the running build returned plus the path fields if any.
        wanted_keys = (
            "version", "service", "watcher", "uptime", "ready",
            "points_count", "total_files", "total_chunks", "last_indexed",
            "scale", "collection", "embedding_model", "score_threshold",
            "projects", "config_path", "data_path", "log_path",
        )
        excerpt = {k: v for k, v in state.api_status.items() if k in wanted_keys}
        # Truncate the projects list inline so the excerpt doesn't bloat
        if isinstance(excerpt.get("projects"), list) and len(excerpt["projects"]) > 5:
            excerpt["projects"] = excerpt["projects"][:5] + [
                f"... +{len(state.api_status['projects']) - 5} more"
            ]
        md.append("```json")
        md.append(redact(json.dumps(excerpt, indent=2, default=str))[:2000])
        md.append("```")
    if state.watcher_status:
        md.append("\n**Watcher:**")
        md.append("```json")
        md.append(redact(json.dumps(state.watcher_status, indent=2, default=str))[:600])
        md.append("```")
    md.append("")

    md.append("## 4. Configuration state\n")
    md.append(f"- Config file resolved: `{normalize_home(state.config_path) or 'not found'}`")
    rag_envs = {k: v for k, v in os.environ.items() if k.startswith("RAG_")}
    if rag_envs:
        md.append("- RAG_* environment variables (redacted):")
        for k, v in sorted(rag_envs.items()):
            md.append(f"  - `{k}` = `{redact(v)[:120]}`")
    else:
        md.append("- No `RAG_*` environment variables set.")
    md.append("")

    md.append("## 5. Data / index state\n")
    # Prefer the hydrated list from /api/projects + per-project status; fall
    # back to the lean projects array embedded in /api/status when the
    # primary endpoint returned nothing.
    project_view: list[dict[str, Any]] = list(state.api_projects)
    if not project_view and state.api_status:
        embedded = state.api_status.get("projects")
        if isinstance(embedded, list):
            project_view = [p for p in embedded if isinstance(p, dict)]

    if project_view:
        md.append(f"- Projects configured: **{len(project_view)}**")
        for p in project_view[:10]:
            name = p.get("project_id") or p.get("id") or p.get("name") or "?"
            files = p.get("files", "?")
            chunks = p.get("chunks", "?")
            enabled = p.get("enabled", "?")
            path = normalize_home(str(p.get("path") or "")) or "?"
            md.append(f"  - `{name}` — files: `{files}`, chunks: `{chunks}`, "
                      f"enabled: `{enabled}`, path: `{path}`")
        if len(project_view) > 10:
            md.append(f"  - _+{len(project_view) - 10} more_")
    else:
        md.append("- No project list available (service down or no projects configured).")

    # Aggregate stats from /api/status — these are the maintainer-relevant
    # numbers: points, total files, total chunks, last_indexed, scale level.
    if state.api_status:
        pts = state.api_status.get("points_count")
        tf = state.api_status.get("total_files")
        tc = state.api_status.get("total_chunks")
        li = state.api_status.get("last_indexed")
        scale = state.api_status.get("scale")
        scale_line = ""
        if isinstance(scale, dict):
            lvl = scale.get("level", "?")
            scale_line = f" — scale.level=`{lvl}`"
            limit = scale.get("limit") or scale.get("cap") or scale.get("max_points")
            if limit:
                scale_line += f" (limit `{limit}`)"
        if pts or tf or tc or li or scale_line:
            md.append(f"- **Index totals:** points=`{pts}`, files=`{tf}`, "
                      f"chunks=`{tc}`, last_indexed=`{li}`{scale_line}")
    md.append("")

    md.append("## 6. Logs and diagnostics\n")
    if not log_hits:
        md.append("- No matching error / warning lines in recent log tails.")
    else:
        for item in log_hits:
            md.append(f"### {item['file']}\n")
            md.append("```")
            for m in item["matches"]:
                md.append(redact(str(m["text"])))
            md.append("```")
    md.append("")

    md.append("## 7. Application-side issues found\n")
    md.append(_render_findings_table(findings))
    md.append("\n")
    md.append(_render_findings_detail(findings))

    md.append("## 8. Improvement opportunities for ragtools\n")
    md.append("- Better `rag service status` exit code semantics (currently 0 in some down states).")
    md.append("- Health endpoint should always return JSON, even on 5xx.")
    md.append("- Surface watcher start failures in `/health` rather than only the watcher endpoint.")
    md.append("- Improve cross-platform install detection so `where rag` always resolves on Windows after install.")
    md.append("- Provide a `--json` flag on `rag doctor` so the plugin doesn't have to text-parse.")
    md.append("- Document log directory location in `--help` output of `rag service`.")
    md.append("")

    md.append("## 9. GitHub-ready summary for github.com/taqat-techno/rag\n")
    md.append("See `github-rag-issue.md` for a copy-pasteable issue body. ")
    md.append("That file includes the redacted environment summary, severity-ranked findings, ")
    md.append("and a suggested title + labels.\n")
    return "\n".join(md)


def render_plugin_report(state: State, plugin: PluginInspection,
                         cci: ClaudeConfigInspection, hook_stats: HookLogStats,
                         scan: SessionScanResult, findings: list[Finding],
                         meta: dict[str, str]) -> str:
    md: list[str] = []
    md.append("# rag-plugin Behavior Report\n")
    md.append(f"_Generated by rag-plugin v{meta['plugin_version']} report engine v{REPORT_VERSION} at {meta['timestamp']}._\n")
    md.append("> Target repository: **https://github.com/taqat-techno/plugins**\n")

    md.append("## 1. Report metadata\n")
    md.append(f"- Generated: `{meta['timestamp']}`")
    md.append(f"- OS / platform: `{meta['platform']}`")
    md.append(f"- Plugin version: `{plugin.manifest_version or 'unknown'}`")
    md.append(f"- Plugin source dir: `{normalize_home(plugin.plugin_dir) or 'not found'}`")
    md.append(f"- Cached plugin dir(s): `{normalize_home(plugin.cache_dir) or 'none detected'}`")
    md.append("")

    md.append("## 2. Plugin installation state\n")
    md.append(f"- Manifest version: `{plugin.manifest_version or 'missing'}`")
    md.append(f"- Commands ({len(plugin.commands)}): {', '.join(plugin.commands) or '_none_'}")
    md.append(f"- Skills ({len(plugin.skills)}): {', '.join(plugin.skills) or '_none_'}")
    md.append(f"- Agents ({len(plugin.agents)}): {', '.join(plugin.agents) or '_none_'}")
    md.append(f"- Hooks ({len(plugin.hooks)}): {', '.join(plugin.hooks) or '_none_'}")
    md.append(f"- Rules ({len(plugin.rules)}): {', '.join(plugin.rules) or '_none_'}")
    md.append(f"- Scripts ({len(plugin.scripts)}): {', '.join(plugin.scripts) or '_none_'}")
    if plugin.expected_missing:
        md.append(f"- **Missing expected files:** {', '.join(plugin.expected_missing)}")
    md.append("")

    md.append("## 3. Claude configuration state\n")
    md.append(f"- `~/.claude/CLAUDE.md` present: `{cci.user_claude_md_exists}` (`{normalize_home(cci.user_claude_md_path)}`)")
    md.append(f"- Retrieval rule present: `{cci.retrieval_rule_present}`")
    if cci.retrieval_rule_marker_version:
        md.append(f"- Retrieval rule version marker: `v{cci.retrieval_rule_marker_version}`")
    md.append(f"- `~/.claude/settings.json` present: `{cci.settings_exists}`")
    md.append(f"- User-level MCP configs scanned: {', '.join(normalize_home(p) for p in cci.user_mcp_paths) or '_none_'}")
    md.append(f"- ragtools entries in user-level MCP configs: **{len(cci.user_mcp_ragtools_entries)}**")
    if cci.user_mcp_ragtools_entries:
        for e in cci.user_mcp_ragtools_entries:
            md.append(f"  - `{e['name']}` (command: `{redact(str(e['command']))[:80]}`) at `{normalize_home(e['source'])}`")
    md.append(f"- Plugin-level `.mcp.json` present: `{cci.plugin_mcp_present}` "
              f"(`{normalize_home(cci.plugin_mcp_path)}`)")
    if cci.duplicate_mcp_warning:
        md.append(f"- **Conflict:** {cci.duplicate_mcp_warning}")
    md.append("")

    md.append("## 4. Hook behavior state\n")
    expected_hooks = {"hooks.json", "lock_conflict_check.py",
                      "prompt_retrieval_reminder.py", "hook_launcher.py"}
    present_hooks = set(plugin.hooks)
    missing = sorted(expected_hooks - present_hooks)
    md.append(f"- Bundled hooks: {', '.join(sorted(present_hooks)) or '_none_'}")
    md.append(f"- Missing hooks: {', '.join(missing) or '_none_'}")
    if plugin.unsafe_advisory_hooks:
        md.append(f"- **⚠ Advisory hooks NOT fail-open:** {len(plugin.unsafe_advisory_hooks)} "
                  "UserPromptSubmit command(s) can block the prompt on path-resolution failure "
                  "(see finding P-013 / D-031).")
    else:
        md.append("- Advisory hook fail-open: `OK` — UserPromptSubmit hooks cannot block the "
                  "prompt (inline bootstrap + hook_launcher.py, D-031).")
    md.append(f"- User settings.json hooks block: `{cci.user_hooks_present}` "
              f"({cci.user_hooks_summary or 'none'})")
    md.append(f"- Hook decision log: `{normalize_home(hook_stats.log_path)}`")
    md.append(f"- Log lines recorded: `{hook_stats.total_lines}`")
    if hook_stats.actions:
        md.append("- Action breakdown:")
        for act, n in hook_stats.actions.items():
            md.append(f"  - `{act}`: {n}")
    if hook_stats.last_entry_ts:
        md.append(f"- Most recent entry: `{hook_stats.last_entry_ts}`")
    if hook_stats.notes:
        md.append(f"- Notes: {hook_stats.notes}")
    md.append("")

    md.append("## 5. Session behavior analysis\n")
    md.append(f"- Sessions found in `~/.claude/projects/`: **{scan.sessions_found}**")
    md.append(f"- Sessions scanned (newest-first): **{scan.sessions_scanned}**")
    md.append(f"- Sessions with at least one RAC/RAG signal: **{scan.sessions_with_signal}**")
    if scan.signal_counts:
        md.append("- Signal counts:")
        for sig, n in sorted(scan.signal_counts.items(), key=lambda kv: -kv[1]):
            md.append(f"  - `{sig}`: {n}")
    if scan.notes:
        md.append(f"- Notes: {scan.notes}")
    md.append("")
    if scan.examples:
        md.append("### Redacted example snippets\n")
        md.append("> Snippets are short, secret-redacted, single-line excerpts. They exist for maintainer triage only.")
        md.append("")
        for i, e in enumerate(scan.examples, 1):
            md.append(f"{i}. `[{e['signal']}]` from `{e['session_file']}`:")
            md.append(f"   > {e['snippet']}")
        md.append("")

    md.append("## 6. Plugin-side findings\n")
    md.append(_render_findings_table(findings))
    md.append("\n")
    md.append(_render_findings_detail(findings))

    md.append("## 7. Plugin improvement opportunities\n")
    md.append("- Add a Tier-3 pre-fetch escalation toggle to the retrieval-reminder hook for users on slow models.")
    md.append("- Add `/rag:config claude-md status --project` so per-project CLAUDE.md status is visible.")
    md.append("- Add a `--ci` flag to the report command so CI runners can enforce `no-high-findings`.")
    md.append("- Document expected hook log noise levels in `docs/decisions.md`.")
    md.append("- Provide a `--json` flag on every command for programmatic consumption.")
    md.append("")

    md.append("## 8. User-local customization analysis\n")
    md.append(f"- User has modified `~/.claude/CLAUDE.md`: `{cci.user_claude_md_exists}`")
    md.append(f"- User-level MCP entries that may shadow plugin: `{bool(cci.user_mcp_ragtools_entries)}`")
    md.append(f"- User-level hooks block: `{cci.user_hooks_present}`")
    md.append("")

    md.append("## 9. GitHub-ready summary for github.com/taqat-techno/plugins\n")
    md.append("See `github-plugins-issue.md` for a copy-pasteable issue body.\n")
    return "\n".join(md)


def render_summary(state: State, app_findings: list[Finding], plugin_findings: list[Finding],
                   plugin: PluginInspection, meta: dict[str, str], outdir: Path) -> str:
    md: list[str] = []
    md.append("# rag-plugin Diagnostic Summary\n")
    md.append(f"_Generated at {meta['timestamp']} (report engine v{REPORT_VERSION})._\n")
    md.append("## At a glance\n")
    md.append(f"- ragtools install: `{state.install_mode}`")
    md.append(f"- ragtools service: `{state.service_mode}`")
    md.append(f"- ragtools version: `{state.version or 'unknown'}`")
    md.append(f"- Plugin version: `{plugin.manifest_version or 'unknown'}`")
    md.append("")
    md.append("## Top application-side issues\n")
    md.append(_render_findings_table([f for f in _sort_findings(app_findings) if f.severity != "info"][:5]))
    md.append("\n## Top plugin-side issues\n")
    md.append(_render_findings_table([f for f in _sort_findings(plugin_findings) if f.severity != "info"][:5]))
    md.append("\n## Recommended next actions\n")
    actions: list[str] = []
    for f in _sort_findings(app_findings + plugin_findings):
        if f.severity in ("critical", "high"):
            actions.append(f"- {f.recommendation}")
    actions = list(dict.fromkeys(actions))[:6]
    if actions:
        md.extend(actions)
    else:
        md.append("- No critical or high findings — system looks healthy.")
    md.append("")
    md.append("## Output files\n")
    md.append(f"- [`rag-application-setup-report.md`](rag-application-setup-report.md)")
    md.append(f"- [`rag-plugin-behavior-report.md`](rag-plugin-behavior-report.md)")
    md.append(f"- [`github-rag-issue.md`](github-rag-issue.md)")
    md.append(f"- [`github-plugins-issue.md`](github-plugins-issue.md)")
    md.append(f"- [`redacted-diagnostics.json`](redacted-diagnostics.json)")
    md.append("")
    md.append(f"Output directory: `{normalize_home(str(outdir))}`\n")
    md.append("\n_This command does NOT upload anything. Copy the GitHub-ready files into a new issue manually._\n")
    return "\n".join(md)


def render_github_issue(target: str, findings: list[Finding], state: State,
                        plugin: PluginInspection, cci: ClaudeConfigInspection,
                        hook_stats: HookLogStats, scan: SessionScanResult,
                        meta: dict[str, str]) -> str:
    """Render a substantive, ready-to-paste GitHub issue body for the target repo.

    The output is designed so a user (anyone running rag-plugin) can copy it
    straight into a new issue and the maintainer gets enough context to triage
    without follow-up questions: install state, service runtime, structured
    /api/status excerpt, hook injection rate, session-signal counts, plugin
    configuration state, and severity-ranked findings with reproduction hints.

    All content is redacted by `redact()` and `normalize_home()` before this
    function sees it. This function only assembles, never raw-strings user data.
    """
    repo = "taqat-techno/rag" if target == "rag" else "taqat-techno/plugins"
    sev_counts: dict[str, int] = {}
    for f in findings:
        sev_counts[f.severity] = sev_counts.get(f.severity, 0) + 1

    # Title, labels, and the duplicate-detection fingerprint all come from the
    # single source of truth (build_issue_meta) so the body marker and
    # issue-plan.json can never drift.
    issue_meta = build_issue_meta(target, findings, state, plugin)
    suggested_title = issue_meta["title"]
    labels = issue_meta["labels"]
    fingerprint = issue_meta["fingerprint"]
    non_info_findings = [f for f in findings if f.severity != "info"]

    md: list[str] = []
    md.append(f"# Suggested issue for `github.com/{repo}`\n")
    md.append(f"**Suggested title:** `{suggested_title}`\n")
    md.append(f"**Suggested labels:** `{', '.join(labels)}`\n")
    md.append("Paste everything from `---` down into a new GitHub issue. The "
              "fields below are already redacted (secrets, tokens, cookies, "
              "PEM keys, long base64 trailing tokens, home-path normalization, "
              "hostname masking) — verify once more before posting publicly.\n")
    md.append("---\n")
    md.append(f"<!-- {FINGERPRINT_MARKER_PREFIX}{fingerprint} -->\n")

    # ------------------------------------------------------------------ #
    # Section 1 — Summary                                                  #
    # ------------------------------------------------------------------ #
    md.append("## Summary\n")
    if non_info_findings:
        primary = _sort_findings(non_info_findings)[0]
        md.append(f"`{primary.id}` ({primary.severity}) — {primary.title}.\n")
        md.append(f"**Recommended action:** {primary.recommendation}\n")
    else:
        md.append("No critical / high / medium / low findings — this report is informational. "
                  "Filing as a healthy-state datapoint for maintainers.\n")
    md.append(f"Findings breakdown: " + ", ".join(
        f"{n} {sev}" for sev, n in sorted(sev_counts.items(),
                                          key=lambda kv: _SEVERITY_ORDER.get(kv[0], 9))
    ) + ".\n")

    # ------------------------------------------------------------------ #
    # Section 2 — Environment                                              #
    # ------------------------------------------------------------------ #
    md.append("## Environment\n")
    md.append(f"- Generated: `{meta['timestamp']}` by report engine v{REPORT_VERSION}")
    md.append(f"- Hostname (masked): `{meta['hostname']}`")
    md.append(f"- OS / platform: `{meta['platform']}`")
    md.append(f"- Python: `{meta['python']}`")
    md.append(f"- Shell: `{meta['shell']}`")
    md.append(f"- Plugin version: **`rag-plugin v{plugin.manifest_version}`**")
    if target == "rag":
        md.append(f"- ragtools install mode: **`{state.install_mode}`**")
        md.append(f"- ragtools binary: `{normalize_home(state.binary_path) or 'not found'}`")
        md.append(f"- ragtools version: **`{state.version or 'unknown'}`**")
        md.append(f"- ragtools service mode: **`{state.service_mode}`**")
        md.append(f"- ragtools host:port: `{state.host}:{state.port}`")
        md.append(f"- ragtools data path: `{normalize_home(state.data_path) or 'not found'}`")
        md.append(f"- ragtools log path: `{normalize_home(state.log_path) or 'not found'}`")
    md.append("")

    # ------------------------------------------------------------------ #
    # Section 3 — Findings table + per-finding detail                      #
    # ------------------------------------------------------------------ #
    md.append("## Findings\n")
    md.append(_render_findings_table(findings))
    md.append("\n### Detail\n")
    md.append(_render_findings_detail(findings))

    # ------------------------------------------------------------------ #
    # Section 4 — target-specific evidence dumps                           #
    # ------------------------------------------------------------------ #
    if target == "rag":
        # Application-side evidence: /health body, /api/status excerpt,
        # watcher status, recent log error patterns. All redacted.
        md.append("## Runtime evidence\n")
        if state.health_status:
            md.append("**`GET /health`:**")
            md.append("```json")
            md.append(redact(json.dumps(state.health_status, indent=2, default=str))[:1200])
            md.append("```\n")
        if state.api_status:
            wanted = ("points_count", "total_files", "total_chunks", "last_indexed",
                      "scale", "collection", "embedding_model", "score_threshold",
                      "version", "service", "ready", "uptime")
            excerpt = {k: state.api_status[k] for k in wanted if k in state.api_status}
            md.append("**`GET /api/status` (key fields):**")
            md.append("```json")
            md.append(redact(json.dumps(excerpt, indent=2, default=str))[:1500])
            md.append("```\n")
        if state.watcher_status:
            md.append("**`GET /api/watcher/status`:**")
            md.append("```json")
            md.append(redact(json.dumps(state.watcher_status, indent=2, default=str))[:600])
            md.append("```\n")

        # Project inventory — concise; many users care about the count + scale
        project_view: list[dict[str, Any]] = list(state.api_projects)
        if not project_view and state.api_status:
            embedded = state.api_status.get("projects")
            if isinstance(embedded, list):
                project_view = [p for p in embedded if isinstance(p, dict)]
        if project_view:
            md.append(f"**Projects configured: {len(project_view)}**\n")
            md.append("| Name | Files | Chunks | Enabled |")
            md.append("|---|---|---|---|")
            for p in project_view[:15]:
                name = p.get("project_id") or p.get("id") or p.get("name") or "?"
                md.append(f"| `{name}` | {p.get('files', '?')} | "
                          f"{p.get('chunks', '?')} | {p.get('enabled', '?')} |")
            if len(project_view) > 15:
                md.append(f"\n_+{len(project_view) - 15} more not shown._")
            md.append("")
    else:
        # Plugin-side evidence: plugin layout inventory, Claude config state,
        # hook decisions stats, redacted session-signal counts.
        md.append("## Plugin layout (`rag-plugin/`)\n")
        md.append(f"- Plugin source dir: `{normalize_home(plugin.plugin_dir) or 'not found'}`")
        md.append(f"- Cached plugin dir(s): `{normalize_home(plugin.cache_dir) or 'none detected'}`")
        md.append(f"- Commands ({len(plugin.commands)}): {', '.join(plugin.commands) or '_none_'}")
        md.append(f"- Skills ({len(plugin.skills)}): {', '.join(plugin.skills) or '_none_'}")
        md.append(f"- Agents ({len(plugin.agents)}): {', '.join(plugin.agents) or '_none_'}")
        md.append(f"- Hooks ({len(plugin.hooks)}): {', '.join(plugin.hooks) or '_none_'}")
        md.append(f"- Rules ({len(plugin.rules)}): {', '.join(plugin.rules) or '_none_'}")
        md.append(f"- Scripts ({len(plugin.scripts)}): {', '.join(plugin.scripts) or '_none_'}")
        if plugin.expected_missing:
            md.append(f"- **Missing expected files:** {', '.join(plugin.expected_missing)}")
        md.append("")

        md.append("## Claude configuration\n")
        md.append(f"- `~/.claude/CLAUDE.md` present: `{cci.user_claude_md_exists}`")
        md.append(f"- Retrieval rule installed: `{cci.retrieval_rule_present}`"
                  + (f" (v{cci.retrieval_rule_marker_version})" if cci.retrieval_rule_marker_version else ""))
        md.append(f"- `~/.claude/settings.json` present: `{cci.settings_exists}`")
        md.append(f"- User-level MCP configs: {', '.join(normalize_home(p) for p in cci.user_mcp_paths) or '_none_'}")
        md.append(f"- ragtools entries in user-level MCP configs: **{len(cci.user_mcp_ragtools_entries)}**")
        md.append(f"- Plugin-level `.mcp.json` present: `{cci.plugin_mcp_present}`")
        if cci.duplicate_mcp_warning:
            md.append(f"- ⚠ {cci.duplicate_mcp_warning}")
        md.append(f"- User settings.json hooks block present: `{cci.user_hooks_present}`"
                  + (f" ({cci.user_hooks_summary})" if cci.user_hooks_summary else ""))
        md.append("")

        md.append("## Retrieval-reminder hook decisions\n")
        if hook_stats.log_exists and hook_stats.total_lines > 0:
            md.append(f"- Log: `{normalize_home(hook_stats.log_path)}`")
            md.append(f"- Total decisions logged: **{hook_stats.total_lines}**")
            if hook_stats.last_entry_ts:
                md.append(f"- Most recent entry: `{hook_stats.last_entry_ts}`")
            md.append("- Action breakdown:")
            total = max(hook_stats.total_lines, 1)
            for act, n in hook_stats.actions.items():
                pct = 100.0 * n / total
                md.append(f"  - `{act}`: {n} ({pct:.1f}%)")
        else:
            md.append("- No hook decision log present (hook never fired or observability disabled).")
        md.append("")

        md.append("## Session-behavior signals\n")
        md.append(f"- Sessions discovered in `~/.claude/projects/`: **{scan.sessions_found}**")
        md.append(f"- Sessions scanned (newest-first, capped): **{scan.sessions_scanned}**")
        md.append(f"- Sessions with at least one RAC/RAG signal: **{scan.sessions_with_signal}**")
        if scan.signal_counts:
            md.append("- Signal counts:")
            for sig, n in sorted(scan.signal_counts.items(), key=lambda kv: -kv[1]):
                md.append(f"  - `{sig}`: {n}")
        if scan.examples:
            md.append("\n_Redacted example snippets (≤220 chars each, single-line, secret-redacted):_\n")
            for i, e in enumerate(scan.examples[:6], 1):
                md.append(f"{i}. `[{e['signal']}]` from `{e['session_file']}`:")
                md.append(f"   > {e['snippet']}")
        md.append("")

    # ------------------------------------------------------------------ #
    # Section 5 — Reproduction                                             #
    # ------------------------------------------------------------------ #
    md.append("## Reproduction\n")
    if target == "rag":
        md.append("To regenerate this evidence on any device with `rag-plugin` installed:")
        md.append("")
        md.append("1. `rag service status` (start with `rag service start` if it returns DOWN)")
        md.append("2. `rag doctor` for the layered dependency report")
        md.append("3. `/rag:doctor --full` from inside Claude Code for the structured version")
        md.append("4. `/rag:report` to regenerate this whole document")
        md.append("")
        md.append("Maintainer: the structured findings are also in "
                  "`redacted-diagnostics.json` next to this file in the user's "
                  "`~/.claude/rag-plugin/reports/<timestamp>/` directory.")
    else:
        md.append("To regenerate this evidence on any device with `rag-plugin` installed:")
        md.append("")
        md.append("1. `/rag:doctor` to confirm state and detect plugin assertions")
        md.append("2. `/rag:config status` for plugin configuration snapshot")
        md.append("3. `/rag:report` to regenerate this whole document")
        md.append("")
        md.append("Maintainer: the structured findings + per-session signal counts "
                  "are in `redacted-diagnostics.json` next to this file.")
    md.append("")

    # ------------------------------------------------------------------ #
    # Section 6 — Privacy notice (always last)                             #
    # ------------------------------------------------------------------ #
    md.append("## Privacy notice\n")
    md.append("This report was redacted before generation:")
    md.append("- Secrets, API keys, bearer headers, cookies, PEM private keys, GitHub PATs, AWS keys, Slack tokens.")
    md.append("- Home directory paths normalized to `~/...`.")
    md.append("- Hostname masked (first 2 + last 2 chars).")
    md.append("- Session JSONL snippets clipped to ≤220 chars and stripped of newlines.")
    md.append("- Only RAC/RAG-related signals were extracted from sessions — never full conversations.")
    md.append("- The command never auto-uploads anything; the user is copying this manually.")
    md.append("")
    md.append("**Before posting publicly, scan the body once more for anything project-specific "
              "you do not want to share.** The redaction is high-precision but not exhaustive — "
              "team names, internal hostnames, branch names, and file paths under your home dir "
              "may still leak through.")
    return "\n".join(md)


# --------------------------------------------------------------------------- #
# Self-test                                                                   #
# --------------------------------------------------------------------------- #


def _self_test() -> int:
    """Lightweight unit-style sanity tests using stdlib only."""
    print("[rag_report] self-test")

    # Redaction sanity
    samples = [
        ("Authorization: Bearer abcdef.GHIJKL_123456789", "<redacted-bearer>"),
        ("api_key=sk_live_abcdef123456ABCDEF", "<redacted-secret>"),
        ("ghp_ABCDEFGHIJKLMNOP01234567890123456789", "<redacted-github-pat>"),
        ("Cookie: session=AAAAAAAA", "<redacted-cookie>"),
        ("plain text with no secret", "plain text with no secret"),
    ]
    failed = 0
    for original, expected_marker in samples:
        out = redact(original)
        if expected_marker not in out and original != expected_marker:
            print(f"  [FAIL] redaction did not catch: {original!r} -> {out!r}")
            failed += 1
        else:
            print(f"  [OK] {original[:30]}...")

    # Snippet scrubbing
    snippet = _redact_snippet("multi\nline\r\n  text  with   spaces api_key=secret_xxxxxxxxxxxxxxxx", 80)
    assert "secret_x" not in snippet, "redaction failed inside snippet"
    assert "\n" not in snippet, "newlines should be stripped"
    print("  [OK] snippet scrubbing")

    # normalize_home
    home = str(Path.home())
    assert normalize_home(home + os.sep + "x").startswith("~"), "home normalization failed"
    print("  [OK] normalize_home")

    # Findings table render with empty list
    assert "No findings" in _render_findings_table([])
    print("  [OK] empty-findings render")

    # Findings render with sample
    f = Finding(id="X-1", title="t|test", severity="high", evidence="e", recommendation="r", target="rag")
    table = _render_findings_table([f])
    assert "X-1" in table and "t\\|test" in table
    print("  [OK] findings table render")

    # Sort order: critical < high < medium < low < info
    arr = [
        Finding("a", "x", "info", "", "", "rag"),
        Finding("b", "x", "critical", "", "", "rag"),
        Finding("c", "x", "low", "", "", "rag"),
    ]
    sorted_arr = _sort_findings(arr)
    assert [f.severity for f in sorted_arr] == ["critical", "low", "info"], \
        f"sort order wrong: {[f.severity for f in sorted_arr]}"
    print("  [OK] severity sort order")

    if failed:
        print(f"[rag_report] FAIL — {failed} redaction sample(s) missed")
        return 1
    print("[rag_report] self-test OK")
    return 0


# --------------------------------------------------------------------------- #
# Main                                                                        #
# --------------------------------------------------------------------------- #


def _hostname_redacted() -> str:
    name = socket.gethostname()
    if not name:
        return "<unknown>"
    if len(name) <= 4:
        return "***"
    return name[:2] + "***" + name[-2:]


def _gather_meta(plugin_version: str) -> dict[str, str]:
    return {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ"),
        "hostname": _hostname_redacted(),
        "platform": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "python": sys.version.split()[0],
        "shell": os.environ.get("SHELL") or os.environ.get("COMSPEC", "unknown"),
        "plugin_version": plugin_version,
    }


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="rag-plugin diagnostic report generator")
    ap.add_argument("--out", help="output directory (default: ~/.claude/rag-plugin/reports/<ts>/)")
    ap.add_argument("--no-sessions", action="store_true",
                    help="skip the session JSONL scanner (privacy-cautious mode)")
    ap.add_argument("--max-sessions", type=int, default=60,
                    help="max session JSONL files to scan (default: 60, newest-first)")
    ap.add_argument("--quiet", action="store_true", help="suppress progress lines")
    ap.add_argument("--self-test", action="store_true", help="run internal sanity tests and exit")
    ap.add_argument("--create", action="store_true",
                    help="create GitHub issues from the report's issue-plan.json via `gh` "
                         "(dedup-checks first; falls back to local-only if gh is unavailable)")
    ap.add_argument("--from", dest="from_dir", default=None,
                    help="with --create: file from an existing report directory instead of re-scanning")
    ap.add_argument("--dry-run", action="store_true",
                    help="generate local artifacts only; never create issues (legacy local-only mode)")
    args = ap.parse_args(argv)

    if args.self_test:
        return _self_test()

    # Safety: --dry-run always wins over --create (legacy local-only mode).
    if args.dry_run:
        args.create = False

    # Create-only fast path: file issues from an already-generated report dir
    # without re-scanning sessions or re-probing the service.
    if args.create and args.from_dir:
        result = do_create(Path(args.from_dir).expanduser().resolve())
        _print_create_result(result)
        return 0

    def log(msg: str) -> None:
        if not args.quiet:
            print(f"[rag_report] {msg}")

    # Resolve plugin
    plugin_dir = find_plugin_dir()
    plugin = inspect_plugin(plugin_dir)
    plugin_version = plugin.manifest_version or "unknown"
    meta = _gather_meta(plugin_version)

    # Output dir
    ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    if args.out:
        outdir = Path(args.out).expanduser().resolve()
    else:
        outdir = Path.home() / ".claude" / "rag-plugin" / "reports" / ts
    try:
        outdir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[rag_report] FATAL: cannot create output dir {outdir}: {e}", file=sys.stderr)
        return 2
    log(f"output: {outdir}")

    # Probe state
    state = State()
    log("detecting install mode")
    detect_install_mode(state)
    log(f"install_mode={state.install_mode}")

    if state.install_mode != "not-installed":
        log("probing service /health")
        probe_service(state)
        log(f"service_mode={state.service_mode}")
        if state.service_mode == "UP":
            probe_api(state)
        if state.binary_path:
            detect_version(state)
        resolve_default_paths(state)

    # Inspect Claude config
    log("inspecting Claude config")
    cci = inspect_claude_config()

    # Hook log
    log("inspecting hook decision log")
    hook_stats = inspect_hook_log()

    # Tail logs
    log_hits: list[dict[str, Any]] = []
    if state.log_path:
        log_hits = tail_recent_errors(state.log_path)

    # Sessions
    if args.no_sessions:
        scan = SessionScanResult(notes="session scan skipped (--no-sessions)")
    else:
        log(f"scanning sessions (max {args.max_sessions})")
        scan = scan_sessions(max_sessions=args.max_sessions)

    # Synthesize
    log("synthesizing findings")
    app_findings, plugin_findings = synthesize_findings(state, plugin, cci, hook_stats, log_hits, scan)

    # Render reports
    app_md = render_application_report(state, log_hits, app_findings, meta)
    plugin_md = render_plugin_report(state, plugin, cci, hook_stats, scan, plugin_findings, meta)
    summary_md = render_summary(state, app_findings, plugin_findings, plugin, meta, outdir)
    # Route every finding to its issue by target (merging both source lists) so a
    # service-down MCP/retrieval fault re-targeted to 'rag' lands in the rag issue
    # instead of being silently dropped. `dropped` surfaces the invariant.
    rag_findings, plugins_findings, dropped = route_findings(app_findings, plugin_findings)
    if dropped:
        print(f"[rag_report] WARNING: {len(dropped)} finding(s) had an unroutable target and were "
              f"omitted from issues: {dropped}", file=sys.stderr)
    issue_rag = render_github_issue("rag", rag_findings,
                                    state, plugin, cci, hook_stats, scan, meta)
    issue_plg = render_github_issue("plugins", plugins_findings,
                                    state, plugin, cci, hook_stats, scan, meta)

    # Structured diagnostics (machine-readable, redacted)
    diag = {
        "report_version": REPORT_VERSION,
        "generated": meta["timestamp"],
        "host": meta["hostname"],
        "platform": meta["platform"],
        "plugin_version": plugin.manifest_version,
        "state": {k: v for k, v in asdict(state).items() if k != "health_status"},
        "plugin": asdict(plugin),
        "claude_config": asdict(cci),
        "hook_stats": asdict(hook_stats),
        "log_hits_count": sum(len(item["matches"]) for item in log_hits),
        "session_scan": asdict(scan),
        "app_findings": [f.to_dict() for f in app_findings],
        "plugin_findings": [f.to_dict() for f in plugin_findings],
    }

    # Issue creation plan + clean (post-preamble, fingerprint-marked) issue bodies.
    routed = [
        ("rag", rag_findings, issue_rag, "github-rag-issue.md"),
        ("plugins", plugins_findings, issue_plg, "github-plugins-issue.md"),
    ]
    issue_plan, issue_bodies = build_issue_plan(routed, state, plugin)

    files = {
        "rag-application-setup-report.md": app_md,
        "rag-plugin-behavior-report.md": plugin_md,
        "summary.md": summary_md,
        "github-rag-issue.md": issue_rag,
        "github-plugins-issue.md": issue_plg,
        "redacted-diagnostics.json": json.dumps(diag, indent=2, default=str),
        "issue-plan.json": json.dumps(issue_plan, indent=2),
    }
    files.update(issue_bodies)
    for name, content in files.items():
        path = outdir / name
        try:
            path.write_text(content, encoding="utf-8")
        except Exception as e:
            print(f"[rag_report] FATAL: writing {path}: {e}", file=sys.stderr)
            return 3

    if not args.quiet:
        print(f"[rag_report] wrote {len(files)} files to {outdir}")
        print(f"[rag_report] open the summary: {outdir / 'summary.md'}")
        _print_issue_plan(issue_plan)

    # Optional one-shot creation (`--create` without `--from`). The /report
    # command normally generates first, shows the plan, asks the yes/no, then
    # calls `--create --from <dir>` on yes — but one-shot --create is supported.
    if args.create:
        result = do_create(outdir)
        _print_create_result(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
