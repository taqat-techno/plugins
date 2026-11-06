#!/usr/bin/env python3
"""Builds a lean, host-neutral package of the Microsoft 365 server into --out DIR.

It follows the vendor-neutral Agent Plugins layout (plugin.json, mcp.json, skills/) so a host that cannot run
Claude Code hooks or commands - for example an OpenClaw bot - loads only the MCP server and one bot-facing skill.
The package starts the server in READ-ONLY mode (M365_READONLY=true), so write tools are not even listed; to allow
writes, remove that line from mcp.json on purpose (and give the bot its own approval step for sends).

Single source: every file is derived from this plugin (server/, data/tools.json, data/agent_skill.md, the version
in .claude-plugin/plugin.json). The package is built on demand and is deliberately not committed inside this
plugin: a SKILL.md outside skills/ would look like an undiscoverable skill to validate_marketplace.py, and a copy
would drift.

    python scripts/build_agent_plugin.py --out <dir>
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"


def _lf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def _json(obj) -> bytes:
    return (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


README = """# m365 (agent package)

Microsoft 365 tools (mail, calendar, Teams chats, OneDrive, people, alerts) for agent hosts that load Agent Plugins,
such as OpenClaw bots. Generated from the `m365` plugin by `scripts/build_agent_plugin.py`; do not edit by hand.
No npm packages and no admin rights: it needs only Node 18+.

## Set up

1. An admin registers one Microsoft app once: `docs/APP_REGISTRATION.md`. You get a client ID.
2. Set these in the environment of the process that runs the host:

| Variable | Meaning |
|---|---|
| `M365_CLIENT_ID` | The app's client ID (required) |
| `M365_TENANT` | Optional, default `organizations` |
| `M365_HOME` | Where the profile and sign-in cache live, default `~/.m365-plugin`. Give each bot or person its own |
| `M365_MODULES` | Optional: `mail,calendar,teams,channels,meetings,people,files` |
| `M365_REFRESH_TOKEN_FILE`, `M365_CLIENT_SECRET_FILE` | Optional: reuse another tool's saved sign-in (a file with its refresh token, and one with the app's secret) |
| `M365_ATTACH_DIRS` | Optional: folders local files may be attached to drafts from (`;`-separated on Windows). Set by the person only |
| `M365_DOWNLOAD_DIR` | Optional: the one folder attachments and OneDrive files may be saved into (never overwriting). Set by the person only |
| `M365_SIGNATURE_FILE` | Optional: an HTML email signature file; drafts become HTML built by the plugin with that signature |
| `M365_REDIRECT_URI` | Optional: the app's one registered redirect, e.g. `http://localhost:8400/callback`, when the app allows no other (often an app with a secret; then also set `M365_CLIENT_SECRET_FILE` and sign in with `cli.mjs sign-in --interactive`) |
| `M365_SCOPE_MODE` | Optional: `app` uses the permissions already approved for the app (no new admin request) |

3. Sign in once by hand as the account the bot should act as: `node server/cli.mjs sign-in --device-code`.
   The refresh token is saved under `M365_HOME` and reused.

## Read-only by default

`mcp.json` sets `M365_READONLY=true`: write tools are not listed and only read permissions are requested.
To let the bot send mail, schedule meetings and post to Teams, remove that line. Do this only for a bot that asks
its owner before every send (`data/tools.json` lists the tools: `write`, and `confirm` for the outward-facing ones).
Changing it adds permissions, so run the sign-in again.

## Alerts

`events_since` (a tool) or `node server/cli.mjs events --since now` then `--since <cursor>` returns what concerns
the signed-in person: new mail, mentions, Teams messages, calendar invitations. It stores nothing: keep the cursor
and deliver the events yourself. If `more` is true, poll again.
"""


def build() -> dict:
    manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    files = {
        "plugin.json": _json({
            "name": "m365",
            "version": manifest["version"],
            "description": "Microsoft 365 tools (mail, calendar, Teams chats, OneDrive, people, alerts) for agent hosts. Read-only by default.",
            "license": manifest.get("license", "MIT"),
        }),
        "mcp.json": _json({
            "$schema": SCHEMA,
            "mcpServers": {
                "m365": {
                    "type": "stdio",
                    "command": "node",
                    "args": ["${PLUGIN_ROOT}/server/index.mjs"],
                    "env": {"M365_READONLY": "true"},
                }
            },
        }),
        "skills/m365/SKILL.md": _lf((ROOT / "data" / "agent_skill.md").read_bytes()),
        "data/tools.json": _lf((ROOT / "data" / "tools.json").read_bytes()),
        "docs/APP_REGISTRATION.md": _lf((ROOT / "docs" / "APP_REGISTRATION.md").read_bytes()),
        "README.md": README.encode("utf-8"),
        "LICENSE": _lf((ROOT / "LICENSE").read_bytes()),
    }
    for f in sorted((ROOT / "server").rglob("*.mjs")):
        files["server/" + f.relative_to(ROOT / "server").as_posix()] = _lf(f.read_bytes())
    return files


def main(argv) -> int:
    if len(argv) != 2 or argv[0] != "--out":
        print("usage: build_agent_plugin.py --out <dir>", file=sys.stderr)
        return 2
    out = Path(argv[1]).resolve()
    if out == ROOT or ROOT in out.parents:
        print("refusing to build inside the m365 plugin itself; pick a directory outside it", file=sys.stderr)
        return 2
    if out.is_dir() and any(out.iterdir()) and not (out / "plugin.json").is_file():
        print(f"refusing to write into non-empty {out} (no plugin.json: not a previous build)", file=sys.stderr)
        return 2
    files = build()
    for rel, data in files.items():
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)  # bytes, so Windows never rewrites line endings
    print(f"wrote {len(files)} files to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
