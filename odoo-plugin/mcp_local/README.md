# `odoo-local` — MCP server for local Odoo services

The odoo plugin ships two stdio MCP servers (both in `.mcp.json`, both standard-library Python):

| Server | Scope | Touches processes? |
|---|---|---|
| `odoo` (`mcp/server.py`) | Record data on instances in `~/.odoo-mcp/profiles.json` (tiers local / stage / prod) over JSON-RPC | Never. Its tests forbid any process or shell path. |
| `odoo-local` (`mcp_local/server.py`, this folder) | **Local services only**: loopback Odoo processes and Postgres clusters in `~/.odoo-mcp/local-services.json` | Yes — start, stop, logs, module jobs, local DBs, cleanup |

Tools appear as `mcp__plugin_odoo_odoo-local__<tool>`.

## Isolation

- Its own file, **`~/.odoo-mcp/local-services.json`**. It never reads or writes `profiles.json`
  (stage/prod live there and are written only by `scripts/mcp/odoo_mcp.py`).
- The writer (`registry.py`) refuses any entry whose `db_host`, `url`, `host` or
  `http_interface` is not loopback (`localhost`, `127.x`, `::1`, `*.localhost`, a unix socket
  or empty). A stage or production instance therefore cannot appear in the file.
- Writes are atomic (temp file + replace), locked, and backed up (last 10) to
  `~/.odoo-mcp/local-backups/`. Prefer `local_discover` over hand edits; the
  `guard_core_odoo` hook does not block this file.
- Set `"pinned": true` on an entry to stop `local_discover` from refreshing it.

Entry fields: `id, project, odoo_version, runtime (wsl|linux|windows|docker), wsl_distro, cwd,
python, odoo_bin, conf, http_port, gevent_port, db_host, db_port, main_db, systemd_unit,
logfile, data_dir, created_by ("odoo-local"), created_at, discovered_at, warnings, pinned`.

## Full access inside the scope, two rails that never switch off

No per-call confirmation is needed for discover / status / start / stop / restart / logs /
module install-upgrade / DB list-create-clone. (Claude Code still asks for MCP tool permission
until the developer allows `mcp__plugin_odoo_odoo-local__*` in their settings.)

Destructive DB work keeps two rails with **no override argument**:

1. **Keep-list** — never dropped: any service's `main_db`; for a service without `db_name`,
   every DB its filter matches (`dbfilter`, and the misspelled `db_filter` that Odoo ignores
   but the developer meant); for a service with neither, every non-scratch-named DB on its
   cluster ("main DB of <service> unknown"); a DB with open connections; a DB active in the
   last 7 days (last login / attachment / module write, or filestore mtime); a DB whose
   activity cannot be read; and template DBs named in fast-test state files
   (`~/.config/*/fast/*.env`). The cleanup plan also keeps any DB whose name contains
   `prod|bk|backup|baseline|golden|reference|vanilla|e2e` unless the name is also
   scratch-style.
2. **Dump before drop** — a DB of 200 MB or more, every plan item with `backup: true` (always
   set for a DB proposed for inactivity alone, or one with a reference-copy word), is
   `pg_dump -Fc`'d to `~/odoo-backups/odoo-local_<date>/<db>.dump` and its TOC checked (one
   `TABLE DATA` entry per table) before `DROP DATABASE` — without `FORCE`, so a DB in use fails
   rather than breaking a session. The result carries the `pg_restore` line.

