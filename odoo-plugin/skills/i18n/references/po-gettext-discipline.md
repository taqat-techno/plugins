# PO / gettext Translation Discipline (Odoo)

This reference covers the gettext discipline an Odoo module must follow for translations to actually apply at runtime. It is Odoo-specific: it assumes the standard `i18n/` directory, the Odoo i18n export, and the way Odoo loads `.po`/`.pot` files against models, selections, and QWeb views.

Brand, client, and project names are kept out of the guidance. Where a concrete value clarifies a point, it is fenced and labelled "Example (illustrative -- not required):" and carries no behavioral weight.

## Why msgid alone is not enough in Odoo

In a plain gettext program, a `msgid` is just the English source string and the runtime matches on that string. Odoo is stricter: it loads translations against specific **translation targets** -- a model's field label, a selection value, a view node's text -- and it uses the **reference comments** above each entry to decide which target an entry binds to. A `msgstr` with the right text but the wrong (or missing) typed reference applies to nothing.

So two things must both be true for a translation to take effect:

1. The `msgid` exactly matches the current English source string.
2. The reference comment(s) above the entry name a real, typed translation target that still exists.

The four sections below are the discipline that keeps both true.

## 1. Typed PO references, not source-file paths

A `.po` entry carries reference comment lines beginning with `#:`. For ordinary Python source strings these are file:line locations and Odoo is tolerant of them drifting. But for **model field labels, selection values, help text, and QWeb view text**, Odoo expects a **typed reference** that names the translation target, not a source-file path. A plain path-style reference does not bind the entry to the label or view node, so the translation silently falls back to the source language even though the `.po` looks complete.

The typed reference forms Odoo emits (and matches against) include:

- `model:ir.model.fields,field_description:<model>,<field>` -- a field's display label.
- `model:ir.model.fields,help:<model>,<field>` -- a field's help/tooltip.
- `model:ir.model.fields.selection,name:<model>,<field>,<value>` -- one selection option label.
- `model_terms:ir.ui.view,arch_db:<module>.<view_id>` -- a translatable term inside a view's arch.

The reliable way to get correct typed references is to **never hand-write them**. Generate the canonical `.pot` from the live module via the Odoo i18n export, which walks the registry and emits the correct typed reference for every target, then merge your existing translations into that `.pot`.

