---
name: odoo-i18n-audit
description: |
  Audit checklist for Odoo translations that look complete in the .po file but silently fall back to the source language at runtime. Covers the four gettext-discipline failures: PO entries for field/view labels need TYPED model references (not source-file paths); editing a translatable English source string invalidates the matching msgid (orphans the translation — re-export and re-merge after); .po/.pot bytes must be decoded as explicit UTF-8 (never routed through latin-1 or a unicode_escape-style codec); and bilingual content must flow through the standard per-language PO merge pipeline (never a forked duplicate per-language view tree). Odoo-version-aware (14-19). Activates when a translation "doesn't apply" despite a filled msgstr, when reviewing a .po diff, after editing a translatable label/selection/help/view term, or before shipping a second language.
version: 0.1.0
last_reviewed: 2026-06-13
license: "MIT"
metadata:
  mode: codebase
  odoo-versions: ["14", "15", "16", "17", "18", "19"]
  categories: [i18n, translation, gettext, po, audit, rtl]
  filePattern: ["**/i18n/*.po", "**/i18n/*.pot"]
  model: sonnet
owns:
  - the "msgstr filled but translation does not apply" audit
  - the typed-reference vs source-path rule for labels/selections/help/view terms
  - the source-string-edit -> msgid-invalidation -> re-export/re-merge discipline
  - the explicit-UTF-8 decode rule for PO bytes (no latin-1 / unicode_escape)
  - the one-arch / one-.pot / one-.po-per-language bilingual pipeline (no forked _<lang> views)
defers_to:
  - skills/i18n/references/po-gettext-discipline.md (full per-rule detail and commands)
  - skills/i18n/SKILL.md (extract / validate / report / import-export workflows)
  - skills/upgrade/references/theme-load-and-cli-upgrade.md (theme-translated-fields mapping; reload via CLI)
---
<!-- Last updated: 2026-06-13 -->

# Odoo i18n Audit Skill

A translation that is fully filled in the `.po` can still render in the source
language at runtime. This skill is the **audit pass** for the four ways that
happens in Odoo. It is generic and version-aware (Odoo 14-19); the deep
per-rule detail and exact commands live in
`skills/i18n/references/po-gettext-discipline.md` — read that file when applying
a fix. Use this SKILL.md as the checklist that decides *which* rule is in play.

## When to use

Activate when any of these is true:

- A label/menu/selection/help text/website term shows the **source language**
  even though its `msgstr` is filled in the `.po`.
- You are reviewing a `.po` / `.pot` diff in a PR.
- You just edited a **translatable English source string** (a field `string=`
  or `help=`, a selection label, literal text in a QWeb view, or a `_()` /
  `_lt()` argument).
- You are about to ship a **second language** for a module or theme.
- Tooling that reads/writes `.po` bytes is producing mojibake.

Do NOT use this skill to *write* the translations — that is `skills/i18n`
(extract / validate / report / import-export). This skill decides whether the
translation will actually bind.

## The four audit rules

### 1. Typed references, not source-file paths

For **field labels, selection values, help text, and QWeb view terms**, Odoo
binds a `.po` entry to its target via the **typed reference comment** above the
entry — not the `msgid` text alone. A path-style `#:` reference
(`addons/<module>/models/foo.py:42`) does **not** bind a label; the entry looks
complete but applies to nothing and the UI falls back to source.

The typed forms Odoo emits and matches against:

| Target | Typed reference form |
|---|---|
| Field label | `model:ir.model.fields,field_description:<model>,<field>` |
| Field help/tooltip | `model:ir.model.fields,help:<model>,<field>` |
| Selection option | `model:ir.model.fields.selection,name:<model>,<field>,<value>` |
| Term inside a view arch | `model_terms:ir.ui.view,arch_db:<module>.<view_id>` |

**Audit action:** never hand-write these. Regenerate the canonical `.pot` via
the Odoo i18n export (which walks the registry and emits correct typed
references), then merge existing translations into it. See reference §1.

### 2. Source-string edits invalidate the msgid

A gettext `msgid` is keyed on the **exact** English source string. The instant
you change a translatable English literal — reword a field label, fix a typo or
trailing space, re-case/re-punctuate a selection value, split or join a string —
the old `msgid` no longer matches the registry. The entry is **orphaned**: its
`msgstr` is still in the `.po`, but at runtime the new source has no match and
falls back to source.

**Audit action:** after **any** user-facing source edit:

1. Re-export the `.pot` so the new `msgid` appears.
2. `msgmerge --previous` each language `.po` against the new template — a
   reworded source becomes **fuzzy** (carrying the old translation as a hint); a
   removed source becomes **obsolete** (`#~`).
3. Refresh the fuzzy/obsolete entries. A `fuzzy` flag is **not** applied at load
   time, so a fuzzy entry counts as untranslated until you confirm it and drop
   the flag.

Never "fix" the fallback by editing the live `.po` `msgstr` while leaving a stale
`msgid` — it re-orphans on the next export. Fix the `msgid` via re-export +
merge, then fill the `msgstr`. See reference §2.

