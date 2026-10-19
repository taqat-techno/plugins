#!/usr/bin/env python3
"""
qa-browser PreToolUse hook — production host gate.

This file is the single owner of the gate's decision rules. README and skills
describe it by reference; change the rules here (and in tests/test_prod_gate.py).

Gated tools (matcher in hooks/hooks.json; dispatch below by tool-name suffix):
  * URL tools   — navigate_page, new_page (chrome-devtools), browser_navigate,
                  browser_tabs (playwright), navigate (Claude in Chrome /
                  Claude Browser). The URL comes from url / URL / href / address.
  * Script tools — browser_evaluate, browser_run_code(_unsafe), evaluate_script,
                  javascript_tool. URLs are taken from the script text ONLY when
                  it contains a navigation construct (location = / location.href =
                  / location.assign|replace( / window.open( / .goto( ). Scripts
                  without one are allowed untouched.

Decision, per URL, on the HOSTNAME only (never the path or query):
  1. host is in `productionHosts` (exact or subdomain), or a hostname label (or a
     '-'/'_'-separated part of one) equals a `productionMarkers` entry
     (a marker containing a '.' is matched as a host)          -> BLOCK (exit 2)
  2. host is localhost / 127.0.0.1 / ::1 / *.localhost / *.test, or the
     `targetUrl` host, or in `allowedHosts`                    -> allow
  3. a target config exists (`targetUrl` or `allowedHosts` set) -> ask
     (permissionDecision "ask": the user approves the unknown host)
  4. no target config                                          -> allow
URLs without a host (about:, data:, relative) are allowed.

Config: `.qa-browser.local.json`, looked up in $CLAUDE_PROJECT_DIR, then the
cwd and its parents. Keys: targetUrl, allowedHosts, productionHosts,
productionMarkers (default ["prod", "production"]). The plugin option
`production_hosts` (userConfig, delivered as CLAUDE_PLUGIN_OPTION_PRODUCTION_HOSTS,
comma-separated) adds hosts to productionHosts in every project.

Tracked credentials: when the config holds inline credential values
(roles.<r>.password / totp / totpSecret) AND git tracks the file, every gated
navigation is denied until the file is untracked (audit QAB-P1-05).

Override: QA_BROWSER_ALLOW_PRODUCTION=1 in the environment Claude Code was
LAUNCHED with turns a BLOCK into an allow plus an audit line for Claude. A hook
inherits Claude Code's environment, so exporting the variable inside the
session (a Bash tool call, another shell) has no effect; restart Claude Code.

Exit codes: 0 allow / ask (JSON on stdout); 2 block (reason on stderr).
Any internal error fails open (exit 0), as does an unparseable payload.
"""

from __future__ import annotations

import ipaddress
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor"))
import hooklib  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass


CONFIG_FILENAME = ".qa-browser.local.json"
DEFAULT_MARKERS = ["prod", "production"]
OVERRIDE_ENV = "QA_BROWSER_ALLOW_PRODUCTION"
OPTION_ENV = "CLAUDE_PLUGIN_OPTION_PRODUCTION_HOSTS"
INLINE_SECRET_KEYS = ("password", "totp", "totpSecret")

