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

## 7. De-Dockerising to a native runtime

Converting a Docker-template project to a native run is mostly the §6 config split, plus
four things that decide whether it can work at all.

**Check the `_pre_init` hooks of transitive dependencies BEFORE choosing where the database
lives.** A module's `_pre_init` hook runs DDL against the target database and raises if it
fails, so a dependency several levels down can dictate the database host. The Odoo 19 `ai`
module is the live example: its `_pre_init` executes
`CREATE EXTENSION IF NOT EXISTS vector` (pgvector) and an ordinary business app can pull it
in transitively. pgvector ships as a single distribution package on Linux and has no
prebuilt Windows binary (it needs a compiler), so on Windows the practical answer is native
Odoo against a Linux-side Postgres rather than a local Windows cluster. Enumerate the
closure and grep it first:

```bash
grep -rl "_pre_init\|pre_init_hook" --include="*.py" --include="__manifest__.py" <addons-path>
```

**On Windows, `workers` MUST be 0.** Odoo's own `requirements.txt` proves the platform
support by exclusion: `gevent` / `greenlet` / `python-ldap` / `python-magic` are pinned
`sys_platform != 'win32'`, and the win32-only entries are separate. Consequences: there is
no prefork/gevent server, `gevent_port` is inert, and websockets are served on the HTTP
port. Do not try to "fix" a slow Windows instance by raising `workers` — it is not a tuning
knob there. (`workers = 0` is a debug choice everywhere else; on Windows it is the only
option.)

**Archive the compose files before deleting them.** A compose file is the **only on-disk
record of its named volumes**. Deleting compose files never deletes volumes, so removing
them without a copy orphans the data with no way left to name it. Back up every infra file
byte-for-byte outside the repo first — deployment roots are frequently *not* git repos
(only the nested addon repo is), which makes the deletion irreversible.

**Delete the compose generator too.** These templates ship a generate/init command that
**recreates** the compose files on demand. Leave it in place and the next person (or the
next agent) regenerates the whole Docker layer over the native runtime you just built.
While you are there, check the project's own docs for a leaked admin password in a
ports/credentials table.

---

### See also

- `skills/docker/references/volume-and-pg-safety.md` — volume copy-forward, `PG_VERSION`.
- `skills/upgrade/references/theme-load-and-cli-upgrade.md` — CLI-vs-RPC upgrade, theme load.
- `hooks/pre_odoo_volume_guard.py` — Bash hard block on blind volume destruction.
- `hooks/pre_odoo_restart_guard.py` — Bash advisory on unbounded readiness polls,
  `pkill && odoo-bin` chains, and `psql TEMPLATE` clones.
