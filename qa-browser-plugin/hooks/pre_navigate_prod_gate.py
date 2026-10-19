#!/usr/bin/env python3
"""
qa-browser PreToolUse hook - production host gate.

This file is the single owner of the gate's decision rules. README and skills
describe it by reference; change the rules here (and in tests/test_prod_gate.py
and tests/test_gate_v091.py).

Gated tools (matcher in hooks/hooks.json; dispatch below by tool-name suffix):
  * URL tools    - navigate_page, new_page (chrome-devtools), browser_navigate,
                   browser_tabs (playwright), navigate (Claude in Chrome /
                   Claude Browser), preview_start (Claude Browser: `url`, or the
                   `name` of a .claude/launch.json entry). The URL comes from
                   url / URL / href / address.
  * Batch tools  - browser_batch (Claude in Chrome / Claude Browser): every nested
                   {name, input} action is inspected as if it were called alone.
  * Script tools - browser_evaluate, browser_run_code(_unsafe), evaluate_script,
                   javascript_tool. A script is inspected only when it contains a
                   navigation construct (location = / location.href = /
                   location.assign|replace( / window.open( / .goto( ) or a network
                   construct (fetch( / XMLHttpRequest .open(method, url /
                   navigator.sendBeacon( / new WebSocket|EventSource|Request( /
                   request.get|post|put|patch|delete|head|fetch( ). Every URL
                   literal in such a script is decided; simple 'a' + 'b' literal
                   concatenation is folded first. A construct whose URL argument
                   is built at run time (a variable, a template `${...}` inside the
                   host) is "unresolved": the user is asked when production hosts
                   are configured (productionHosts or the production_hosts
                   option), otherwise it is allowed. Scripts without a construct
                   are allowed untouched.
  * Bash / PowerShell - only when a .qa-browser.local.json exists: curl / wget / httpie
                   (http, https) / xh / aria2c / Invoke-WebRequest / Invoke-RestMethod
                   (iwr, irm) aimed at a production host -> BLOCK. Other hosts are
                   not asked about. A command that names a role's passwordEnv /
                   totpEnv that is outside the credential allow-list -> deny.

URL normalisation follows browsers (WHATWG): leading/trailing whitespace and
control characters are trimmed and tab/CR/LF removed; backslashes count as '/';
for http(s)/ws(s)/ftp any run of slashes after the scheme is skipped
(`https:/h`, `https:\\\\h`, `https:h` all reach host h); `//h` is scheme-relative;
userinfo (`user@`) and the port are dropped; the host is percent-decoded,
lower-cased, IDN-encoded to punycode, and stripped of trailing dots; numeric IPv4
forms are canonicalised. Config entries are normalised the same way.
view-source: and blob: are unwrapped; a javascript: URL is decided by the URL
literals inside it.

Decision, per URL, on the HOSTNAME only (never the path or query):
  1. host is in `productionHosts` (exact or subdomain), or a hostname label (or a
     '-'/'_'-separated part of one) equals a `productionMarkers` entry
     (a marker containing a '.' is matched as a host)          -> BLOCK (exit 2)
  2. host is localhost / 127.0.0.1 / ::1 / *.localhost / *.test, or the
     `targetUrl` host, or in `allowedHosts`                    -> allow
  3. a target config exists (`targetUrl` or `allowedHosts` set) -> ask
     (permissionDecision "ask": the user approves the unknown host)
  4. no target config                                          -> allow
URLs that carry no host by design (about:, data:, mailto:, file:, relative paths,
navigate "back"/"forward") are allowed. A URL whose host CANNOT be determined
(http(s) with an empty or malformed host) -> ask: navigation fails closed.

Config: `.qa-browser.local.json`, looked up in $CLAUDE_PROJECT_DIR, then the
cwd and its parents. Keys: targetUrl, allowedHosts, productionHosts,
productionMarkers (default ["prod", "production"]). The plugin option
`production_hosts` (userConfig, delivered as CLAUDE_PLUGIN_OPTION_PRODUCTION_HOSTS,
comma-separated) adds hosts to productionHosts in every project.

Credential env allow-list: a role's passwordEnv / totpEnv must start with `QA_`
(upper case, `QA_[A-Z0-9_]+`) or be listed in the plugin option
`credential_env_allowlist` (CLAUDE_PLUGIN_OPTION_CREDENTIAL_ENV_ALLOWLIST,
comma-separated). `credential_env_allowed()` is the single owner of that rule;
scripts/totp.py and the SessionStart hook import it.

Tracked credentials: when the config holds inline credential values
(roles.<r>.password / totp / totpSecret) AND git tracks the file, every gated
navigation is denied until the file is untracked (audit QAB-P1-05).

Override: QA_BROWSER_ALLOW_PRODUCTION=1 in the environment Claude Code was
LAUNCHED with turns a BLOCK into an allow plus an audit line for Claude. A hook
inherits Claude Code's environment, so exporting the variable inside the
session (a Bash tool call, another shell) has no effect; restart Claude Code.

Exit codes: 0 allow / ask / deny (JSON on stdout); 2 block (reason on stderr).
Any internal error fails open (exit 0), as does an unparseable payload.
"""

