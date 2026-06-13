---
name: odoo-stack-doctor
description: |
  Diagnostic checklist for an Odoo Docker stack that "comes up clean but is wrong" — data silently orphaned, Postgres refusing to boot, an upgrade that ran but changed nothing, or a website theme that renders blank. Covers: a compose mount-point change orphans the old named volume (migrate data forward with cp -a, never `down -v`); never regenerate a pinned non-template Postgres major without preserving the deviation (forward-incompatible data dir); upgrade modules via the odoo-bin CLI --stop-after-init, NOT the RPC immediate-upgrade button (the website module can hijack it into a configurator action and silently skip the translation reload); on a fresh DB the theme content only materializes when the theme-load post-copy step runs (assigning theme_id is intent, not load) — trigger or re-trigger it after languages are active; and a theme-to-concrete mirror must list every translatable field in its translated-fields mapping or non-default-language translations are silently dropped. It is also the canonical safe stack & DB lifecycle runbook: start a standalone Postgres that has no auto-start via its own pg_ctl (a WAL-crash-recovery timeout/exit is not automatically failure — verify with pg_isready + the server log); re-inventory a SHARED QC instance and check pg_stat_activity before any destructive DB action; restart hygiene (kill by resolved PID, never `pkill ... && odoo-bin` in one chain because the pkill self-matches and SIGTERMs the chain with exit 144, split stop/start into separate calls, confirm the port is free, tail the correct logfile); BOUNDED readiness polling only (never an unbounded `curl --retry-connrefused` against an Odoo port — it can retry-storm the backend); verify the real install/upgrade result from the LOG, not the shell-wrapper/background exit code; clone DBs with a filestore-aware duplicate (`odoo-bin db duplicate`), never `psql ... TEMPLATE`; and keep a separate local config (never mutate the Docker conf for local debugging). Odoo-version-aware (14-19). Activates on data-loss-risk volume operations, Postgres version-mismatch boot failures, "upgrade ran but nothing changed", "theme selected but page is blank", a standalone Postgres that won't start, restart/exit-144/port-collision symptoms, unbounded readiness polling, or DB clone/snapshot operations.
version: 0.2.0
last_reviewed: 2026-06-13
license: "MIT"
metadata:
  mode: codebase
  odoo-versions: ["14", "15", "16", "17", "18", "19"]
  categories: [docker, postgres, volumes, upgrade, theme, troubleshooting, data-safety, lifecycle, restart, readiness, clone]
  bashPattern: ["docker compose", "docker volume", "odoo-bin", "stop-after-init", "pg_ctl", "pkill", "createdb", "psql"]
  model: sonnet
owns:
  - the mount-point-change -> orphan-volume diagnosis (migrate forward, never down -v)
  - the preserve-the-running-Postgres-major rule (forward-incompatible data dir)
  - the CLI-upgrade-over-RPC rule (RPC hijacked by website configurator silently skips reload)
  - the theme-load-after-languages rule (theme_id is intent; post-copy hook materializes content)
  - the theme-translated-fields-mapping completeness rule (silent drop on non-default languages)
  - the standalone-Postgres lifecycle rule (own pg_ctl; WAL-recovery timeout/exit is not failure)
  - the shared-instance safety rule (re-inventory + pg_stat_activity before destructive DB action)
  - the restart-hygiene rule (kill by PID; never `pkill && odoo-bin`; split stop/start; tail the right log)
  - the bounded-readiness-poll rule (never an unbounded `curl --retry-connrefused`)
  - the verify-install-from-log rule (not the wrapper/background exit code)
  - the filestore-aware clone rule (`odoo-bin db duplicate`, never `psql TEMPLATE`)
  - the separate-local-config rule (never mutate the Docker conf for local debugging)
defers_to:
  - skills/stack-doctor/references/db-safety.md (snapshot backup, filestore-aware clone, multi-instance isolation, local-vs-docker config)
  - skills/docker/references/volume-and-pg-safety.md (volume/PG detail, copy-forward + PG_VERSION commands)
  - skills/upgrade/references/theme-load-and-cli-upgrade.md (theme-load + CLI-upgrade + mapping detail)
  - skills/docker/SKILL.md (compose generation, deployment, container debugging)
  - hooks/pre_odoo_volume_guard.py (hard-blocks blind volume destruction at the Bash layer)
  - hooks/pre_odoo_restart_guard.py (advisory nudges: unbounded readiness poll, pkill&&odoo-bin chain, psql TEMPLATE clone)
  - claude-env-doctor-plugin (generic Windows/WSL/Git-Bash environment troubleshooting)
