#!/usr/bin/env python3
"""Builds a lean, host-neutral package of the Google server into --out DIR.

It follows the vendor-neutral Agent Plugins layout (plugin.json, mcp.json, skills/) so a host that cannot run Claude
Code hooks - for example an OpenClaw bot - loads only the MCP server and one bot-facing skill. Claude Code's confirm hook
is not in the package: the host gates the tools listed under "confirm" in data/tools.json itself.

The package does NOT switch on read-only mode: read-only asks for read-only scopes, so an existing sign-in that can
change data would be refused until a new sign-in. A host that wants fewer tools sets GOOGLE_TOOLS_DENY or
GOOGLE_TOOLS_ALLOW instead (no new sign-in needed).

Single source: every file is derived from this plugin (server/**/*.mjs, data/tools.json, data/google_mcp_snapshot.json,
data/agent_skill.md, docs/GOOGLE_CLOUD_SETUP.md, the version in .claude-plugin/plugin.json). Backups and other files
under server/ that are not .mjs are never copied. The package is built on demand and deliberately not committed inside
this plugin: a SKILL.md outside skills/ would look like an undiscoverable skill to validate_marketplace.py, and a copy
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


README = """# google (agent package)

Gmail, Google Calendar and Google Drive for agent hosts that load Agent Plugins, such as OpenClaw bots: a local bridge
to Google's own Workspace MCP servers, signed in with your own Google Cloud OAuth client. Generated from the `google`
plugin by `scripts/build_agent_plugin.py`; do not edit by hand. No npm packages and no admin rights: it needs only
Node 18+.

## Set up

1. Create your own Desktop app OAuth client, enable the Gmail, Calendar and Drive APIs and their MCP APIs, and tick
   "Use this client for an AI-powered agent": `docs/GOOGLE_CLOUD_SETUP.md`.
2. Set these in the environment of the process that runs the host:

| Variable | Meaning |
|---|---|
| `GOOGLE_CLIENT_SECRET_FILE` | Path to the client JSON (required). Only a path: never paste its contents anywhere |
| `GOOGLE_PLUGIN_HOME` | Where the sign-in is kept, default `~/.google-plugin`. Give each bot or person its own |
| `GOOGLE_MODULES` | Optional: `gmail,calendar,drive` (default all three; a module turned on later needs a new sign-in) |
| `GOOGLE_READONLY` | Optional: `true` asks for read-only scopes and lists no write tool. Needs its own sign-in |
| `GOOGLE_TOOLS_ALLOW` / `GOOGLE_TOOLS_DENY` | Optional: comma-separated tool names; deny wins. No new sign-in needed |
| `GOOGLE_CONFIRM_MODE` | Optional: `forward` (default: pass Google's confirmation form to the host if it declared form elicitation, else `CONFIRMATION_NEEDED`) or `error` (never forward) |
| `GOOGLE_IDENTITIES_FILE` / `GOOGLE_IDENTITIES` | Optional: the owner's addresses for `gmail_message_identity` (file path, or the JSON itself) |
| `GOOGLE_DOWNLOAD_DIR`, `GOOGLE_MAX_SAVE_MB` | Optional: the one folder `gmail_get_attachment` / `drive_save_file` save into (set by the person only), and the size limit (default 25) |
| `GOOGLE_REFUSE_GUEST_EVENTS` | Optional: `1` refuses calendar changes that involve other people (`GUESTS_NEED_APPROVAL`) |
| `GOOGLE_WRITE_LIMIT_PER_HOUR` | Optional: `N` caps trash / spam / delete / move calls per rolling hour (`WRITE_LIMIT_REACHED`) |
| `GOOGLE_ATTACH_DIRS` | Optional: folders local files may be attached from (default: `GOOGLE_DOWNLOAD_DIR`) |
| `GOOGLE_BOUNCE_CHECK_SECONDS` | Optional: seconds to look for a bounce after a send (default 10, 0 = off) |
| `GOOGLE_GMAIL_SETTINGS` | Optional: `1` requests Gmail settings scopes and adds the settings tools (new sign-in) |
| `GOOGLE_FULL_MAILBOX` | Optional: `1` requests full mailbox access and adds permanent delete / empty Trash and Spam (new sign-in) |
| `GOOGLE_REST_FALLBACK` | Optional: `1` adds the `*_rest_*` tools (Gmail reads with their own quota, send a draft, reply / forward drafts, draft edit and delete, Drive search, download, trash, move, rename, share) |
| `GOOGLE_CLI_COMMAND` | Optional: the command the owner types for this server's CLI (for example a wrapper with its own `GOOGLE_PLUGIN_HOME`); hints name it instead of `node .../server/cli.mjs`. Text only, never run |
| `GOOGLE_TIMEOUT_MS`, `GOOGLE_CONFIRM_TIMEOUT_MS`, `GOOGLE_MAX_STRING_CHARS`, `GOOGLE_MAX_RESULT_CHARS` | Optional limits |

3. Sign in once by hand, on the machine that runs the host, as the account the bot should act as:
   `node server/cli.mjs sign-in` (a browser opens). Check it with `node server/cli.mjs status`.
4. Answer Google's confirmation questions once in a terminal: `node server/cli.mjs grant`. Google keeps those answers
   for 90 days; a user cannot view or revoke them (see the setup guide).

## Classes

`data/tools.json` lists every tool: `read`, `local`, `write` (the owner's own data, reversible) and `confirm`
(calendar changes, which email other people; Gmail trash and spam; Drive create, copy and revision upload). **The host must ask the owner
before every `confirm` tool**: once the owner told Google "Always allow", Google no longer asks, so this is the last
guard. There is no tool to send mail, edit or delete drafts, share, move or trash Drive files, or delete permanently.
"""


def build() -> dict:
    manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    files = {
        "plugin.json": _json({
            "name": "google",
            "version": manifest["version"],
            "description": "Gmail, Google Calendar and Google Drive for agent hosts: a local bridge to Google's own Workspace MCP servers with your own OAuth client.",
            "license": manifest.get("license", "MIT"),
        }),
        "mcp.json": _json({
            "$schema": SCHEMA,
            "mcpServers": {
                "google": {
                    "type": "stdio",
                    "command": "node",
                    "args": ["${PLUGIN_ROOT}/server/index.mjs"],
                }
            },
        }),
        "skills/google/SKILL.md": _lf((ROOT / "data" / "agent_skill.md").read_bytes()),
        "data/tools.json": _lf((ROOT / "data" / "tools.json").read_bytes()),
        "data/google_mcp_snapshot.json": _lf((ROOT / "data" / "google_mcp_snapshot.json").read_bytes()),
        "docs/GOOGLE_CLOUD_SETUP.md": _lf((ROOT / "docs" / "GOOGLE_CLOUD_SETUP.md").read_bytes()),
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
        print("refusing to build inside the google plugin itself; pick a directory outside it", file=sys.stderr)
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