from __future__ import annotations

import ipaddress
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

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
CRED_ALLOWLIST_ENV = "CLAUDE_PLUGIN_OPTION_CREDENTIAL_ENV_ALLOWLIST"
CRED_ENV_RE = re.compile(r"^QA_[A-Z0-9_]+$")
CRED_ENV_KEYS = ("passwordEnv", "totpEnv")
INLINE_SECRET_KEYS = ("password", "totp", "totpSecret")

URL_KEYS = ("url", "URL", "href", "address")
SCRIPT_KEYS = ("function", "code", "expression", "script", "text")
SCRIPT_TOOLS = {"browser_evaluate", "browser_run_code", "browser_run_code_unsafe",
                "evaluate_script", "javascript_tool"}
URL_TOOLS = {"navigate", "navigate_page", "new_page", "browser_navigate", "browser_tabs"}
BATCH_TOOLS = {"browser_batch"}
SHELL_TOOLS = {"Bash", "PowerShell"}
PREVIEW_TOOLS = {"preview_start"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
LOCAL_SUFFIXES = (".localhost", ".test")
SPECIAL_SCHEMES = {"http", "https", "ws", "wss", "ftp"}
WRAPPER_SCHEMES = {"view-source", "blob"}
HOSTLESS_WORDS = {"back", "forward", "reload"}
MAX_BATCH_DEPTH = 3

# Each construct ends right before its URL argument.
CONSTRUCT_RE = re.compile(
    r"\blocation\s*(?:\.\s*href\s*)?=(?!=)"
    r"|\blocation\s*\.\s*(?:assign|replace)\s*\("
    r"|\bwindow\s*\.\s*open\s*\("
    r"|\.\s*goto\s*\("
    r"|\bfetch\s*\("
    r"|\bnavigator\s*\.\s*sendBeacon\s*\("
    r"|\bnew\s+(?:WebSocket|EventSource|Request)\s*\("
    r"|\.\s*open\s*\(\s*(['\"`])[A-Za-z]+\1\s*,"
    r"|\brequest\s*\.\s*(?:get|post|put|patch|delete|head|fetch)\s*\(",
)
SCRIPT_URL_RE = re.compile(
    r"""(?:(?:https?|wss?|ftp):[/\\]*|//)[^\s'"`<>)\]}]+""", re.IGNORECASE)
LITERAL_CONCAT_RE = re.compile(r"""(['"])((?:\\.|(?!\1).)*)\1\s*\+\s*(['"])((?:\\.|(?!\3).)*)\3""")

NET_TOOL_RE = re.compile(
    r"(?:^|[\s;&|(`'\"])(?:[\w.:~/\\-]*[/\\])?"
    r"(curl|wget2?|https?|httpie|xh|xhs|aria2c|invoke-webrequest|invoke-restmethod|iwr|irm)"
    r"(?:\.exe)?(?=\s)", re.IGNORECASE)
BARE_HOST_RE = re.compile(r"[A-Za-z0-9_.-]+\.[A-Za-z][A-Za-z0-9-]*\.?(?::\d+)?(?:[/?#]\S*)?")
CMD_SEPARATORS_RE = re.compile(r"[;&|\n]")

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


def _option(upper: str) -> str:
    lower = "CLAUDE_PLUGIN_OPTION_" + upper[len("CLAUDE_PLUGIN_OPTION_"):].lower()
    return os.environ.get(upper) or os.environ.get(lower) or ""


def effective_config(config: dict) -> dict:
    """The project config plus user-level production hosts from the plugin option."""
    extra = [h.strip() for h in _option(OPTION_ENV).split(",") if h.strip()]
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


# ---------------------------------------------------------------- credential env names

def credential_env_allowed(name) -> bool:
    """True when `name` may be read as a QA credential: QA_[A-Z0-9_]+ or allow-listed."""
    if not isinstance(name, str) or not name.strip():
        return False
    name = name.strip()
    if CRED_ENV_RE.match(name):
        return True
    extra = {n.strip() for n in _option(CRED_ALLOWLIST_ENV).split(",") if n.strip()}
    return name in extra


def disallowed_credential_envs(config: dict) -> list[str]:
    """passwordEnv / totpEnv names in the config that fail the allow-list."""
    roles = config.get("roles")
    if not isinstance(roles, dict):
        return []
    bad = set()
    for entry in roles.values():
        if not isinstance(entry, dict):
            continue
        for key in CRED_ENV_KEYS:
            v = entry.get(key)
            if isinstance(v, str) and v.strip() and not credential_env_allowed(v):
                bad.add(v.strip())
    return sorted(bad)


# ---------------------------------------------------------------- hosts

def _ipv4(host: str) -> str | None:
    """WHATWG IPv4 parse: '0x7f.1', '2130706433', '0177.0.0.1' -> dotted quad.
    Returns None when the host is not an IPv4 form, '' when it is a malformed one."""
    parts = host.split(".")
    if not parts or len(parts) > 4 or not re.fullmatch(r"0[x][0-9a-f]*|[0-9]+", parts[-1]):
        return None
    nums = []
    for p in parts:
        if re.fullmatch(r"0x[0-9a-f]*", p):
            nums.append(int(p[2:] or "0", 16))
        elif re.fullmatch(r"0[0-7]+", p):
            nums.append(int(p, 8))
        elif re.fullmatch(r"[0-9]+", p):
            nums.append(int(p))
        else:
            return ""
    if any(n > 255 for n in nums[:-1]) or nums[-1] >= 256 ** (5 - len(nums)):
        return ""
    value = nums[-1]
    for i, n in enumerate(nums[:-1]):
        value += n * 256 ** (3 - i)
    return str(ipaddress.IPv4Address(value))


def normalise_hostname(host: str) -> str | None:
    """Browser-style host canonicalisation; None when the host is invalid."""
    host = unquote(host or "").strip()
    host = re.sub("[。．｡]", ".", host).rstrip(".").lower()
    if not host:
        return None
    if any(ord(c) > 127 for c in host):
        try:
            host = host.encode("idna").decode("ascii").lower()
        except (UnicodeError, ValueError):
            return None
    if not re.fullmatch(r"[a-z0-9_.-]+", host) or ".." in host:
        return None
    v4 = _ipv4(host)
    if v4 == "":
        return None
    return v4 or host


def _host_from_authority(authority: str) -> tuple[str, str | None]:
    auth = authority.rpartition("@")[2]
    if auth.startswith("["):
        end = auth.find("]")
        if end < 0:
            return "unknown", None
        try:
            return "host", str(ipaddress.IPv6Address(auth[1:end])).lower()
        except ValueError:
            return "unknown", None
    host = normalise_hostname(auth.split(":", 1)[0])
    return ("host", host) if host else ("unknown", None)


def parse_host(url) -> tuple[str, str | None]:
    """Classify a URL as a browser would: ('host', h) / ('none', None) for URLs that
    carry no host by design / ('unknown', None) when the host cannot be determined."""
    url = str(url or "")
    url = url.strip("".join(chr(c) for c in range(0x21)))
    url = re.sub(r"[\t\n\r]", "", url)
    if not url or url.lower() in HOSTLESS_WORDS:
        return "none", None
    m = re.match(r"^([a-z][a-z0-9+.-]*):(?![0-9])", url, re.IGNORECASE)
    if m:
        scheme, rest = m.group(1).lower(), url[m.end():]
        if scheme in WRAPPER_SCHEMES:
            return parse_host(rest)
        if scheme not in SPECIAL_SCHEMES:
            return "none", None  # about:, data:, javascript:, mailto:, file:, chrome:
        rest = rest.replace("\\", "/").lstrip("/")
        return _host_from_authority(re.split(r"[/?#]", rest, maxsplit=1)[0])
    u = url.replace("\\", "/")
    if u.startswith("//"):
        return _host_from_authority(re.split(r"[/?#]", u[2:].lstrip("/"), maxsplit=1)[0])
    if u.startswith(("/", "?", "#", ".")):
        return "none", None  # relative to the current (already gated) page
    return _host_from_authority(re.split(r"[/?#]", u, maxsplit=1)[0])


def hostname_of(url: str) -> str | None:
    kind, host = parse_host(url)
    return host if kind == "host" else None


def _entry_host(entry: str) -> str | None:
    entry = str(entry).strip().lower()
    if entry.startswith("*."):
        entry = entry[2:]
    return hostname_of(entry)


def _host_entry_matches(host: str, entry: str) -> bool:
    e = _entry_host(entry)
    return bool(e) and (host == e or host.endswith("." + e))


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


def production_adjacent(config: dict) -> bool:
    """Production hosts are configured, so an unresolvable script URL is worth a prompt."""
    return bool(_str_list(config.get("productionHosts")))


def decide(url: str, config: dict, *, unknown: str = "ask") -> tuple[str, str]:
    """Classify one URL: ('allow'|'ask'|'block', reason)."""
    stripped = str(url).strip()
    if re.match(r"^\s*javascript:", stripped, re.IGNORECASE):
        inner = unquote(stripped.split(":", 1)[1])
        worst = ("allow", "javascript: URL without a URL literal")
        for m in SCRIPT_URL_RE.finditer(inner):
            v = decide(m.group(0).rstrip(".,;"), config, unknown=unknown)
            if _RANK[v[0]] > _RANK[worst[0]]:
                worst = v
        return worst
    kind, host = parse_host(url)
    if kind == "none":
        return "allow", "no host"
    if kind == "unknown":
        return unknown, "the gate cannot determine this URL's host"
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


# ---------------------------------------------------------------- scripts

def _fold_literals(text: str) -> str:
    """'https://' + 'app.example.com' -> 'https://app.example.com' (literals only)."""
    for _ in range(20):
        new = LITERAL_CONCAT_RE.sub(lambda m: m.group(1) + m.group(2) + m.group(4) + m.group(1), text)
        if new == text:
            break
        text = new
    return text


def _read_literal(text: str, i: int) -> tuple[str, int, bool]:
    """Read the JS string literal starting at text[i]; return (value, end, dynamic)."""
    q = text[i]
    j, buf = i + 1, []
    while j < len(text) and text[j] != q:
        if text[j] == "\\" and j + 1 < len(text):
            buf.append(text[j + 1])
            j += 2
            continue
        buf.append(text[j])
        j += 1
    value = "".join(buf)
    if q == "`" and "${" in value:
        return value[:value.index("${")], j + 1, True
    return value, j + 1, False


def _resolve_arg(text: str, pos: int) -> tuple[str, str | None]:
    """The construct argument at `pos`: ('url', u) / ('relative', None) / ('unresolved', None)."""
    n = len(text)
    i = pos
    while i < n and text[i].isspace():
        i += 1
    if i >= n or text[i] not in "'\"`":
        return "unresolved", None
    value, i, dynamic = _read_literal(text, i)
    while not dynamic:
        k = i
        while k < n and text[k].isspace():
            k += 1
        if k < n and text[k] == "+":
            dynamic = True  # a non-literal operand follows (literal pairs were folded)
        break
    norm = value.strip().replace("\\", "/")
    has_scheme = re.match(r"^[a-z][a-z0-9+.-]*:", norm, re.IGNORECASE)
    if has_scheme or norm.startswith("//"):
        if dynamic:
            body = re.sub(r"^[a-z][a-z0-9+.-]*:", "", norm, flags=re.IGNORECASE).lstrip("/")
            if not re.search(r"[/?#]", body):
                return "unresolved", None  # the host itself is built at run time
        return "url", value
    if dynamic and norm in ("", "/"):
        return "unresolved", None
    return "relative", None


def script_targets(text: str) -> tuple[list[str], bool]:
    """URLs a script navigates to or requests, and whether any target is unresolved."""
    text = _fold_literals(text)
    constructs = list(CONSTRUCT_RE.finditer(text))
    if not constructs:
        return [], False
    urls: list[str] = []
    unresolved = False
    for m in constructs:
        kind, url = _resolve_arg(text, m.end())
        if kind == "url" and url:
            urls.append(url)
        elif kind == "unresolved":
            unresolved = True
    urls.extend(m.group(0).rstrip(".,;") for m in SCRIPT_URL_RE.finditer(text))
    return urls, unresolved


# ---------------------------------------------------------------- tool input

def _launch_json_url(name: str) -> str | None:
    roots = [os.environ.get("CLAUDE_PROJECT_DIR") or "", str(Path.cwd())]
    for root in roots:
        if not root:
            continue
        p = Path(root) / ".claude" / "launch.json"
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for conf in data.get("configurations", []) if isinstance(data, dict) else []:
            if isinstance(conf, dict) and conf.get("name") == name:
                if isinstance(conf.get("url"), str):
                    return conf["url"]
                if conf.get("port"):
                    return f"http://localhost:{conf['port']}"
                return None
    return None


def collect(tool_name: str, tool_input: dict, depth: int = 0, nested: bool = False):
    """Yield ('nav', url) / ('script', url) / ('unresolved', None) for one tool call."""
    suffix = str(tool_name).rsplit("__", 1)[-1]
    if suffix in BATCH_TOOLS:
        if depth >= MAX_BATCH_DEPTH:
            return
        actions = tool_input.get("actions")
        for item in actions if isinstance(actions, list) else []:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or item.get("tool") or ""
            inp = item.get("input") if isinstance(item.get("input"), dict) else item.get("args")
            if isinstance(inp, dict):
                yield from collect(name, inp, depth + 1, nested=True)
        return
    if suffix in SCRIPT_TOOLS:
        for key in SCRIPT_KEYS:
            text = tool_input.get(key)
            if isinstance(text, str):
                urls, unresolved = script_targets(text)
                for u in urls:
                    yield "script", u
                if unresolved:
                    yield "unresolved", None
        return
    if nested and suffix not in URL_TOOLS | PREVIEW_TOOLS:
        return  # computer, find, read_page ... carry no navigation URL
    for key in URL_KEYS:
        v = tool_input.get(key)
        if isinstance(v, str) and v.strip():
            yield "nav", v
            return
    if suffix in PREVIEW_TOOLS and isinstance(tool_input.get("name"), str):
        u = _launch_json_url(tool_input["name"])
        if u:
            yield "nav", u


def extract_urls(tool_name: str, tool_input: dict) -> list[str]:
    """Back-compat helper: the URLs a tool call would be gated on."""
    return [u for kind, u in collect(tool_name, tool_input) if u]


def _bash_hosts(command: str) -> list[str]:
    """Hosts a shell command sends HTTP requests to (curl / wget / httpie / ...)."""
    if not NET_TOOL_RE.search(command):
        return []
    hosts: list[str] = []
    for m in SCRIPT_URL_RE.finditer(command):
        h = hostname_of(m.group(0).rstrip(".,;"))
        if h:
            hosts.append(h)
    for m in NET_TOOL_RE.finditer(command):
        segment = CMD_SEPARATORS_RE.split(command[m.end():], maxsplit=1)[0]
        try:
            tokens = shlex.split(segment, posix=True)
        except ValueError:
            tokens = segment.split()
        for tok in tokens:
            tok = tok.strip("'\"")
            if "=" in tok and tok.startswith("-"):
                tok = tok.split("=", 1)[1]
            if not tok or tok.startswith("-"):
                continue
            if "://" in tok or BARE_HOST_RE.fullmatch(tok):
                h = hostname_of(tok)
                if h:
                    hosts.append(h)
    return hosts


def _mentions(command: str, name: str) -> bool:
    return re.search(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])", command) is not None