---
<!-- Last updated: 2026-06-13 -->

# Odoo Stack Doctor Skill

The dangerous failures on an Odoo Docker stack are the ones where the stack
**comes up looking healthy** but is silently wrong: data orphaned in an
abandoned volume, Postgres refusing to boot after a regeneration, an upgrade
that "ran" but reloaded nothing, or a theme that is selected but renders blank.
This skill is the checklist for those four. Deep per-rule detail and the exact
commands live in the two reference files; read them when applying a fix.

## When to use

Activate when any of these appears:

- A `docker compose down -v`, `docker volume rm`, or `docker volume prune` is
  about to run on a stack (the `pre_odoo_volume_guard.py` hook also hard-blocks
  these unless an explicit override token is present).
- A volume mount point or named-volume key in `docker-compose.yml` was changed,
  and the stack now 500s on the first request that needs the filestore.
- Postgres refuses to boot after a compose regeneration with a
  "database files are incompatible with server" / version-mismatch error.
- An upgrade "ran" but nothing changed — stale translations, missing migration
  effects — especially on a website-enabled instance.
- A theme is selected in settings but the homepage renders blank or generic, or
  a theme-backed field is untranslated in every non-default language.
- A standalone Postgres won't start (refused connection on its port; stale
  `postmaster.pid`), or `pg_ctl` "timed out"/exited non-zero on a start.
- A restart self-kills (exit 144), Odoo ports collide, or a background `-i`/`-u`
  was reported "exit 0" but the DB is broken.
- A readiness poll (`curl --retry-connrefused …`) is about to run against an Odoo
  port, or a DB is about to be cloned / dropped / restored (the
  `pre_odoo_restart_guard.py` hook also nudges on the unbounded-poll, `pkill &&
  odoo-bin`, and `psql TEMPLATE` shapes).

For generic Windows / WSL / Git-Bash environment problems (PATH, line endings,
Docker Desktop integration, MSYS path translation in general), defer to the
**claude-env-doctor** plugin — do not re-diagnose those here.

## The four diagnoses

### 1. A mount-point change orphans the old volume — migrate forward

Editing a volume mount in `docker-compose.yml` (renaming the named volume, or
changing the container path the filestore/DB mounts at) does **not** move the
data. Docker creates a fresh **empty** volume for the new mount and leaves the
old one orphaned — still holding every byte, just no longer attached.

Failure signature: the stack comes up "clean," the DB may even initialize fresh,
and the **first request that needs the filestore 500s** because the attachments
the DB rows point to are not in the new (empty) volume.

**Diagnosis / fix (never `down -v`, never delete the orphan to "clean up"):**

1. `docker volume ls` + `docker volume inspect <vol>` to find the orphaned (old)
   and the new (empty) volume.
2. Copy forward with a throwaway container mounting both, preserving ownership
   (`cp -a` keeps UID/GID — Odoo's filestore and Postgres's data dir are owned
   by specific UIDs; a root-owned copy is unreadable by the service).
3. Only after the service is healthy on the new volume, archive then remove the
   orphan **by explicit name** — never a blanket prune.

See `skills/docker/references/volume-and-pg-safety.md` for the exact `docker run
... alpine cp -a` invocation and the orphan-drift detail.

### 2. Preserve the running Postgres major version

Postgres data directories are **forward-incompatible across major versions**. A
dir written by PG 15 cannot be opened by PG 14, and a fresh PG 16 image pointed
at a 15 data dir refuses to start. This bites hardest when **regenerating a
compose stack from a template**: templates pin a default tag
(`postgres:latest`, or whatever the template author chose) that may not match
the major that actually wrote the live volume. Regenerating blindly silently
downgrades or upgrades the pinned major and bricks the boot.

**Diagnosis / fix:**

1. Read the actual major recorded inside the DB volume:
   `cat /var/lib/postgresql/data/PG_VERSION` (via a throwaway container mounting
   the volume).
