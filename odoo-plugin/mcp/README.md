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
| `tools.py` | The eleven tool schemas, their handlers, per-call routing and the result tag |
| `odoo_client.py` | Version-adaptive transport — JSON-2 on Odoo 19+, XML-RPC on 18 and older |
| `config.py` | `profiles.json` schema v2, folder → project matching (git worktrees included), live reload with last-good fallback, v1 read-only loading, validated `save()` |
| `session.py` | Per-session routing: instance → effective mode → cached client, `db: "auto"`, production unlock and expiry, audit log |
| `guards.py` | Single owner of every access decision, plus credential redaction |

Each concern has one owner. Tools ask `guards` for permission; they never re-implement a
rule locally.

## Configuration

**One file:** `~/.odoo-mcp/profiles.json`, one per Windows account. `ODOO_MCP_HOME` relocates
the store (tests use it). Full reference: `../config/odoo-mcp.profiles.json.example`.

```json
{"version": 2,
 "projects": {
   "acme": {"paths": ["C:/work/acme"], "default": "stage",
            "instances": {
              "stage": {"url": "https://acme-stage.odoo.com", "db": "auto", "username": "admin",
                        "api_key": "...", "tier": "stage", "access": "write"},
              "prod":  {"url": "https://acme.odoo.com", "db": "acme-main-1", "username": "mcp_readonly",
                        "api_key": "...", "tier": "prod", "access": "read"}}}}}
```

- **Project.** The one whose `paths` contain the session folder (`ODOO_MCP_PROJECT_DIR`, else
  the working directory). The longest path wins. A git worktree also counts as its main
  checkout, but only when git's back-pointer confirms it. Nothing else selects a connection:
  no pins, no environment profile, no global default.
- **Instance.** Every tool takes `instance` (`"prod"` or `"project/instance"`), else the
  project's `default`. The first line of every result is
  `[project/instance · database · access]`.
- **Limits.**
  - `access` (`read` / `write` / `full`) is the limit. Local and stage instances work at it.
  - A `prod` instance stays read-only until `odoo_session action=unlock`. The unlock needs the
    developer's verbatim yes, lasts 30 minutes by default (120 at most), stays in memory for
    this session and is audited.
  - `tier` must be written for any remote url. `local` needs a loopback url.
- **Databases.** `db: "auto"` (local/stage) uses the one database the url serves, and re-checks
  it after an Odoo.sh rebuild without storing anything. A fixed database is never followed; a
  missing one is reported with what the url now serves.
- **Reload.** The file is re-read whenever it changes. A broken edit keeps the last valid
  version serving, with a warning. A broken instance fails alone.
- **Old files.** A version-1 file loads **read-only**, as `legacy/<name>`, until
  `odoo_mcp.py migrate`.

The developer-side CLI lives outside this package, in `scripts/mcp/`. That keeps the server
free of any process-execution path, and the tests enforce it. `odoo_mcp.py` provides
`check | add | bind | remove | local | migrate` and is the only writer of the file:
- every write is validated, backed up to `~/.odoo-mcp/backups/` and replaced atomically;
- a change that widens a remote instance needs the developer's yes (`--approved-by`, or their
  own terminal) and is written to `audit.log`;
- a hook blocks direct edits of the file.

### What the limits do and do not guarantee

`access` in the file is the hard limit: no call, unlock or session action exceeds it. The
production unlock and `--approved-by` are procedural: they record the developer's verbatim
answer, and Claude is instructed never to supply one itself. A process that runs as you could
still edit the file through a shell. Keep production at `access: read` unless you need writes,
and use a dedicated least-privilege Odoo user for every remote instance.

Keys may be written directly in the file, which lives in your user profile. `"${VAR}"` also
works; an unset variable is reported for that instance, never sent as an empty key.

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
python -m pytest tests/mcp
```

| File | Covers |
|---|---|
| `test_config.py`, `test_session.py` | Schema rules, folder and worktree matching, reload, v1 read-only, unlock and expiry, `db: "auto"` |
| `test_mcp_server.py`, `test_mcp_routing.py` | The real process over stdio; routing, the result tag, the prod gate, rebuild follow-up, against fake Odoo servers on 127.0.0.1 |
| `test_call_guard.py`, `test_nested_commands.py` | Every write gate, including `odoo_call` and nested x2many commands |
| `test_cli.py`, `test_migrate.py` | `odoo_mcp.py`: the widening gate, key handling, local provisioning, migration |

No real Odoo instance is needed. Guards resolve before a socket is opened.

## Troubleshooting

The server launches as `python`. If that name does not resolve (some Linux distributions
ship only `python3`), set `ODOO_MCP_PYTHON` to the interpreter to use. Python 3.10+.

To see startup diagnostics, run it directly — it logs to stderr and waits on stdin:

```
python mcp/server.py
```
