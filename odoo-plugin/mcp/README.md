# Odoo MCP server

A small MCP server that connects Claude to a **running** Odoo instance. Bundled with
`odoo-plugin`; registered through the plugin's `.mcp.json`.

## Why it looks like this

**Standard library only.** No `pip install`, no `npm`, no `uv`. If `python` runs, this
runs. A plugin distributed to a team cannot assume a particular package manager is present,
and a server that fails to start is worse than no server.

**Ten tools.** Every MCP tool schema is injected into the context window of every session
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
| `tools.py` | The ten tool schemas and their handlers |
| `odoo_client.py` | Version-adaptive transport — JSON-2 on Odoo 19+, XML-RPC on 18 and older |
| `profiles.py` | Connection-profile resolution and the discovery assist |
| `guards.py` | Single owner of every access decision, plus credential redaction |

Each concern has one owner. Tools ask `guards` for permission; they never re-implement a
rule locally.

## Configuration

Resolution order, first match wins:

1. `ODOO_MCP_PROFILE` — explicit profile name
2. `<project>/.odoo-mcp.json` — per project (git-ignore it)
3. `~/.odoo-mcp/profiles.json` — user-wide, with an optional `project_map`
4. `ODOO_URL` / `ODOO_DB` / `ODOO_USERNAME` / `ODOO_API_KEY`

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