URL_KEYS = ("url", "URL", "href", "address")
SCRIPT_KEYS = ("function", "code", "expression", "script", "text")
SCRIPT_TOOLS = {"browser_evaluate", "browser_run_code", "browser_run_code_unsafe",
                "evaluate_script", "javascript_tool"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
LOCAL_SUFFIXES = (".localhost", ".test")

NAV_CONSTRUCT_RE = re.compile(
    r"location\s*(?:\.\s*href\s*)?=(?!=)"
    r"|location\s*\.\s*(?:assign|replace)\s*\("
    r"|window\s*\.\s*open\s*\("
    r"|\.\s*goto\s*\(",
)
SCRIPT_URL_RE = re.compile(r"""(?:https?:)?//[^\s'"`<>)\]}]+""", re.IGNORECASE)

_RANK = {"allow": 0, "ask": 1, "block": 2}


# ---------------------------------------------------------------- config

def find_config() -> Path | None:
    candidates: list[Path] = []
    project = os.environ.get("CLAUDE_PROJECT_DIR")
    if project:
        candidates.append(Path(project))
    cwd = Path.cwd()
    candidates.append(cwd)
    candidates.extend(cwd.parents)
    for d in candidates:
        p = d / CONFIG_FILENAME
        if p.is_file():
            return p
    return None


def load_config(path: Path | None = None) -> dict:
    path = path if path is not None else find_config()
    if path is None:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def effective_config(config: dict) -> dict:
    """The project config plus user-level production hosts from the plugin option."""
    raw = os.environ.get(OPTION_ENV) or os.environ.get("CLAUDE_PLUGIN_OPTION_production_hosts") or ""
    extra = [h.strip() for h in raw.split(",") if h.strip()]
    if not extra:
        return config
    merged = dict(config)
    merged["productionHosts"] = _str_list(config.get("productionHosts")) + extra
    return merged


def has_inline_secrets(config: dict) -> bool:
    roles = config.get("roles")
    if not isinstance(roles, dict):
        return False
    return any(isinstance(e, dict) and any(isinstance(e.get(k), str) and e[k].strip()
                                           for k in INLINE_SECRET_KEYS)
               for e in roles.values())


def is_tracked(path: Path) -> bool:
    try:
        r = subprocess.run(["git", "ls-files", "--error-unmatch", path.name],
                           cwd=str(path.parent), capture_output=True, timeout=3)
    except Exception:
        return False
    return r.returncode == 0


def _str_list(value) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [str(v).strip().lower() for v in value if str(v).strip()]


# ---------------------------------------------------------------- hosts

def hostname_of(url: str) -> str | None:
    url = url.strip()
    if not url:
        return None
    if url.startswith("//"):
        url = "http:" + url
    elif "://" not in url:
        # about:blank, data:, javascript:, mailto: carry no host; a bare
        # "example.com/x" does.
        if re.match(r"^[a-z][a-z0-9+.-]*:(?!\d)", url, re.IGNORECASE):
            return None
        if url.startswith(("/", "?", "#", ".")):
            return None
        url = "http://" + url
    try:
        host = urlsplit(url).hostname
    except ValueError:
        return None
    if not host:
        return None
    return host.rstrip(".").lower()


def _host_entry_matches(host: str, entry: str) -> bool:
    entry = entry.strip().lower().rstrip(".")
    if "://" in entry or "/" in entry:
        entry = hostname_of(entry) or ""
    if entry.startswith("*."):
        entry = entry[2:]
    return bool(entry) and (host == entry or host.endswith("." + entry))


def _is_local(host: str) -> bool:
    if host in LOCAL_HOSTS or host.endswith(LOCAL_SUFFIXES):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def production_match(host: str, config: dict) -> str | None:
    """Return a description of the production rule `host` hits, else None."""
    for entry in _str_list(config.get("productionHosts")):
        if _host_entry_matches(host, entry):
            return f"productionHosts entry '{entry}'"
    markers = _str_list(config.get("productionMarkers")) or DEFAULT_MARKERS
    labels = host.split(".")
    tokens = set(labels)
    for label in labels:
        tokens.update(t for t in re.split(r"[-_]", label) if t)
    for m in markers:
        if "." in m:
            if _host_entry_matches(host, m):
                return f"production marker '{m}'"
        elif m in tokens:
            return f"production marker '{m}'"
    return None


def allowed_hosts(config: dict) -> list[str]:
    hosts = _str_list(config.get("allowedHosts"))
    target = config.get("targetUrl")
    if isinstance(target, str):
        th = hostname_of(target)
        if th:
            hosts.append(th)
    return hosts


def decide(url: str, config: dict) -> tuple[str, str]:
    """Classify one URL: ('allow'|'ask'|'block', reason)."""
    host = hostname_of(url)
    if not host:
        return "allow", "no host"
    hit = production_match(host, config)
    if hit:
        return "block", f"host '{host}' matches {hit}"
    if _is_local(host):
        return "allow", "local host"
    allow = allowed_hosts(config)
    if any(_host_entry_matches(host, a) for a in allow):
        return "allow", "allow-listed host"
    if allow:
        return "ask", (f"host '{host}' is not the QA target or in allowedHosts "
                       f"({', '.join(sorted(set(allow)))})")
    return "allow", "no target config"


# ---------------------------------------------------------------- tool input

def extract_urls(tool_name: str, tool_input: dict) -> list[str]:
    suffix = tool_name.rsplit("__", 1)[-1]
    if suffix in SCRIPT_TOOLS:
        urls: list[str] = []
        for key in SCRIPT_KEYS:
            text = tool_input.get(key)
            if isinstance(text, str) and NAV_CONSTRUCT_RE.search(text):
                urls.extend(m.group(0).rstrip(".,;") for m in SCRIPT_URL_RE.finditer(text))
        return urls
    for key in URL_KEYS:
        v = tool_input.get(key)
        if isinstance(v, str) and v.strip():
            return [v.strip()]
    return []


# ---------------------------------------------------------------- main

def main() -> int:
    hooklib.watchdog(4.5)
    payload = hooklib.read_payload()
    if payload is None:
        return 0
    tool_input = hooklib.tool_input(payload) or payload.get("toolInput") or {}
    if not isinstance(tool_input, dict):
        return 0
    tool_name = str(payload.get("tool_name") or payload.get("toolName") or "")

    urls = extract_urls(tool_name, tool_input)
    if not urls:
        return 0

    config_path = find_config()
    config = load_config(config_path) if config_path else {}
    if config_path and has_inline_secrets(config) and is_tracked(config_path):
        hooklib.deny(f"[qa-browser] {CONFIG_FILENAME} holds inline credentials and is "
                     f"tracked by git. Navigation is refused until the user runs "
                     f"`git rm --cached {CONFIG_FILENAME}`, git-ignores it, and rotates "
                     f"the exposed passwords. Tell the user; do not work around this.")
        return 0
    config = effective_config(config)
    verdict, reason, worst_url = "allow", "", ""
    for url in urls:
        v, r = decide(url, config)
        if _RANK[v] > _RANK[verdict]:
            verdict, reason, worst_url = v, r, url

    if verdict == "allow":
        return 0

    if verdict == "ask":
        hooklib.ask(f"[qa-browser] {worst_url}: {reason}. Approve only if this is a "
             f"non-production host; to stop this prompt, add it to allowedHosts "
             f"in {CONFIG_FILENAME}.")
        return 0

    if os.environ.get(OVERRIDE_ENV) == "1":
        hooklib.context("PreToolUse", f"[qa-browser] navigation to production URL {worst_url} ({reason}) "
                f"ALLOWED because {OVERRIDE_ENV}=1 is set for this session.")
        return 0

    print(
        f"[qa-browser] BLOCKED navigation to {worst_url}\n"
        f"  Reason: {reason}.\n"
        f"  There is no in-session override. To run against production on purpose,\n"
        f"  quit Claude Code and relaunch it with the variable set:\n"
        f"      Windows PowerShell:  $env:{OVERRIDE_ENV} = '1'; claude\n"
        f"      bash / zsh:          {OVERRIDE_ENV}=1 claude\n"
        f"  Setting it from a Bash tool call or another shell does not reach this hook.\n"
        f"  If this host is not production, adjust productionHosts / productionMarkers\n"
        f"  in {CONFIG_FILENAME}.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    hooklib.run(main)  # fail open: the gate is best-effort, never a crash-blocker
