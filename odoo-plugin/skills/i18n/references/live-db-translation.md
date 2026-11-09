# Translating a running database (no module deploy)

Use this when translations must land in a live database (local, staging, Odoo.sh or production)
without shipping or upgrading a module: dashboard names, menu-like records, selection labels,
records created in the UI or over RPC. The durable path is still a module that ships
`i18n/<lang>.po` (see Workflow 4 in `../SKILL.md`). This file covers what a live database can and
cannot take.

Verified against Odoo 19 source (`odoo/tools/translate.py`, `base/wizard/base_export_language.py`,
`base/wizard/base_import_language.py`). Used end to end on Odoo 17 (staging and production).

## 1. Decide first: record term or code term?

| Text | Kind | Can a live import translate it? |
|---|---|---|
| A field declared `translate=True` (record `name`, `ir.model.fields.selection.name`, `spreadsheet.dashboard.name`, `ir.ui.menu.name`, `translate=html_translate` fields…) | **record (model) term**, stored as jsonb in the row | **yes** |
| `_()` / `_lt()` in Python, `_t()` in JS and Owl, `=_t("…")` inside a spreadsheet workbook, figure titles rendered with `_t(chart.title)` | **code term**, read from `i18n/*.po` files on the server's disk | **no** |

`TranslationImporter._load` skips every row whose type is `code`. The source comment is
literally `# ignore code translations`. An imported `.po` therefore never translates
`_t`/`_()` texts on a live database, whatever it contains. A data-only `base_import_module` zip
reads its `.po` once, at import time, so it does not help either.

Rule: **if the text you need to translate on a live DB is a code term, move it into a record**
(see the spreadsheet pattern in `../../spreadsheet-dashboards/SKILL.md`, "Translating a dashboard
without code"), or ship it in a module. Do not tell the user that a `.po` "needs a module on
disk" without saying which kind of term it is. That is true for code terms only.

## 2. The round trip: Export Translation (Model) → fill → Import Translation

These are the standard wizards behind *Settings → Translations → Export / Import Translation*. A
user can do the same steps by hand. Over RPC, drive them with a guarded script, not ad-hoc MCP
writes (see `../../mcp/SKILL.md`, scripts section). Payloads are base64 files, and the
target is often a remote stage or prod instance.

```python
# call(model, method, args, **kw) = your XML-RPC / JSON-2 execute_kw helper
from base64 import b64decode, b64encode

def export_po(model, domain_str, lang):
    mid = call('ir.model', 'search', [[('model', '=', model)]])[0]
    wiz = call('base.language.export', 'create', [{
        'lang': lang, 'format': 'po',
        'export_type': 'model', 'model_id': mid, 'domain': domain_str,   # domain is a STRING
    }])
    call('base.language.export', 'act_getfile', [[wiz]])
    data = call('base.language.export', 'read', [[wiz]], fields=['data'])[0]['data']
    return b64decode(data).decode('utf-8')

def import_po(po_text, lang, lang_name):
    wiz = call('base.language.import', 'create', [{
        'name': lang_name, 'code': lang, 'filename': 'live.%s.po' % lang,
        'overwrite': True, 'data': b64encode(po_text.encode('utf-8')).decode(),
    }])
    call('base.language.import', 'import_lang', [[wiz]])
```

Steps:
1. The target language must be **active** on the database (`res.lang` `active=True`). Load it
   first if it is not.
2. Export one `.po` per model with a domain that selects exactly the records you own. For a
   dashboard set, for example:
   - `ir.model.fields.selection` with `[('field_id.model', '=like', 'x_my_labels%')]`
   - `spreadsheet.dashboard` with `[('dashboard_group_id.name', '=', 'My Boards')]`
   - `spreadsheet.dashboard.group` with `[('name', '=', 'My Boards')]`
   Records without an external ID get an automatic `__export__.*` ID during export, so the file
   imports back onto the same rows.
3. Fill `msgstr`: by hand, from a translator, or by mapping `msgid → msgstr` from an existing
   module `<lang>.po`. Edit with `polib` or the binary-safe rules in `../SKILL.md`. Never touch
   the `#:` reference lines: they carry the record IDs.
4. Import with `overwrite=True`. The change is live at once: no restart, no module update, no
   asset rebuild.
5. Read back (section 4).

**Overwrite vs `noupdate`.** `TranslationImporter.save` replaces an existing translation only if
`force_overwrite or (not noupdate and overwrite)`. Rows exported with fresh `__export__` IDs are
fine. A record a module loaded as `noupdate="1"` can keep its old translation even with
*Overwrite* on. Use `update_field_translations` on that record instead (section 3).

## 3. One field, one record: `update_field_translations`

For a handful of values, skip the wizard:

```python
call('spreadsheet.dashboard', 'update_field_translations',
     [[rec_id], 'name', {'ar_001': 'لوحة المبيعات', 'fr_FR': 'Tableau des ventes'}])
```

- Writing with `context={'lang': 'ar_001'}` on a plain `translate=True` field sets only that
  language's value. Writing with **no** lang, or with `en_US`, changes the source text.
- On an `html_translate` / `xml_translate` field, a write with `lang` in context also rewrites
  the source. Write the source first (no lang), then `update_field_translations` per language.
  Terms are matched by source term, not by the whole value. See `runtime-traps.md`.
- Through the Odoo MCP this is `odoo_call` with method `update_field_translations`. It needs an
  instance with `write` access, and on prod the session unlock.

## 4. Verify in both languages

1. **Over RPC.** Read each record with `context={'lang': 'en_US'}` and with the target language.
   Compare against the expected map and report the mismatch counts, for example
   `keys 71 | en mismatches 0 | ar mismatches 0`:
   ```python
   def labels(lang):
       rows = call('ir.model.fields.selection', 'search_read',
                   [[('field_id.model', '=', 'x_my_labels')]], fields=['value', 'name'],
                   context={'lang': lang})
       return {r['value']: r['name'] for r in rows}
   ```
2. **In the browser** (local or staging): set `res.users.lang` for the test user, then do a
   **full** reload with a cache-buster query (`/web?r=<n>#action=…`). A hash-only URL change
   keeps the old session language. The first load in an RTL language builds the RTL asset bundle,
   so wait for it before judging the layout.
3. Rehearse with a two-record probe on a local copy, then the full set locally, then staging, then
   production.

## 5. Durability: a live import is not a delivery

- The values live in the jsonb columns of those rows. A module **update** leaves them alone.
- **Rebuilding or recreating the records loses them:** a staging rebuild, re-creating a dashboard,
  or re-deploying a SQL view whose model and selection rows are regenerated. All of these start
  in the source language again.
- Keep the filled `.po` files (`*.exported.po`, `*.<lang>.po`) in the repo next to the deploy
  tooling, and re-run export → fill → import after every such re-deploy.
- The permanent fix is a module that ships `i18n/<lang>.po`. That is also the only way to deliver
  code terms. Before installing that module, remove the temporary live records, or the UI shows
  both sets.