2. Pin the regenerated compose file to that **same** major — never silently
   change it, never downgrade against an existing data dir.
3. To intentionally upgrade a major, do a real migration (`pg_dumpall` from the
   old major → start the new major on a fresh volume → restore). Do not point
   the new image at the old data dir and hope.

Treat a **pinned, non-template** Postgres major as a deliberate deviation: when
you regenerate, preserve it. See the reference for the `PG_VERSION` read.

### 3. Upgrade via the odoo-bin CLI, not the RPC immediate-upgrade button

When an upgrade must reliably run migration scripts and reload module
translations, use the command-line form, not an RPC "immediate upgrade" call:

```bash
odoo -u <modules> -d <db> --stop-after-init
```

`--stop-after-init` runs the full pipeline (schema migrations, pre/post
migration scripts, translation reload) in a controlled init context and exits
with a clean code — deterministic and scriptable.

**Why not RPC:** on an instance where the **`website`** module is installed, the
RPC immediate-upgrade path (the one an interactive Apps action uses) can be
**hijacked into returning a website configurator action** instead of completing
the upgrade. The call appears to succeed but the **translation reload is
silently skipped**, leaving stale translations with no error. The CLI
`--stop-after-init` form has no interactive action to divert to, so it runs to
completion.

Diagnosis tell: an upgrade "ran" but translations are stale on a website-enabled
instance → suspect the RPC path was diverted; re-run via the CLI form.

### 4. Theme load: `theme_id` is intent, the post-copy hook is the load

On a fresh DB, writing `website.theme_id` does **not** copy the theme's pages,
views, assets, and records into the website. That materialization happens in a
post-copy step that runs when the theme is **loaded**, not when the field is
assigned. Set the field and stop → a website that claims a theme but renders
blank/generic pages.

**Correct order on a fresh DB:**

1. Ensure the `website` record exists and its core config is set.
2. Ensure the languages you intend to support are **installed and activated
   before** the theme load — the post-copy step mirrors translatable content per
   active language; languages added afterward do not retroactively receive theme
   translations.
3. Trigger the theme load so the post-copy hook runs (re-run the theme module's
   upgrade `-u <theme_module>`, or call the theme-load action for that website).
   Verify concrete pages/views exist afterward — not just that `theme_id` is set.

**And the silent-drop trap (theme-translated-fields mapping):** theme content
lives on `theme.*` mirror models copied into concrete models on load. The
mapping that drives which fields are mirrored must list **every translatable
field**. A translatable field present on the model but **missing from the
mapping** has its non-default-language translations **silently dropped** on load
(default language copies fine, so the bug is invisible until someone switches
language). Whenever you add a translatable field to a theme-backed model, add it
to the mapping in the same change, re-audit, reload, and verify a non-default
language.

See `skills/upgrade/references/theme-load-and-cli-upgrade.md` for full detail.

## Stack & DB lifecycle safety

A second failure family is the **lifecycle** of the running stack: a DB that won't
auto-start, a restart that self-kills, a readiness poll that DoSes the backend, a lying
exit code, and a clone that loses the filestore. These bite on bare-metal / local dev as
much as on Docker. Generic placeholders: `<port>`, `<config>`, `<data-dir>`, `<logfile>`.

### Standalone Postgres with no auto-start

A manually-managed Postgres instance (not a systemd cluster, not a container) does **not**
come back on reboot. Start it through **its own** `pg_ctl` against its data dir + log;
never repoint Odoo at a *different* cluster/port to "make it connect" (auth and data
differ there):

```bash
pg_ctl -D <data-dir> -l <data-dir>/server.log start
```

A `pg_ctl` 60s timeout / exit 1 **is not automatically a failure** — after an abrupt stop
the server does fsync + WAL crash-recovery before it accepts connections. Verify the real
state instead of rolling back:

```bash
pg_isready -p <port>      # or: grep "ready to accept connections" <data-dir>/server.log
```

### Shared QC instance — re-inventory before destroying

A dev/QC instance is often **shared** across parallel sessions, so its DB inventory can
change under a paused task. Before any `dropdb` / restore-over / `DROP DATABASE`, list the
current DBs and check for live connections; if another session holds the DB, **stand
down**. Commands in `references/db-safety.md`.

