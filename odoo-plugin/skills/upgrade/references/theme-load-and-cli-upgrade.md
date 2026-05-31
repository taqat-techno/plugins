# Theme load and reliable module upgrade

Odoo-specific reference for two failure modes that look like "the upgrade ran but nothing changed": theme content not appearing on a fresh website, and translation reloads being silently skipped during an upgrade. Read this before debugging a website theme that "didn't apply" or an upgrade that "didn't pick up new translations".

## Theme load does not happen just because theme_id is set

On a fresh database, writing a value to `website.theme_id` (the field that records which theme module a website uses) does **not** by itself copy the theme's pages, views, assets, and records into that website. The theme's content lives in the theme module's data and is materialized into concrete website records by a post-copy step that runs when the theme is *loaded*, not when the field is merely assigned.

If you set the field and stop, you get a website that claims to use a theme but renders empty or default pages. The symptom is "theme is selected in settings but the homepage is blank / generic".

### Correct order on a fresh DB

Configure the website context first, then trigger the load:

1. Ensure the `website` record exists and its core configuration is set (company, default language, domain/name as needed).
2. Ensure the languages you intend to support are **installed and activated** on the database before the theme load runs. The post-copy step mirrors translatable content per active language; languages added afterward will not retroactively receive theme translations.
3. Trigger the theme load so the post-copy hook runs. The hook is what copies theme views and pages into concrete website records.

### Triggering or re-triggering the load

If theme pages are missing after the field was set, force the materialization rather than re-setting the field:

- Re-run the theme module's upgrade (`-u <theme_module>`), which re-invokes the post-copy/load path.
- Or call the theme-load action exposed by the website/theme layer for that website, which performs the copy explicitly.

After the load, verify that concrete website pages/views exist for the theme, not just that the `theme_id` field is populated.

> Lesson: assigning `theme_id` records an intent; the post-copy hook fulfills it. Configure website and languages first, then load.

## Prefer the odoo-bin CLI form for upgrades that must run migrations and reload translations

When an upgrade must reliably run migration scripts and reload module translations, use the command-line upgrade form rather than an RPC immediate-upgrade call.

### Use the CLI form

```bash
odoo -u <modules> -d <db> --stop-after-init
```

- `-u <modules>` upgrades the named modules (comma-separated; `all` upgrades everything installed).
- `-d <db>` selects the target database.
- `--stop-after-init` runs the upgrade and exits, so the process is deterministic and scriptable (no lingering server, clean exit code).

This path runs the full upgrade pipeline in a controlled init context: schema migrations, pre/post migration scripts, and translation reload all execute before the process exits.

### Why not the RPC immediate-upgrade call

Triggering an upgrade over RPC (the "immediate upgrade" path that an interactive Apps action uses) is less reliable for migrations and translation reloads. On an instance where the `website` module is installed, that RPC path can be **hijacked into returning a website configurator action** instead of completing the upgrade flow as expected. When that happens the call appears to succeed but the translation reload is silently skipped, leaving you on stale translations with no error.

The CLI `--stop-after-init` form is not subject to that redirect: there is no interactive action to return to, so the upgrade and translation reload run to completion.

> Lesson: if an upgrade "ran" but translations are stale on a website-enabled instance, suspect the RPC path was diverted to a configurator action. Re-run via the CLI form.

### Example (illustrative — not required)

```bash
# Upgrade two modules and reload their translations, then exit
odoo -u sale,account -d mydb --stop-after-init

# Re-run a theme module's upgrade to re-trigger its post-copy hook
odoo -u theme_default -d mydb --stop-after-init
```

Module and database names above are placeholders; substitute your own.

## Theme to concrete model mirrors: declare every translatable field

Theme content is stored on `theme.*` mirror models and copied into the corresponding concrete models on load. The mapping that drives which fields get mirrored — the **theme-translated-fields mapping** — must list **every translatable field** that should carry translations across the copy.

If a translatable field is present on the model but **missing from the theme-translated-fields mapping**, its translations for **non-active / non-default languages are silently dropped** during the load. The default-language value copies fine, so the bug is invisible until someone switches language and finds the field untranslated. There is no error and no log line.

### Re-audit the mapping whenever you add a translatable field

This is the maintenance rule that prevents the silent drop:

1. When you add a new translatable field to a theme-backed model (or its `theme.*` mirror), add the same field to the theme-translated-fields mapping in the same change.
2. After any change that adds or renames translatable fields, re-audit the full mapping against the model's translatable fields — diff "fields declared `translate=True`" against "fields present in the mapping" and reconcile.
3. Re-run the theme load (or theme module upgrade) and verify a non-default language to confirm the field's translation survived the copy.

### Example (illustrative — not required)

If a model gains a translatable `subtitle` field and only the existing `name` field is listed in the mapping, then on load the website gets `name` translated in all active languages but `subtitle` translated only in the default language; every other language shows the default-language `subtitle`. Adding `subtitle` to the mapping and reloading fixes it.

> Lesson: an incomplete theme-translated-fields mapping fails open on the default language and fails silent on every other language. Treat "added a translatable field" as a trigger to re-audit the mapping.

## Quick checklist

- Fresh website blank despite theme selected → website + languages configured first, then theme load triggered (not just `theme_id` set).
- Upgrade ran but translations stale on a website instance → re-run via `odoo -u <modules> -d <db> --stop-after-init`; suspect RPC path diverted to a configurator action.
- New translatable field on a theme model → add it to the theme-translated-fields mapping, re-audit, reload, verify a non-default language.
