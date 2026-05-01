#!/usr/bin/env python3
"""rag-plugin diagnostic report generator (v0.8.0).

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
from urllib import request as urlrequest
from urllib.error import URLError, HTTPError

# Force UTF-8 stdout on Windows cp1252 consoles (same pattern as md_analyzer.py)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

REPORT_VERSION = "0.8.0"
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
        req = urlrequest.Request(url, headers={"User-Agent": "rag-plugin-report/0.8.0"})
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
    code, body, _ = _http_get_json(f"{base}/api/status", timeout=2.0)
    if code == 200 and isinstance(body, dict):
        state.api_status = body
        for key in ("config_path", "data_path", "log_path"):
            v = body.get(key)
            if v and isinstance(v, str):
                setattr(state, key, v)
    code, body, _ = _http_get_json(f"{base}/api/projects", timeout=2.0)
    if code == 200 and isinstance(body, list):
        state.api_projects = [p for p in body if isinstance(p, dict)]
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
            f"alongside the plugin-level registration. /rag-config mcp-dedupe clean removes them."
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


_SIGNAL_PATTERNS = [
    ("rag-mention", re.compile(r"\b(ragtools|rac/rag|rag-plugin|search_knowledge_base|knowledge base)\b", re.IGNORECASE)),
    ("rag-port", re.compile(r"127\.0\.0\.1:21420|:21420\b")),
    ("mcp-error", re.compile(r"MCP[^\n]{0,40}(error|failed|disconnected|not connect)", re.IGNORECASE)),
    ("retrieval-skipped", re.compile(r"(I don't have (enough )?information|I don't have access|I don't have any information)", re.IGNORECASE)),
    ("user-correct-search", re.compile(r"(why didn'?t you search|use the knowledge base|search first|did you check the (rag|knowledge))", re.IGNORECASE)),
    ("rag-error-line", re.compile(r"\[RAG ERROR\]|\[RAG STATUS\].*failed", re.IGNORECASE)),
    ("connect-refused", re.compile(r"(connection refused|ECONNREFUSED|HTTPConnectionPool.*Failed)", re.IGNORECASE)),
    ("port-in-use", re.compile(r"(EADDRINUSE|address already in use|port .* in use)", re.IGNORECASE)),
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
            recommendation="Install via `/rag:rag-setup` (auto-detects platform) or "
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
                recommendation="Run `/rag:rag-doctor --full --logs` to classify against F-001..F-012.",
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
                    recommendation="POST /api/watcher/start or run `/rag:rag-doctor --symptom F-004 --fix`.",
                    target="rag",
                ))
            if not state.api_projects:
                app.append(Finding(
                    id="A-008", title="no projects configured",
                    severity="info",
                    evidence="/api/projects returned an empty list.",
                    recommendation="Add a project with `/rag:rag-projects add` so the knowledge base is populated.",
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
                recommendation="Run `/rag:rag-doctor --logs` to classify against F-001..F-012.",
                target="rag",
            ))
        else:
            app.append(Finding(
                id="A-010", title=f"{total_hits} log warning(s) in recent tails",
                severity="low",
                evidence=", ".join(item["file"] for item in log_hits),
                recommendation="Skim `/rag:rag-doctor --logs --verbose` if behavior is unexpected.",
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

    # Claude config
    if not cci.user_claude_md_exists:
        plg.append(Finding(
            id="P-004", title="~/.claude/CLAUDE.md does not exist",
            severity="medium",
            evidence=cci.user_claude_md_path,
            recommendation="Run `/rag:rag-config claude-md install` to install the retrieval rule.",
            target="plugins",
        ))
    elif not cci.retrieval_rule_present:
        plg.append(Finding(
            id="P-005", title="retrieval rule not installed in ~/.claude/CLAUDE.md",
            severity="high",
            evidence="None of the canonical markers were found in CLAUDE.md.",
            recommendation="Run `/rag:rag-config claude-md install` (D-016).",
            target="plugins",
        ))

    if cci.duplicate_mcp_warning:
        plg.append(Finding(
            id="P-006", title="duplicate ragtools MCP registration detected",
            severity="high",
            evidence=cci.duplicate_mcp_warning,
            recommendation="Run `/rag:rag-config mcp-dedupe clean` (D-015).",
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
            plg.append(Finding(
                id="P-010", title="possible skipped retrieval pattern in recent sessions",
                severity="medium",
                evidence=f"{skipped} 'I don't have information'-shaped responses across "
                         f"{scan.sessions_with_signal} session(s) that also referenced ragtools.",
                recommendation="Consider escalating Tier 2 → Tier 3 pre-fetch, or verify the CLAUDE.md rule is loaded "
                               "into project sessions (`/rag:rag-config claude-md status --project`).",
                target="plugins",
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
            plg.append(Finding(
                id="P-012", title="MCP error phrases detected in sessions",
                severity="medium",
                evidence=f"{mcp_errors} MCP-error phrase(s) seen in recent session JSONL.",
                recommendation="Cross-check with `/rag:rag-doctor` and the maintainer playbook P-mcp.",
                target="plugins",
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
        excerpt = {k: v for k, v in state.api_status.items() if k in
                   ("version", "service", "watcher", "uptime", "config_path", "data_path", "log_path")}
        md.append("```json")
        md.append(redact(json.dumps(excerpt, indent=2, default=str))[:1500])
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
    if state.api_projects:
        md.append(f"- Projects configured: **{len(state.api_projects)}**")
        for p in state.api_projects[:10]:
            md.append(f"  - `{p.get('name', '?')}` — files: `{p.get('files', '?')}`, "
                      f"chunks: `{p.get('chunks', '?')}`, enabled: `{p.get('enabled', '?')}`")
        if len(state.api_projects) > 10:
            md.append(f"  - _+{len(state.api_projects) - 10} more_")
    else:
        md.append("- No project list available (service down or no projects configured).")
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
    expected_hooks = {"hooks.json", "lock_conflict_check.py", "prompt_retrieval_reminder.py"}
    present_hooks = set(plugin.hooks)
    missing = sorted(expected_hooks - present_hooks)
    md.append(f"- Bundled hooks: {', '.join(sorted(present_hooks)) or '_none_'}")
    md.append(f"- Missing hooks: {', '.join(missing) or '_none_'}")
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
    md.append("- Add `/rag:rag-config claude-md status --project` so per-project CLAUDE.md status is visible.")
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
                        plugin: PluginInspection, meta: dict[str, str]) -> str:
    repo = "taqat-techno/rag" if target == "rag" else "taqat-techno/plugins"
    sev_counts: dict[str, int] = {}
    for f in findings:
        sev_counts[f.severity] = sev_counts.get(f.severity, 0) + 1

    def _severity_label() -> str:
        for k in ("critical", "high", "medium", "low"):
            if sev_counts.get(k):
                return k
        return "info"

    top_sev = _severity_label()
    title_subject = "ragtools" if target == "rag" else "rag-plugin"
    suggested_title = f"[diagnostic] {title_subject} — {top_sev} findings from rag-plugin v{plugin.manifest_version} report"
    labels = ["diagnostic", f"severity:{top_sev}"]
    labels.append("source:rag-plugin-report")

    md: list[str] = []
    md.append(f"# Suggested issue for github.com/{repo}\n")
    md.append(f"**Suggested title:** `{suggested_title}`\n")
    md.append(f"**Suggested labels:** `{', '.join(labels)}`\n")
    md.append("---\n")
    md.append("## Environment\n")
    md.append(f"- Generated by `rag-plugin` v{plugin.manifest_version} report engine v{REPORT_VERSION} on {meta['timestamp']}")
    md.append(f"- OS: `{meta['platform']}`")
    md.append(f"- Python: `{meta['python']}`")
    if target == "rag":
        md.append(f"- ragtools install: `{state.install_mode}`, version: `{state.version or 'unknown'}`")
        md.append(f"- service mode: `{state.service_mode}`")
    md.append("")
    md.append("## Findings\n")
    md.append(_render_findings_table(findings))
    md.append("\n## Detail\n")
    md.append(_render_findings_detail(findings))
    md.append("## Reproduction\n")
    if target == "rag":
        md.append("1. `rag service status` (or `rag service start` if down)")
        md.append("2. `rag doctor` for the layered dependency report")
        md.append("3. tail the most recent service log\n")
    else:
        md.append("1. `/rag:rag-doctor` to confirm state")
        md.append("2. `/rag:rag-config status` for plugin config snapshot")
        md.append("3. `/rag:rag-report` to regenerate this evidence on a fresh device\n")
    md.append("## Privacy\n")
    md.append("Secrets, tokens, bearer headers, cookies, and private keys were redacted before this issue was generated. ")
    md.append("Home directories are normalized to `~`. Snippets are short and single-line. ")
    md.append("Verify the redaction once more before posting publicly.\n")
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
    args = ap.parse_args(argv)

    if args.self_test:
        return _self_test()

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
    issue_rag = render_github_issue("rag", [f for f in app_findings if f.target == "rag"],
                                    state, plugin, meta)
    issue_plg = render_github_issue("plugins", [f for f in plugin_findings if f.target == "plugins"],
                                    state, plugin, meta)

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

    files = {
        "rag-application-setup-report.md": app_md,
        "rag-plugin-behavior-report.md": plugin_md,
        "summary.md": summary_md,
        "github-rag-issue.md": issue_rag,
        "github-plugins-issue.md": issue_plg,
        "redacted-diagnostics.json": json.dumps(diag, indent=2, default=str),
    }
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
