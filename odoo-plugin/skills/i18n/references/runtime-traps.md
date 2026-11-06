# Runtime translation traps (Odoo 16-19)

Ways a string renders in the source language although the catalogue looks right. Each entry:
rule, why, how to check or fix. Catalogue-shape rules (typed references, `#. module:`,
UTF-8, newline convention) live in `skills/i18n-audit/SKILL.md`; this file covers how terms
are extracted, cached, written and rendered.

## Owl templates

**Component props translate only with the `.translate` suffix.** Odoo's QWeb extractor treats
a tag that starts with an uppercase letter as a component and extracts only attributes whose
name ends in `.translate`; Owl strips the suffix and translates the value at render time.
So `<FormField label="'Name'"/>` is invisible to both the extractor and the renderer, and
adding an entry by hand changes nothing.
- Fix: `<FormField label.translate="Name"/>` (raw text, no inner quotes).
- Inverse mistake: `.translate` on a plain element (`<input placeholder.translate=...>`) is
  neither extracted nor stripped and reaches the DOM as a literal attribute. Plain elements
  translate their standard attributes (`title`, `placeholder`, `alt`, `aria-label`, `label`).
- Check: run the extractor over the file and grep for the string; do not judge by eye.

**Multi-line text nodes keep their whitespace.** A QWeb text node is stripped at both ends but
not normalised, so a `<p>` spanning lines yields a msgid with embedded newlines and the
source file's indentation. A hand-typed msgid never matches it. Take msgids from the export.

**Strings that are never a term.** A bare JS literal (`notify("Saved.")`), a string literal
inside a `t-esc` expression (`'Active' : 'Archived'`) and an enum value printed raw
(`t-esc="rec.state"`) have no msgid at all, so no catalogue entry can fix them. Use `_t()` in
JS (module-level `_t()` is lazy and safe), text nodes with `t-if`/`t-else`, or a label map /
server-resolved label for enum values.

**Markers decide which runtime serves the entry.** JS `_t()` and Owl templates under
`static/src` are served from `#. odoo-javascript` entries via `/web/webclient/translations`;
server `_()` reads `#. odoo-python`. An entry under the wrong marker is present, translated
and invisible.

## Caches

- **Code terms** (`odoo-python` / `odoo-javascript`) are read from the `.po` on disk through a
  per-process cache keyed `(module, lang)`. A registry reload does not drop it: **restart**.
- **Model terms** (field labels, selections, view `arch_db`) live in the database: they need
  `-u <module>` or an i18n import, not a restart.
- `/web/webclient/translations` is HTTP-cached; re-test in a fresh browser context.

## `html_translate` fields over RPC

A write with `context={'lang': 'ar_001'}` to an `html_translate` field (term-based, such as a
product description) **overwrites the source value too**. Plain `translate=True` char/text
fields behave normally.
- Fix: write the source language first, then
  `get_field_translations(ids, field)` to read the source terms, then
  `update_field_translations(ids, field, {'ar_001': {source_term: translated}})`.
- Check: read the record back in both languages.

## Theme translations

The source language stays in the arch; the translation ships as `i18n/<lang>.po` (see
`po-gettext-discipline.md` for the ordering rule against post-copy).

1. **References.** Theme view terms are `model_terms:theme.ir.ui.view,arch:<module>.<view>`
   (the theme mirror model and its `arch` field), not `ir.ui.view,arch_db`. Regenerate them
   with the export; never hand-write them.
2. **`--load-language` is not enough.** It activates the language but does not populate the
   theme-view terms the export reads, so an export right after it comes back almost empty.
   Export to a fresh file, then copy each msgstr from the old catalogue by msgid, translate the
   remainder, and check placeholder parity.
3. **Load and propagate.** `-u <theme> --i18n-overwrite --stop-after-init` (language active)
   imports the catalogue and copies translations from `theme.ir.ui.view` into the live
   website views. Also add the language to the website (Website settings, Languages).
4. **Render in normal mode.** `--dev=xml` reads each view's arch from the source file and
   bypasses the per-language `arch_db`, so `/<lang>/...` shows the source language. Restart
   without `--dev` to verify translated pages.
5. **Scope.** The theme catalogue covers theme view text only; `website.menu` labels and
   other records are translated separately.

## Verification

A catalogue-coverage percentage cannot fail for a missing term (see i18n-audit rule 7).
Verify at three layers: the source (extracted terms vs entries), the runtime (ask the ORM in
the target language for the labels the screen draws) and the rendered screen in a browser
session whose user and website language are really set to that language, not a `?lang=`
query string.