# ---------------------------------------------------------------- output

def _block(target: str, reason: str) -> int:
    if os.environ.get(OVERRIDE_ENV) == "1":
        hooklib.context("PreToolUse", f"[qa-browser] request to production target {target} ({reason}) "
                        f"ALLOWED because {OVERRIDE_ENV}=1 is set for this session.")
        return 0
    print(
        f"[qa-browser] BLOCKED navigation to {target}\n"
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


def gate_bash(command: str, config_path: Path) -> int:
    raw = load_config(config_path)
    for name in disallowed_credential_envs(raw):
        if _mentions(command, name):
            hooklib.deny(f"[qa-browser] {CONFIG_FILENAME} names '{name}' as a role credential "
                         f"variable, but credential variables must start with QA_ or be listed "
                         f"in the credential_env_allowlist plugin option. Reading it is refused: "
                         f"a shared config could otherwise exfiltrate any secret in the "
                         f"environment. Tell the user; do not work around this.")
            return 0
    config = effective_config(raw)
    for host in _bash_hosts(command):
        hit = production_match(host, config)
        if hit:
            return _block(host, f"shell HTTP request: host '{host}' matches {hit}")
    return 0


def main() -> int:
    hooklib.watchdog(4.5)
    payload = hooklib.read_payload()
    if payload is None:
        return 0
    tool_input = hooklib.tool_input(payload) or payload.get("toolInput") or {}
    if not isinstance(tool_input, dict):
        return 0
    tool_name = str(payload.get("tool_name") or payload.get("toolName") or "")

    if tool_name in SHELL_TOOLS:
        command = tool_input.get("command")
        config_path = find_config()
        if not isinstance(command, str) or config_path is None:
            return 0  # the Bash check runs only in a project that uses qa-browser
        return gate_bash(command, config_path)

    targets = list(collect(tool_name, tool_input))
    if not targets:
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
    for kind, url in targets:
        if kind == "unresolved":
            if production_adjacent(config):
                v, r, shown = "ask", ("a script builds a request or navigation URL at run "
                                      "time that the gate cannot resolve, and production "
                                      "hosts are configured"), "(script)"
            else:
                continue
        else:
            v, r = decide(url, config, unknown="ask" if kind == "nav" else
                          ("ask" if production_adjacent(config) else "allow"))
            shown = url
        if _RANK[v] > _RANK[verdict]:
            verdict, reason, worst_url = v, r, shown

    if verdict == "allow":
        return 0

    if verdict == "ask":
        hooklib.ask(f"[qa-browser] {worst_url}: {reason}. Approve only if this is a "
                    f"non-production host; to stop this prompt, add it to allowedHosts "
                    f"in {CONFIG_FILENAME}.")
        return 0

    return _block(worst_url, reason)


if __name__ == "__main__":
    hooklib.run(main)  # fail open: the gate is best-effort, never a crash-blocker