### 3. Decode PO bytes as explicit UTF-8

`.po` / `.pot` files are UTF-8 (the header declares
`Content-Type: text/plain; charset=UTF-8`). Any tool you write to read, rewrite,
or diff them must decode **explicitly as UTF-8**.

The trap: routing PO bytes through a `unicode_escape`-style codec (or any
"escape/unescape" pass that treats backslashes as string escapes), or through
`latin-1`. That mangles every multi-byte UTF-8 sequence — accented Latin,
Cyrillic, **Arabic**, CJK, emoji — silently. The file still parses, so the
corruption ships unnoticed until someone reads the rendered label.

Keep two concerns **separate**:

- **File encoding** → always `open(path, encoding="utf-8")` (or
  `bytes.decode("utf-8")`). Never `unicode_escape`, never `latin-1`, never a
  charset guess.
- **PO-quote escapes** (`\"`, `\\`, `\n`, `\t`) → these are *PO syntax*, not
  Unicode escapes; unescape them with PO-aware logic (or a real PO library),
  not a string-escape codec.

Prefer a real PO library (it gets both right). See reference §4.

### 4. One arch, one .pot, one .po per language — never fork per-language views

The supported way to maintain a second language is **one source tree, one
`.pot`, one `.po` per language**. Forking a parallel `_<lang>` copy of a view
(or model) to hold translated text defeats gettext: the trees drift, IDs collide
or diverge, and the translation never flows through the loader. All language
variants of a view come from the **same** `arch`, translated through
`model_terms:ir.ui.view,arch_db:...` entries in the `.po`.

**Audit action — the canonical bilingual loop:**

1. Export the `.pot` from the installed module (single source of truth for
   `msgid`s and typed references).
2. `msgmerge --previous --update <module>/i18n/<lang>.po <module>/i18n/<module>.pot`.
3. Fill new entries; confirm fuzzy entries and drop the flag; leave obsolete
   (`#~`) unless deliberately pruning.
4. Reload via the CLI import / module upgrade so the refreshed `.po` is applied.

Hard rule: **never fork duplicate `_<lang>` view trees** (or shadow models) to
carry translations. See reference §3.

## Version-aware notes (Odoo 14-19)

| Concern | 14-15 | 16-17 | 18-19 |
|---|---|---|---|
| Translation storage | `ir.translation` table | JSON terms (internal) | JSON terms |
| JS translation import | `from "web.core"` | `from "@web/core/l10n/translation"` | same as 16 |
| View root tag (affects `arch_db` term ids) | `<tree>` | `<tree>` | `<list>` (19) |
| Clear translation cache | `ir.translation.clear_caches()` | `clear_caches()` | registry reload on `-u` |

Export format is `.po` on every version even where storage is JSON internally —
the typed-reference and msgid rules above are identical across 14-19. Only the
JS import path and the view root tag (which changes the `arch_db` term ids the
export emits) differ.

## Audit checklist

- [ ] Label/selection/help/view terms carry **typed references** from the Odoo
      export — not source-file paths.
- [ ] After any user-facing source-string edit, the `.pot` was re-exported and
      each `.po` re-merged; fuzzy/obsolete entries were treated as untranslated.
- [ ] Every tool touching `.po` bytes decodes **explicit UTF-8**; no `latin-1`
      / `unicode_escape` pass; PO-quote escapes handled separately.
- [ ] Second language flows through one `.pot` + `msgmerge` + one `.po` per
      language — **no** forked `_<lang>` view/model trees.
- [ ] For theme-backed models, every translatable field is in the
      theme-translated-fields mapping (see upgrade reference) before reload.
- [ ] Reload was done so the refreshed `.po` actually applied (module upgrade /
      CLI import), then a non-default language was spot-checked in the UI.

## Anti-patterns

| Anti-pattern | Why it is wrong | Correct |
|---|---|---|
| Hand-writing `#:` references for labels | Path refs do not bind labels; entry applies to nothing | Generate typed refs via the Odoo i18n export |
| Editing the live `.po` `msgstr` to fix a fallback after rewording the source | Re-orphans on next export; stale `msgid` | Re-export `.pot`, re-merge, then fill `msgstr` |
| `raw.decode("unicode_escape")` / `latin-1` on PO bytes | Silently corrupts every non-ASCII char | `open(..., encoding="utf-8")`; PO-aware unescape separately |
| Forking `view_form_ar.xml` for the Arabic copy | Trees drift; loader never sees it; IDs collide | One arch, translate via `arch_db` terms in `ar.po` |
| Treating a `fuzzy` entry as done | Fuzzy is not applied at load — counts as untranslated | Confirm and drop the `fuzzy` flag |

## Cross-references

- `skills/i18n/references/po-gettext-discipline.md` — full per-rule detail,
  export/`msgmerge`/import commands, and `msgattrib` audit snippets.
- `skills/i18n/SKILL.md` — extract / validate / report / import-export tooling.
- `skills/upgrade/references/theme-load-and-cli-upgrade.md` — the
  theme-translated-fields mapping rule and CLI reload that this audit depends on
  for theme-backed translations.