### Restart hygiene

- Resolve the target **PID** and kill by PID (or a bracketed pattern).
- **Never** combine stop + start in one chain:
  `pkill -f "<config>" && odoo-bin -c <config>` self-matches — the `pkill` pattern is
  present in the chain's own command line (including the `odoo-bin` part), so it SIGTERMs
  itself and **exits 144 before the start runs**. Stop in **one** call, start in a
  **separate** call.
- Confirm the HTTP `<port>` (and the gevent/longpolling port) are actually free before
  starting — a Windows-side listener can hold a WSL port (defer to claude-env-doctor).
- A config defines its **own** logfile; a launch redirected elsewhere looks "silent" —
  tail the config's logfile, not the redirect.

### Bounded readiness polling only

Never poll an Odoo endpoint with an **unbounded** retry — e.g.
`curl --retry-connrefused .../web/login` with no `--max-time`. An unthrottled retry storm
can saturate the backend and, through IDE port-forwarding, take it down. Use a bounded
loop, or grep the log:

```bash
for i in $(seq 1 30); do
  curl -fsS --max-time 5 "http://127.0.0.1:<port>/web/login" >/dev/null 2>&1 && break
  sleep 1
done
# or, race-free: grep -q "HTTP service .* running" <logfile>
```

The `pre_odoo_restart_guard.py` advisory hook nudges on the unbounded form.

### Verify install/upgrade from the LOG, not the exit code

A background job's completion notification reports the **wrapper** command's exit (often a
trailing `echo`), not the Odoo result — an `-i`/`-u` that aborted with a CRITICAL can be
reported as "exit 0". After any `odoo-bin -i/-u`, grep the real log:

```bash
grep -E "ERROR|CRITICAL|Traceback" <logfile>        # must be empty
grep -E "Modules loaded|Registry loaded" <logfile>  # positive signal
```

### Clone with the filestore; keep configs separate

Clone an Odoo DB with `odoo-bin db duplicate` (or a full dump/load) — **never**
`psql ... TEMPLATE`, which copies SQL only and breaks the filestore. Use a **separate
local config**; never mutate the Docker/container conf to debug locally. Full detail,
multi-instance isolation (own hostname / port pair / `db_filter` / filestore / log /
addons_path), and snapshot backup+checksum are in `references/db-safety.md`.

## Version-aware notes (Odoo 14-19)

| Concern | 14-16 | 17 | 18-19 |
|---|---|---|---|
| Default Postgres major (template) | 12 | 15 | 15 |
| Odoo entry point | `odoo-bin` | `odoo-bin` | `setup/odoo` (19) |
| Gevent/longpolling key (compose conf) | `longpolling_port` | `gevent_port` | `gevent_port` |
| Translation storage | `ir.translation` table | JSON terms | JSON terms |

The CLI-upgrade, theme-load, mapping-completeness, and volume/PG rules are
identical across 14-19. Only the **pinned Postgres major** (12 vs 15) and the
**entry-point path** differ — which is exactly why rule 2 says read `PG_VERSION`
from the live volume rather than trusting the template default.

## Doctor checklist

- [ ] Before any `down -v` / `volume rm` / `volume prune`: confirmed which volume
      holds live data (`docker volume ls` + `inspect`) and have a fresh DB dump +
      filestore archive outside that volume.
- [ ] Mount-point changed → copied data forward with `cp -a` (ownership
      preserved), did NOT delete the orphan, did NOT `down -v`.
- [ ] Read `PG_VERSION` from the DB volume and pinned the regenerated compose to
      that exact major; no silent downgrade/upgrade.
- [ ] Upgrade run via `odoo -u <modules> -d <db> --stop-after-init`, not the RPC
      immediate-upgrade button (especially on website-enabled instances).
- [ ] Fresh-DB theme: website + languages configured and active first, THEN
      theme load triggered; concrete pages/views verified (not just `theme_id`).
- [ ] Every translatable field on a theme-backed model is in the
      theme-translated-fields mapping; reloaded and a non-default language
      verified.
- [ ] Standalone Postgres started via its own `pg_ctl`; a `pg_ctl` timeout was
      confirmed (or refuted) with `pg_isready` / the server log before any rollback.