Export the template (writes the module's canonical `.pot` to its `i18n/` directory):

```bash
# from the Odoo root, with the module installed in the target database
odoo-bin -d <db> --i18n-export=<module>/i18n/<module>.pot --modules=<module> --stop-after-init
```

Then merge existing language files into the freshly-exported template (see Section 3), so the typed references come from the export and the translated text comes from your `.po`.

> Example (illustrative -- not required): an entry for a status field's label and one of its options would carry references like
> ```
> #. module: sales_extra
> #: model:ir.model.fields,field_description:sales_extra.model_order_line,order_line.note
> msgid "Note"
> msgstr "..."
>
> #: model:ir.model.fields.selection,name:sales_extra.model_order_line,order_line.state,draft
> msgid "Draft"
> msgstr "..."
> ```
> A path like `#: addons/sales_extra/models/order_line.py:42` in place of those typed references would leave the label untranslated.

## 2. Source-string edits invalidate the msgid

A gettext `msgid` is keyed on the exact English source string. The moment you edit a translatable English source -- a field `string=`/`help=` value, a selection label, literal text inside a QWeb view, or a `_()` argument -- the old `msgid` no longer matches anything in the registry. The entry is **orphaned**: its `msgstr` still exists in the `.po`, but at runtime the new source string has no matching translation and falls back to the source language.

Common ways this happens, all of which look harmless in a diff:

- Changing a field label from one wording to another.
- Fixing a typo or trailing space in any translatable literal.
- Re-casing, re-punctuating, or pluralizing a selection value or view label.
- Splitting or joining one source string into two.

Discipline after **any** user-facing source edit:

1. Re-export the `.pot` so the new `msgid` appears (Section 1).
2. `msgmerge` each language `.po` against the new template (Section 3). A reworded source becomes a **fuzzy** entry carrying the old translation as a hint; a removed source becomes **obsolete** (`#~`).
3. Audit the affected `.po` for those fuzzy/obsolete entries and refresh them. A `fuzzy` flag is **not** applied by Odoo at load time, so a fuzzy entry counts as untranslated until you confirm it and drop the flag.

Quick audit of what changed after a merge:

```bash
# count fuzzy and untranslated entries that now need attention
msgattrib --fuzzy <module>/i18n/<lang>.po | grep -c '^msgid'
msgattrib --untranslated <module>/i18n/<lang>.po | grep -c '^msgid'
```

Never "fix" a fallback by editing the live `.po`'s `msgstr` while leaving a stale `msgid` -- that re-orphans on the next export. Fix the `msgid` via re-export + merge, then fill the `msgstr`.

## 3. Canonical bilingual workflow

The supported way to maintain a second language for a module is one source tree, one `.pot`, and one `.po` per language -- never a duplicated view tree. Forking a parallel `_<lang>` copy of a view (or model) to hold translated text defeats gettext entirely: the two trees drift, IDs collide or diverge, and the translation never flows through the normal loader.

The loop:

1. **Export the template.** Regenerate the module `.pot` from the installed module (Section 1). This is the single source of truth for `msgid`s and typed references.

2. **Merge with `--previous` to salvage exact matches.** Update each language file against the new template, preserving prior translations and old-source hints:

   ```bash
   msgmerge --previous --update <module>/i18n/<lang>.po <module>/i18n/<module>.pot
   ```

   Behavior to expect:
   - Source strings that are unchanged keep their existing `msgstr` verbatim.
   - Reworded source strings become **fuzzy**, with the previous translation attached as a starting point (and the old source recorded via `#| msgid`).
   - Source strings that no longer exist become **obsolete** (`#~`), retained for reference but not loaded.
   - Genuinely new targets appear as empty, untranslated entries.

3. **Fill new and fuzzy entries.** Translate the empty entries, confirm or correct each fuzzy entry, and remove the `fuzzy` flag once verified. Leave obsolete entries alone unless you are pruning the file deliberately.

4. **Re-import / reload.** Update the module (or use the Odoo i18n load path) so the refreshed `.po` is applied against the registry targets.

```bash
# load a language file back into a database
odoo-bin -d <db> --i18n-import=<module>/i18n/<lang>.po --language=<lang> --stop-after-init
```

Hard rule: **never fork duplicate `_<lang>` view trees** (or shadow models) to carry translations. All language variants of a view come from the same `arch` translated through `model_terms:ir.ui.view,arch_db:...` entries in the `.po`. One arch, one set of typed term references, many languages.

## 4. Encoding: PO files are UTF-8, decode them as UTF-8

`.po` and `.pot` files are UTF-8 (the header declares `Content-Type: text/plain; charset=UTF-8`). Any tooling you write to read, rewrite, or diff these files must decode the bytes **explicitly as UTF-8**.

The trap: routing PO bytes through a `unicode_escape`-style codec (or any "escape/unescape" pass that treats backslashes as Python/C string escapes). That codec is not UTF-8 -- it interprets each byte in a Latin-1-ish way and mangles multi-byte UTF-8 sequences, silently corrupting every non-ASCII character. Accented Latin, Cyrillic, Arabic, CJK, and emoji all break. The file may still parse, so the corruption ships unnoticed until someone reads the rendered label.

Two distinct concerns that must be handled **separately**:

- **File encoding.** Always `open(path, encoding="utf-8")` (or read bytes and `.decode("utf-8")`). Never `unicode_escape`, never `latin-1`, never a "guess the charset" pass.
- **PO-quote escapes.** Inside a `msgid`/`msgstr`, gettext uses its own quoting: `\"`, `\\`, `\n`, `\t`. These are *PO syntax*, not Unicode escapes, and must be unescaped with PO-aware logic (or a real PO library), not by a Unicode/string-escape codec.

```python
# correct: UTF-8 for the file, PO-aware library for the entries
import polib
po = polib.pofile("i18n/<lang>.po", encoding="utf-8")   # bytes decoded as UTF-8
for entry in po:
    text = entry.msgstr        # already correct Unicode; PO escapes handled by polib

# WRONG -- corrupts every non-ASCII character:
#   raw.decode("unicode_escape")
#   open(path).read().encode("latin-1").decode("unicode_escape")
```

If you only need to read or count entries, prefer a real PO library (it gets both the file encoding and the PO-quote escapes right). If you must touch bytes directly, decode UTF-8 first, then handle gettext quoting as a separate, explicit step -- and re-encode as UTF-8 on write.

## Checklist

- Typed references (`field_description`, `help`, selection `name`, view `arch_db`) come from the Odoo i18n export, never hand-written paths.
- After any user-facing source-string edit, re-export the `.pot` and re-merge -- treat orphaned/fuzzy `msgid`s as untranslated.
- One source tree per module: export `.pot`, `msgmerge --previous`, fill new/fuzzy, reload. No duplicate `_<lang>` view trees.
- Read/write `.po`/`.pot` as explicit UTF-8; handle gettext quote escapes separately; never use a `unicode_escape`-style codec on PO bytes.
