# Contract with the odoo plugin's `odoo-local` MCP server

The odoo plugin (separate plugin, separate maintainers) ships a local-services MCP server,
`odoo-local`, whose `local_cleanup_plan` tool produces the Odoo-specific half of a cleanup:
scratch databases, orphan filestores, dead confs, stale logs. This skill consumes it **when
the tool is available in the session**, and works without it (generic Postgres + filestore
inventory).

Tool names as Claude Code exposes them follow the plugin namespacing rule
`mcp__plugin_<plugin>_<server>__<tool>`, so expect `mcp__plugin_odoo_odoo-local__local_cleanup_plan`
(check the session's tool list; do not assume an un-namespaced form).

## Shape consumed

The authoritative definition is the odoo plugin's `mcp_local/README.md` ("Contract:
`local_cleanup_plan`"); it is declared stable, and consumers ignore keys they do not know.
As of 2026-11-06:

```json
{
  "plan_id": "plan-20261106194104-e013e90862",
  "items": [
    {"kind": "scratch_db", "target": "Ubuntu:5434/kg_qa", "size_bytes": 90479639,
     "reason": "inactive 83 days", "action": "drop", "backup": false}
  ],
  "keep": [{"target": "Ubuntu:5434/PearlPixels", "reason": "main_db of service pearl-pixels-18"}],
  "created_at": "...", "expires_at": "...", "distro": "Ubuntu", "total_bytes": 0
}
```

- `kind`: `scratch_db` (`drop`), `orphan_filestore` (`delete`), `dead_conf` (`archive` into
  `<conf dir>/_archive_<YYYYMMDD>/`), `stale_log` (`delete`).
- `target`: a database is `<distro>:<port>/<db>`; a path is `<distro>:<absolute path>`
  (`local:` on a Linux host).
- With several distros the tool returns `{"plans": [<plan>, ...]}`.

## How the plans merge (`plan.py build --odoo-plan <file>`)

`merge_odoo()` normalises targets to env-doctor's form (`<db>@<port>`, plain paths) and kinds
(`scratch_db` → `db`, `orphan_filestore` → `filestore`, `dead_conf` → `conf`, `stale_log` →
`log`), then:

1. A plan for another distro than the inventory's is not merged (noted).
2. odoo-local `keep` entries join the kept list.
3. Each `drop` / `archive` / `delete` item is added with `source: "odoo-local"`, its
   `odoo_plan_id` and its original `odoo_target`, **unless** env-doctor's keep-list covers it
   (same database name, same path, or a keep-file pattern) — then it is left out with a note.
   env-doctor's rails always win.
4. An item env-doctor already plans (same kind and target) is not duplicated; env-doctor's
   scripts apply it once.
5. Unknown actions and unknown keys are ignored.

If the published shape changes, update this file, `merge_odoo()` and
`tests/test_cleanup_plan.py::test_odoo_local_published_contract_shape` together.

## How they are applied

`plan.py emit` writes only env-doctor's own items to the apply lists. Items with
`source: "odoo-local"` are applied with
`local_cleanup_apply {plan_id: <odoo_plan_id>, only: [<odoo_target>, ...]}` after the user
approved the merged env-doctor plan id that contains them (and before the odoo plan's 24 h
expiry). The odoo tool re-runs its own keep-list and path guard at apply time.

## Before a WSL restart

When the plan leads to a compaction (or anything else that stops the VM), use
`local_snapshot` before and `local_relaunch` after if they exist; otherwise snapshot the
running servers' working directory and command line yourself and relaunch them as
`systemd-run --user` units (see `env-doctor-router/references/windows-wsl.md`).
