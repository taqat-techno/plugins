#!/usr/bin/env python3
"""Builds a lean, host-neutral package of the Azure DevOps connection into --out DIR.

It follows the vendor-neutral Agent Plugins layout (plugin.json, mcp.json, skills/) so a
host that cannot run Claude Code hooks, commands or subagents - for example an OpenClaw
bot - loads only the MCP launcher and one bot-facing skill. The package starts the server
in READ-ONLY mode (ADO_PLUGIN_READONLY=true) so a bot cannot write even if its prompt is
subverted; to allow writes, edit mcp.json on purpose.

Single source: every file is derived from this plugin (launcher, data/write_tools.json,
data/agent_skill.md, the version in .claude-plugin/plugin.json). The package is built on
demand and is deliberately not committed inside this plugin: a SKILL.md outside skills/
would look like an undiscoverable skill to validate_marketplace.py, and a copy would drift.

    python scripts/build_agent_plugin.py --out <dir>   # (re)write the package into <dir>
    openclaw plugins install <dir>                     # OpenClaw example
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


def build() -> dict:
    """Returns {relative path: bytes} for every file of the package."""
    manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    readme = (
        "# azure-devops (agent package)\n\n"
        "Read-only Azure DevOps access for agent hosts that load Agent Plugins, such as OpenClaw bots.\n"
        "Generated from the `devops` plugin by `scripts/build_agent_plugin.py`; do not edit by hand.\n\n"
        "## Set up\n\n"
        "Set these in the environment of the process that runs the host (the gateway):\n\n"
        "| Variable | Meaning |\n|---|---|\n"
        "| `ADO_ORGANIZATION` | Organization name, e.g. `contoso` |\n"
        "| `ADO_MCP_AUTH_TOKEN_FILE` | Path to a file holding a read-only PAT (first line). Preferred over the token itself |\n"
        "| `ADO_MCP_AUTH_TOKEN` | The PAT itself, if a file is not possible |\n"
        "| `ADO_MCP_PROJECT`, `ADO_MCP_TEAM` | Optional defaults |\n\n"
        "A bot has no browser, so it signs in with a PAT. Give it a PAT with read-only scopes only\n"
        "(Work Items: Read, Code: Read, Build: Read). The package also starts the server in read-only\n"
        "mode, which removes and blocks every write tool whatever the PAT can do.\n\n"
        "## Allow writes (deliberately)\n\n"
        "Remove `ADO_PLUGIN_READONLY` from `mcp.json`. Only do this for an agent that has its own\n"
        "confirmation step for writes.\n"
    )
    files = {
        "plugin.json": _json({
            "name": "azure-devops",
            "version": manifest["version"],
            "description": "Read-only Azure DevOps access (work items, sprints, pull requests, builds, search) through the pinned @azure-devops/mcp server.",
            "license": manifest.get("license", "MIT"),
        }),
        "mcp.json": _json({
            "$schema": SCHEMA,
            "mcpServers": {
                "azure-devops": {
                    "type": "stdio",
                    "command": "node",
                    "args": ["${PLUGIN_ROOT}/scripts/ado-mcp-launch.js"],
                    "env": {"ADO_PLUGIN_READONLY": "true"},
                }
            },
        }),
        "skills/azure-devops/SKILL.md": _lf((ROOT / "data" / "agent_skill.md").read_bytes()),
        "scripts/ado-mcp-launch.js": _lf((ROOT / "scripts" / "ado-mcp-launch.js").read_bytes()),
        "data/write_tools.json": _lf((ROOT / "data" / "write_tools.json").read_bytes()),
        "README.md": readme.encode("utf-8"),
        "LICENSE": _lf((ROOT / "LICENSE").read_bytes()),
    }
    return files


def main(argv) -> int:
    if len(argv) != 2 or argv[0] != "--out":
        print("usage: build_agent_plugin.py --out <dir>", file=sys.stderr)
        return 2
    OUT = Path(argv[1]).resolve()
    if OUT == ROOT or ROOT in OUT.parents:
        print("refusing to build inside the devops plugin itself; pick a directory outside it", file=sys.stderr)
        return 2
    if OUT.is_dir() and any(OUT.iterdir()) and not (OUT / "plugin.json").is_file():
        print(f"refusing to write into non-empty {OUT} (no plugin.json: not a previous build)", file=sys.stderr)
        return 2
    files = build()
    for rel, data in files.items():
        p = OUT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)  # bytes, so Windows never rewrites line endings
    print(f"wrote {len(files)} files to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
