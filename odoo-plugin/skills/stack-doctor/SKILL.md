---
name: odoo-stack-doctor
description: |
  Diagnostic checklist for an Odoo Docker stack that "comes up clean but is wrong" — data silently orphaned, Postgres refusing to boot, an upgrade that ran but changed nothing, or a website theme that renders blank. Covers: a compose mount-point change orphans the old named volume (migrate data forward with cp -a, never `down -v`); never regenerate a pinned non-template Postgres major without preserving the deviation (forward-incompatible data dir); upgrade modules via the odoo-bin CLI --stop-after-init, NOT the RPC immediate-upgrade button (the website module can hijack it into a configurator action and silently skip the translation reload); on a fresh DB the theme content only materializes when the theme-load post-copy step runs (assigning theme_id is intent, not load) — trigger or re-trigger it after languages are active; and a theme-to-concrete mirror must list every translatable field in its translated-fields mapping or non-default-language translations are silently dropped. Odoo-version-aware (14-19). Activates on data-loss-risk volume operations, Postgres version-mismatch boot failures, "upgrade ran but nothing changed", or "theme selected but page is blank".
version: 0.1.0
last_reviewed: 2026-06-13
license: "MIT"
metadata:
  mode: codebase
  odoo-versions: ["14", "15", "16", "17", "18", "19"]
  categories: [docker, postgres, volumes, upgrade, theme, troubleshooting, data-safety]
  bashPattern: ["docker compose", "docker volume", "odoo-bin", "stop-after-init"]
  model: sonnet
owns:
  - the mount-point-change -> orphan-volume diagnosis (migrate forward, never down -v)
  - the preserve-the-running-Postgres-major rule (forward-incompatible data dir)
  - the CLI-upgrade-over-RPC rule (RPC hijacked by website configurator silently skips reload)
  - the theme-load-after-languages rule (theme_id is intent; post-copy hook materializes content)
  - the theme-translated-fields-mapping completeness rule (silent drop on non-default languages)
defers_to:
  - skills/docker/references/volume-and-pg-safety.md (volume/PG detail, copy-forward + PG_VERSION commands)
  - skills/upgrade/references/theme-load-and-cli-upgrade.md (theme-load + CLI-upgrade + mapping detail)
  - skills/docker/SKILL.md (compose generation, deployment, container debugging)
  - hooks/pre_odoo_volume_guard.py (hard-blocks blind volume destruction at the Bash layer)
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

## Anti-patterns

| Anti-pattern | Why it is wrong | Correct |
|---|---|---|
| `docker compose down -v` to "reset the stack" | Deletes DB + filestore volumes irreversibly | Plain `down`; remove specific volumes by name only after a backup |
| Deleting the orphaned old volume to "clean up" after a mount change | That orphan still holds the only copy of the data | Copy forward with `cp -a`, verify health, then archive/remove by name |
| Regenerating compose with the template's default `postgres:` tag | Silently changes the major; data dir is forward-incompatible | Read `PG_VERSION`, pin the same major |
| Clicking the Apps "Upgrade" (RPC immediate-upgrade) on a website instance | Can divert to a configurator action; translation reload silently skipped | `odoo -u <modules> -d <db> --stop-after-init` |
| Setting `theme_id` and expecting pages to appear | Assignment is intent; the post-copy load step never ran | Configure website + languages, then trigger the theme load |
| Adding a translatable field without updating the mapping | Non-default-language translations silently dropped on load | Add the field to the theme-translated-fields mapping in the same change |

## Cross-references

- `skills/docker/references/volume-and-pg-safety.md` — copy-forward command,
  `PG_VERSION` read, orphan-drift detail, Git-Bash path note.
- `skills/upgrade/references/theme-load-and-cli-upgrade.md` — theme-load order,
  CLI-vs-RPC upgrade, theme-translated-fields mapping completeness.
- `skills/docker/SKILL.md` — compose generation, deployment, container debugging.
- `hooks/pre_odoo_volume_guard.py` — Bash-layer hard block on blind volume
  destruction (override token required to proceed).
- `claude-env-doctor-plugin` — generic Windows/WSL/Git-Bash environment issues.
