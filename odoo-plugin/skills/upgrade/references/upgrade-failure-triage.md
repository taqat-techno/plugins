# Upgrade failure triage: what failed, who owns it, and what counts as clean

Read this when an upgrade (`-u`, a version migration, a platform build) fails or logs warnings and
you must decide whether the cause is data or code, which warnings block acceptance, and what is
safe to fix. The migration mechanics themselves live in `../SKILL.md`.

## 1. Data or code? Prove corruption independently

- A record id in a traceback is where the defect surfaced, not proof the record is bad. Prove
  corruption on its own: FK orphans, NULLs in required columns, values outside a selection,
  duplicates against a unique rule, unvalidated constraints.
- If the records are structurally valid, classify the failure as **code / upgrade path** (scale,
  ORM batching, compute order). Tell-tale: the failing id changes between runs (a prefetch or batch
  boundary moved), or the row count is merely large.
- Never "repair" valid production records through RPC or a shell to get an upgrade past a failure.
  Live-instance tools are for investigation and verification; the fix is versioned code.
- A fix is proven only against all four of: the exact release baseline (refs and submodule pins), a
  fresh disposable clone of a production-scale database (pass the pristine restore as a template,
  never as `-d`), the core/runtime that matches the target environment, and the real mutually
  dependent deploy set upgraded together. Module-by-module `-u` breaks `pre`/`post`/`end` ordering
  and produces false failures. Record the command, DB source, repo and core HEADs and module
  versions with each run.

## 2. A "clean upgrade log", defined

Clean means: no unhandled traceback, no ERROR or CRITICAL, no unresolved actionable warning from
your own code or configuration, and every remaining warning understood. It does not mean zero
WARNING lines.

Classify every WARNING and ERROR by owner before acting:

| Bucket | Owner | Action |
|---|---|---|
| A | Your custom source code | Fix, with proof |
| B | Your custom configuration or manifest | Fix, with proof |
| C | Odoo core / Enterprise | Document |
| D | Third-party, vendor or OCA | Document (or fix upstream / in the vendored copy deliberately) |
| E | Environment or version mismatch | Document, fix the environment |
| F | Expected benign noise | Document |

- Run a baseline pass with no `-u` first: anything already in it is C, E or F by definition. Only
  signatures new in the upgrade run and classified A or B block acceptance.
- Count by the log level field (`^<date> <time> <pid> (ERROR|CRITICAL) `), not by substring:
  `grep -i error` also counts `KeyError` inside traceback bodies.
- Never silence a warning without fixing its cause, never invent manifest metadata, and never
  assign a `license` because another license is common in the repository: find the module's owner
  and license evidence, fix only what is proven, otherwise classify and leave it.
- Decide bucket B versus D by ownership, as the reviewer skill's ownership check describes
  (`../../reviewer/SKILL.md`, "How to use this skill").

## 3. Failures that look like your diff but are not

- **A renamed module bricks every database that still has the old name.** `button_upgrade` dies on
  the missing manifest, often before anything is logged. Before investigating your change, query
  `SELECT name, state FROM ir_module_module WHERE name IN (<retired names>)` and retry on a database
  known to have the new name. After any rename, rebuild shared test templates from a post-rename
  database; the old DBs need a module-rename migration (`openupgradelib.update_module_names`).
- **Removing a model leaves its table.** Odoo unregisters the model but only logs
  `DROP TABLE IF EXISTS "<table>"; -- N row(s)` as a note for a DBA. Check for the orphan table
  before reporting data loss, and decide explicitly whether to archive or drop it.
- **A field "removed in vN" can survive through an installed addon** (e.g. `stock.move.line.qty_done`
  in 17 lives on as a compute in Enterprise `stock_barcode`). Field-removal impact is per database:
  check whether the re-introducing addon is installed before predicting a crash, because the quieter
  outcome is wrong values, not a `KeyError`.
- **Removing a `required` field strands its NOT NULL column.** Every database and test template
  created before the change hits `NotNullViolation` on insert until it is upgraded (`-u`) or the
  constraint is dropped by a migration.

## 4. Views and QWeb after a cross-version upgrade

- **Per-website view copies outlive upgrades.** A copy made by the website editor or a migration
  script (`website_id` set, no xmlid) replaces the module template on that website, and `-u` never
  touches it. If it calls a template renamed across versions, its pages 500 and "Restore previous
  version" cannot help. Find it by arch content plus `website_id` plus missing xmlid (confirm by
  reading the arch: `ilike` also matches the correct dotted name), then archive it so the website
  falls back to the module template.
- **`t-value` is a Python expression; `t-valuef` is a literal (format string).** A bare URL in
  `t-value` fails to compile the whole page. Use `t-valuef` for literals, and fix every language
  version of the arch, since website arches are stored per language.
- After migrating views across versions, scan every copied view for `t-call` targets that no longer
  exist and for `t-value` expressions that do not compile.