- [ ] Before dropping/restoring a DB on a shared instance: re-listed DBs and
      checked `pg_stat_activity` for live connections.
- [ ] Restart issued stop and start as SEPARATE calls (no `pkill … && … odoo-bin`),
      killed by PID, confirmed the port free, tailed the config's own logfile.
- [ ] Readiness polled with a BOUNDED loop (`--max-time` + fixed count/delay) or
      a log grep — never an unbounded `curl --retry-connrefused`.
- [ ] Install/upgrade result verified from the LOG (no ERROR/CRITICAL/Traceback),
      not from the wrapper/background exit code.
- [ ] DB cloned with `odoo-bin db duplicate` (filestore copied), never
      `psql … TEMPLATE`; baseline snapshot backed up + sha256'd before regenerating.

## Anti-patterns

| Anti-pattern | Why it is wrong | Correct |
|---|---|---|
| `docker compose down -v` to "reset the stack" | Deletes DB + filestore volumes irreversibly | Plain `down`; remove specific volumes by name only after a backup |
| Deleting the orphaned old volume to "clean up" after a mount change | That orphan still holds the only copy of the data | Copy forward with `cp -a`, verify health, then archive/remove by name |
| Regenerating compose with the template's default `postgres:` tag | Silently changes the major; data dir is forward-incompatible | Read `PG_VERSION`, pin the same major |
| Clicking the Apps "Upgrade" (RPC immediate-upgrade) on a website instance | Can divert to a configurator action; translation reload silently skipped | `odoo -u <modules> -d <db> --stop-after-init` |
| Setting `theme_id` and expecting pages to appear | Assignment is intent; the post-copy load step never ran | Configure website + languages, then trigger the theme load |
| Adding a translatable field without updating the mapping | Non-default-language translations silently dropped on load | Add the field to the theme-translated-fields mapping in the same change |
| Repointing Odoo at a different Postgres cluster/port to "make it connect" | Different instance = different auth/data; masks the real (down) instance | Start the intended instance via its own `pg_ctl`; verify with `pg_isready` |
| Treating a `pg_ctl` timeout / exit 1 as a failed start | The server may be mid WAL crash-recovery and come up fine | Check `pg_isready` / the server log before rolling back |
| `pkill -f "<config>" && odoo-bin -c <config>` in one chain | The pkill self-matches the chain and exits 144 before the start | Stop and start in separate calls; kill by PID |
| `curl --retry-connrefused …:<port>/web` with no `--max-time` | Unbounded retry storm can take the backend down | Bounded loop (`--max-time` + fixed count/delay) or a log grep |
| Concluding install success from a background/notification exit code | The wrapper exit (e.g. a trailing `echo`) hides a CRITICAL | Grep the real log for ERROR/CRITICAL/Traceback |
| `psql … TEMPLATE` / `createdb -T` to clone an Odoo DB | Copies SQL only; the filestore/attachments break | `odoo-bin db duplicate` (or full dump/load) |
| Editing the Docker/container conf to run locally | Breaks the container setup and the local run (wrong host/paths) | A separate local config; leave the Docker conf untouched |

## Cross-references

- `skills/docker/references/volume-and-pg-safety.md` — copy-forward command,
  `PG_VERSION` read, orphan-drift detail, Git-Bash path note.
- `skills/upgrade/references/theme-load-and-cli-upgrade.md` — theme-load order,
  CLI-vs-RPC upgrade, theme-translated-fields mapping completeness.
- `skills/docker/SKILL.md` — compose generation, deployment, container debugging.
- `skills/stack-doctor/references/db-safety.md` — snapshot backup+checksum, real
  uninstall-not-SQL-hack, filestore-aware clone vs `psql TEMPLATE`, multi-instance
  isolation, local-vs-Docker config.
- `hooks/pre_odoo_volume_guard.py` — Bash-layer hard block on blind volume
  destruction (override token required to proceed).
- `hooks/pre_odoo_restart_guard.py` — Bash-layer ADVISORY (never blocks): nudges on
  an unbounded readiness poll, a `pkill … && … odoo-bin` chain, and a `psql TEMPLATE`
  clone.
- `claude-env-doctor-plugin` — generic Windows/WSL/Git-Bash environment issues
  (e.g. a Windows-side listener holding a WSL port).
