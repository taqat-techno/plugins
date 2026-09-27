# Odoo MCP server

A small MCP server that connects Claude to a **running** Odoo instance. Bundled with
`odoo-plugin`; registered through the plugin's `.mcp.json`.

## Why it looks like this

**Standard library only.** No `pip install`, no `npm`, no `uv`. If `python` runs, this
runs. A plugin distributed to a team cannot assume a particular package manager is present,
and a server that fails to start is worse than no server.

**Eleven tools.** Every MCP tool schema is injected into the context window of every session
where the server is enabled — including sessions doing pure source-code work that never
touch a live instance. Odoo MCP servers in the wild expose between 3 and 138 tools; a large
surface is a permanent tax on unrelated work. Breadth lives in parameters, not tool names.

**No credentials, no default instance.** Each developer supplies their own connection.
Nothing here is machine-specific or checked in.

**Acts as the authenticated Odoo user.** No sudo, no superuser, no SQL, no shell, no
filesystem, no module installation. Odoo's `ir.model.access`, `ir.rule` and field groups
apply to every call. The guards in `guards.py` are a second layer on top of that, not a
replacement for it.

## Layout

| File | Responsibility |
|---|---|
| `server.py` | MCP stdio transport: JSON-RPC framing, lifecycle, dispatch |
| `tools.py` | The eleven tool schemas and their handlers, database auto-follow |
| `odoo_client.py` | Version-adaptive transport — JSON-2 on Odoo 19+, XML-RPC on 18 and older |
| `profiles.py` | Profile schema (tier / ceiling / start / approval), the three stores, resolution order, learned database renames |
| `session_state.py` | Per-session active profile, mode, expiry and write scope; approval checks; grants; audit log |
| `guards.py` | Single owner of every access decision, plus credential redaction |

Each concern has one owner. Tools ask `guards` for permission; they never re-implement a
rule locally.

## Configuration

Three owners, so the configuration never becomes a mess:

| Store | Owner | Holds |
|---|---|---|
| `~/.odoo-mcp/servers.json` (legacy `profiles.json`) | developer | staging / production / shared servers |
| `<project>/.odoo-mcp.json` | developer | optional pin for one checkout |
| `~/.odoo-mcp/local/<project>.json` | `scripts/mcp/local_profile.py` | local instances, one file per checkout, expiring keys |
| `~/.odoo-mcp/state/learned.json` | the server | staging databases renamed by a rebuild |
| `~/.odoo-mcp/grants/`, `audit.log` | `scripts/mcp/odoo_mcp_ctl.py` / the server | human approvals, the audit trail |

`ODOO_MCP_HOME` relocates the whole store (tests use it).

Resolution order, first match wins (`odoo_status` reports which rule chose the profile):

1. `ODOO_MCP_PROFILE`, or the session's `odoo_session action=use`
2. `<project>/.odoo-mcp.json`
3. the local profile for this checkout
4. a server profile bound to this checkout (`"projects"`, or legacy `"project_map"`)
5. the servers file `default`, **only if it is local-tier**; a remote default is never auto-selected
6. `ODOO_URL` / `ODOO_DB` / `ODOO_USERNAME` / `ODOO_API_KEY`

Each profile carries a `tier` (local / staging / production; local requires a loopback url),
a `ceiling` (the most a session may do), a `start` mode and the `approval` needed to raise
the mode (local none, staging chat, production human). Sessions switch profile and mode
in memory with `odoo_session`, never by editing a file, so one session cannot change another.
Legacy `mode` / `production` / `allow_unlink` / `allow_production_writes` keys still load.

The developer-side CLIs live outside this package, in `scripts/mcp/`. That keeps the server
free of any process-execution path, and the tests enforce it:
- `local_profile.py provision | list | prune` sets up local connections without questions;
- `odoo_mcp_ctl.py approve | revoke | grants | audit` handles production approvals, and
  `approve` needs an interactive terminal.

Any string value may reference an environment variable as `${VAR}`, so a profile file can
be kept free of secrets. Full reference: `../config/odoo-mcp.profiles.json.example`.

Run `/mcp-setup` for a guided walkthrough.

## Which Odoo API

Chosen automatically from `server_version_info`:

| Odoo | Transport | Authentication |
|---|---|---|
| 19+ | `POST /json/2/<model>/<method>` | `Authorization: Bearer <api_key>` |
| ≤ 18 | `/xmlrpc/2/common` → `/xmlrpc/2/object` `execute_kw` | API key sent as the password |

JSON-2 is new in Odoo 19 — it does not exist on 18. The API key is accepted anywhere a
password is, and the XML-RPC path is non-interactive, so it is not blocked by 2FA.

Portability details already handled: `name_get` was removed in **18.0** (read `display_name`
instead), `fields_view_get` was removed in **17.0** (`get_views` replaces it), and
`read_group` is deprecated in 19.0 but still callable, which makes it the portable choice
across 14–19.

## Protocol

Newline-delimited JSON-RPC 2.0 over stdin/stdout. The `initialize` handshake used by
current clients is implemented; `server/discover` answers *method not found*, which the
specification's backward-compatibility rule tells a newer client to treat as a legacy
server and fall back to `initialize`. Both client generations work.

Two invariants: stdout carries protocol messages only (diagnostics go to stderr), and one
message per line with no embedded newlines. On Windows the streams are reconfigured so
`\n` is not translated to `\r\n`, which would corrupt the framing.

## Tests

```
python tests/mcp/test_mcp_server.py     # standalone
pytest tests/mcp/test_mcp_server.py     # or under pytest
```

20 tests drive the real process over stdio. No Odoo instance and no network are needed:
protocol behaviour, profile resolution and every safety guard resolve before a socket is
opened.

## Troubleshooting

The server launches as `python`. If that name does not resolve (some Linux distributions
ship only `python3`), set `ODOO_MCP_PYTHON` to the interpreter to use. Python 3.10+.

To see startup diagnostics, run it directly — it logs to stderr and waits on stdin:

```
python mcp/server.py
```
