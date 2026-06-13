# Odoo DB & Snapshot Safety (reference)

Detail for the `odoo-stack-doctor` skill's **Stack & DB lifecycle safety** section.
Every command uses generic placeholders — substitute your own values:

- `<db>` — a database name · `<src>` / `<dst>` — clone source / destination DB
- `<port>` — an Odoo HTTP port · `<gevent-port>` — the longpolling/gevent port
- `<config>` — an Odoo config file · `<odoo-root>` — the Odoo source checkout root
- `<module>` — a module technical name · `<snapshot>` — a baseline dump file

---

## 1. Back up + checksum a baseline before you regenerate it

A "vanilla"/baseline snapshot is load-bearing — restore points depend on it. Before
regenerating or replacing one, copy the existing artifact aside and record a checksum
so the change is reversible and tamper-evident:

```bash
cp "<snapshot>" "backup/<snapshot>.$(date -u +%Y%m%dT%H%M%SZ).bak"
sha256sum "<snapshot>" "backup/<snapshot>."*.bak     # record both, verify the copy
```

Only after the new snapshot is built **and validated** (restore it into a throwaway DB,
confirm it boots and the expected modules are present) do you repoint the restore runbook
at it. Keep the previous snapshot until the new one has been proven.

## 2. Change a baseline with a real Odoo uninstall/upgrade — not a SQL hack

To remove or change a module's footprint in a baseline DB, run a **real** Odoo
uninstall/upgrade, never hand-deletes in SQL. A SQL `DELETE` leaves orphaned
`ir_model_data`, view records, columns, and ACL rows that resurface on the next load:

```bash
# real uninstall (module record set to 'to remove', then processed at init)
python <odoo-root>/odoo-bin -c <config> -d <db> --stop-after-init \
  -u base                                  # after marking <module> for uninstall
```

Verify zero leftovers afterward (no `ir_model_fields` row for removed fields, no orphan
view, no dropped-but-referenced column). Treat a clean uninstall + leftover audit as the
definition of done.

## 3. Clone Odoo DBs with a tool that copies the FILESTORE

An Odoo database is **DB rows + a filestore** (attachments/images live on disk, the rows
only reference them). A clone that copies SQL but not the filestore produces a DB whose
attachments are all broken.

```bash
# GOOD — copies SQL AND filestore:
python <odoo-root>/odoo-bin db duplicate <src> <dst>
#   or, programmatically, the same call the web DB-manager uses:
#   env['ir.module.module']  ... or service db.exp_duplicate_database(<src>, <dst>)

# GOOD — full portable dump (zip contains manifest.json, dump.sql, filestore/):
python <odoo-root>/odoo-bin db -c <config> dump <db> "<db>.zip"
python <odoo-root>/odoo-bin db -c <config> load <dst> "<db>.zip"
```

```bash
# BAD — copies SQL ONLY; the filestore is NOT copied -> every attachment breaks:
psql -c "CREATE DATABASE <dst> TEMPLATE <src>"
createdb -T <src> <dst>
```

> The `pre_odoo_restart_guard.py` advisory hook nudges on `CREATE DATABASE ... TEMPLATE`
> / `createdb -T` for exactly this reason. For QC, duplicate into a **disposable** DB and
> run module updates there (`--max-cron-threads=0`); never mutate the live instance.

## 4. Re-inventory before any destructive DB action on a SHARED instance

A dev/QC Postgres instance is often **shared** across parallel sessions, so its DB
inventory can change underneath a paused task. Before any `dropdb` / `DROP DATABASE` /
restore-over:

```bash
psql -l                                              # current inventory (don't assume it)
psql -d <db> -c "SELECT pid, usename, state, query FROM pg_stat_activity WHERE datname='<db>';"
```

If another session holds live connections, **stand down** — do not drop a DB with active
connections or one that may belong to another track. Duplicate a known baseline instead
of editing it in place.

## 5. Multi-instance isolation (run several stacks side by side)

To run multiple Odoo instances concurrently without session/port/db collisions, give each
its **own** of everything:

| Axis | Rule |
|---|---|
| Hostname | a distinct `<name>.localhost` per instance (browsers scope the session cookie per host; `*.localhost` resolves to loopback with no hosts-file edit) |
| Ports | its own HTTP `<port>` **and** `<gevent-port>` (longpolling) pair |
| `db_filter` | a regex that matches only that instance's DBs, e.g. `^<name>.*$` |
| Filestore | its own `data_dir` |
| Log | its own logfile (so a redirected launch never looks "silent") |
| `addons_path` | the correct per-instance path; first match per path wins, so order matters |

Putting two instances on the same host/port/`db_filter` causes cross-login bleed, bind
failures, and the wrong DB being served.

## 6. Keep local-dev config separate from container/Docker config

The Docker/container config (`db_host=<service>`, container `/opt`-style paths) does not
work for a bare-metal local run, and **mutating it to debug locally risks the container
setup**. Create a **separate** local config:

- a NEW `<config>` (e.g. a local-only conf) — never edit the Docker one for local work;
- `db_host = False` to use the local Unix socket (peer auth as your OS user) where that is
  how the local Postgres is reachable, or the real local host/port otherwise;
- `data_dir` under the repo, `workers = 0` for a simple debug run;
- `addons_path` = the framework addons plus the parent dir of your custom `<module>`.

Source-built Python deps (psycopg2, python-ldap, etc.) compile only with the C toolchain
+ dev headers present — verify the toolchain **before** `pip install` so the build does
not fail partway.

---

### See also

- `skills/docker/references/volume-and-pg-safety.md` — volume copy-forward, `PG_VERSION`.
- `skills/upgrade/references/theme-load-and-cli-upgrade.md` — CLI-vs-RPC upgrade, theme load.
- `hooks/pre_odoo_volume_guard.py` — Bash hard block on blind volume destruction.
- `hooks/pre_odoo_restart_guard.py` — Bash advisory on unbounded readiness polls,
  `pkill && odoo-bin` chains, and `psql TEMPLATE` clones.