Path removal goes through one guard: absolute path, strictly below an allowed root
(`<data_dir>/filestore`, the services' log directories), never a root itself, never `$HOME`.

## Execution

- **WSL from Windows**: `wsl.exe -d <distro> -- bash -s`, script on **stdin**. The request
  travels as base64 JSON; the agent (`agent.py`) runs as `python3 -` from a quoted heredoc. No
  command text is ever quoted through `bash -lc "..."`, which is how an empty `$var` once turned
  `rm -rf ~/.local/share/Odoo/$d` into a wipe of every filestore.
- **Linux**: the same script through local `bash -s`. **Windows-native Odoo**: `agent.py` runs
  by path with the current Python. **Docker**: listed, not managed (use the docker skill).
- Every subprocess inside the agent is an argv list; nothing reaches a shell.
- Servers start as **`systemd-run --user --unit=odoo-<id> --collect`** with the venv `bin` on
  `PATH` (a venv python started by path loses the venv on Odoo's first self-reload). `nohup`
  inside a `wsl --` call dies when the call returns.
- **Durability caveat**: with `Linger=no` the systemd user manager stops user units when the
  last WSL session closes (~20 s after the starting call returns, measured). `local_start` and
  `local_discover` warn when linger is off; enabling it (`loginctl enable-linger <user>`) is the
  developer's one-time decision. WSL's VM idle-stop is a separate problem (env-doctor plugin).
- Stop = the PID holding the listening port, verified to be Odoo with this conf (never
  `pkill -f`), via its unit when it has one; SIGTERM, SIGKILL after 15 s.
- Long work (module `-i`/`-u`, DB create, DB clone) is a **background job**: the tool returns a
  `job_id` at once; `local_job` reports `running | finished | died`, exit code, ERROR/CRITICAL
  count, module states, test summary and a verdict that does not trust the exit code alone.
  Jobs live in `~/.cache/odoo-local/jobs/<id>/` inside the runtime; the index in
  `~/.odoo-mcp/local-jobs.json`.
- Clones use Odoo's `exp_duplicate_database`, so the filestore is copied too.

## Tools

| Tool | Does |
|---|---|
| `local_discover` | Scan distros (`~/.config/*/*.conf`, `conf/*.conf` under `~/workspace`) and the Windows project folder; write entries; report PG clusters, running `odoo-bin`, conf traps (`db_filter` typo, `db_name`+`dbfilter`, conf `dev_mode`, shared ports, linger) |
| `local_services` | Status per service: listening, PID, owner matches conf, uptime, HTTP status, server version, unit state |
| `local_start` / `local_stop` / `local_restart` | As above; bounded readiness (default 40 s, max 90) |
| `local_logs` | Tail the conf logfile or the unit journal; `grep`, `errors_only` (by log level), `since`, `pid` |
| `local_module` + `local_job` | Background `-i`/`-u` (optionally `--test-enable --test-tags`) and its result |
| `local_db` | `list` / `create` (job) / `clone` (job) / `drop` (rails) |
| `local_cleanup_plan` / `local_cleanup_apply` | See the contract below |
| `local_snapshot` / `local_relaunch` | Save running servers before a WSL restart; bring them back as `odoo-restored-N` units |

## Contract: `local_cleanup_plan` (consumed by env-doctor's cleaning skill)

Stable. Consumers must ignore keys they don't know. Changed in 4.1.1: the default response is a
**summary**; full lists are paged.

**Item and keep shapes (unchanged):**
`item = {kind, target, size_bytes, reason, action, backup}`, `keep = {target, reason}`.

- `kind`: `scratch_db` (action `drop`), `orphan_filestore` (`delete`), `dead_conf` (`archive`:
  moved to `<conf dir>/_archive_<YYYYMMDD>/`, never deleted), `stale_log` (`delete`).
- `target`: a database is `<distro>:<pg port>/<db name>`; a path is `<distro>:<absolute path
  inside that runtime>` (`local:` on a Linux host).
- `backup`: `true` means the DB is dumped and TOC-verified before the drop. It is `true` for
  every DB proposed only because it is inactive; `false` only for a small scratch-named DB.

**Default response (`view: "summary"`)** — sized to show a user (~7 KB for ~600 items):

```json
{
  "plan_id": "plan-20261106201420-220afb6530", "view": "summary",
  "created_at": "...", "expires_at": "...", "distro": "Ubuntu", "total_bytes": 41304705958,
  "items_total": 586, "keep_total": 186,
  "plan_file": "C:\\Users\\<you>\\.odoo-mcp\\local-plans\\plan-....json",
  "summary": {
    "by_kind": {"scratch_db": {"count": 533, "bytes": 40779269995, "with_backup": 529}, "...": {}},
    "scratch_db_groups": [{"group": "Ubuntu:5434 medline*", "count": 120, "bytes": 0}],
    "scratch_db_groups_total": 40,
    "keep_reasons": {"recent or not scratch": 133, "main_db": 35, "reference-copy name": 4}
  },
  "items": ["... the 20 largest items, item shape ..."],
  "keep": ["... up to 20 main-DB / reference-copy keeps, keep shape ..."],
  "more": "how to page"
}
```

**Full lists (`detail: true`)** — `{..., "view": "page", "offset", "limit", "items": [...],
"keep": [...], "next_offset"?}`: `items[offset:offset+limit]` and `keep[offset:offset+limit]`
(limit default 100, max 500); `next_offset` is present while either list has more. Pass
`plan_id` to page a stored plan without scanning again. The stored plan file (`plan_file`,
JSON `{"plan": {plan_id, items, keep, ...}, ...}`) always holds the complete lists.

With several distros the tool returns `{"plans": [<view>, ...]}`. Orphan filestores are
proposed only when every cluster could be listed; otherwise `keep` says why they were not
judged.

`local_cleanup_apply {plan_id, only?: [target, ...]}` executes only items of that stored,
unexpired (24 h), not-yet-applied plan, re-validating each against live state (the keep-list,
filters and path guard run again at apply time). A refused item is reported and skipped; an
unexpected error stops the run. Applying a whole plan applies every stored item, not only the
20 shown in the summary — show the summary totals to the user before applying.

When `odoo-local` is not available, a consumer should fall back to a generic Postgres inventory.
