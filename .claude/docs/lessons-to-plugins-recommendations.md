# lessons-to-plugins — recommendations

Regenerated 2026-09-27. Supersedes the 2026-09-12 edition.

This run took the newest batch: the 48 lessons `/lessons` added on 2026-09-27.
The batch was 31 lessons: 24 Odoo-routed or framework-neutral, plus 7
project-specific. 9 lessons were absorbed into 5 skills across 2
plugins. Everything below is what could **not** or should **not** be absorbed,
with the reason. The 17 remaining 2026-09-27 lessons (Django/DRF, React/CSS,
release, user preferences) were not analyzed this run and stay candidates.

> **Status: complete.** Committed as `e302c75`; P9 recorded in the ledger (9 absorbed,
> 15 deferred, 7 rejected; `ledger_write.py verify` clean).
---

## Corpus state after this run

| | |
|---|---|
| Lessons in corpus | 503 (h2 = 139, h3 = 325) |
| Ledger entries | 193 (162 + 9 absorbed + 15 deferred + 7 rejected) |
| Candidates remaining | 332 (348 - 31 resolved + 15 deferred that stay live) |
| Analyzed this run | 31 |

---

## New-plugin / new-skill candidates

### Visual-parity measurement — carried over, owner APPROVED, **not implemented**

This is unchanged from 2026-09-12. Six lessons (`120cd969880a`, `b32c36cb624f`,
`836d0b726568`, `fe6001629221`, `c71dee5fe6bd`, `96f6a39b6852`) are approved for
a new `react-kit` skill that owns visual-reference comparison. It has not been
built yet and still needs a dedicated run. This run's `13da2cc4aafe` (CSS `zoom`
subtree coordinates) and `74e9f3e0fb2c` (unlayered CSS beats Tailwind utilities)
are unanalyzed candidates in the same neighbourhood. Consider them when that
skill is built.

### Odoo stock / import mechanics — watch, below threshold

Five deferred lessons from one investigation share a domain that no shipped
Odoo skill owns: product/stock data import. They are `e9c3012df980` (variant
barcodes), `35bab7c43af8` (nomenclature prefixes), `b8e054d57f02`
(`stock.quant` import whitelist), `2215dc931a16` (`complete_name` at view
locations) and `a27d1f2d754e` (website availability per warehouse).

Together they meet the lesson count for a new skill (≥ 4), but they span only
**one date and one project**, so they fail the ≥ 2-dates rule. Re-score them
once a second, independent stock-import incident is recorded. A candidate home
would be an `odoo` data-migration/import skill.

---

## Human decisions outstanding

### `25e279e68077` — carried over, coverage PARTIAL

The linter-validation lesson is still unresolved, for the same reason as on
2026-09-12. Rule 9 of `test-result-evidence` ships only one of its four claims,
and no skill owns authoring a scan rule set. The recommended next step is
unchanged: seed a scan-rule-authoring rule set, either in `structural-assertions`
or as its own skill.

### Framework defect — carried over, not fixed

The `lessons_index.py` section-attribution defect is still open. The trailing
`h2` regime still inherits the `## Processing Log` label. See
`claude_plugins/.claude/docs/2026-09-12_lessons-index-section-attribution-defect.md`.

---

## Absorbed this run

| id(s) | Owner | Rule (short) |
|---|---|---|
| `124f23b1fd71` | `odoo/stack-doctor` (`references/db-safety.md`) | The conf key is `dbfilter`. `db_filter` is ignored silently. This corrected a shipped table that used the wrong key |
| `a9cde60abdb3` `9ca81e803bf1` `a198a6fab615` | `odoo/upgrade` | `-u` reconciles module-owned data. Three cases: hand-deleted shipped records are re-created and fail; hotfix records given a module xmlid are deleted; UI edits to code-defined records are reverted, and a Portal ↔ Internal role switch cannot be done in place |
| `a7f4f363e6f0` | `odoo/security` | Widen portal/public visibility with a narrow rule on the user's own group, or sudo one search term. Never grant public ACLs on internal models |
| `d3367a8e5936` `c9312ccf0ab7` `167c39093edb` | `odoo/mcp` | A domain on a non-stored field is dropped on 17/18 (verified in source). The shared profile file needs a DB re-check before each write. `cannot marshal None` fires after the commit |
| `3a359a0a120b` | `agent-safety-guards/defensive-failure-design` rule 7 | An idempotent skip must not skip a side effect that later steps depend on. A missing lookup is a hard error, not a default |

## Deferred (stay live, re-scored next run)

| id | lesson | Score | Why |
|---|---|---|---|
| `59a4e62c57ee` | Odoo menu missing after a group change → cached `load_menus` hash | 4 | Singleton, < 14 days old, no severity |
| `e9c3012df980` | Odoo 17 product barcode lives on the variant; uniqueness goes global | 4 | Stock-import cluster, see above |
| `35bab7c43af8` | Barcode nomenclature matches on prefix; label print never rejects a bad EAN-13 | 4 | Stock-import cluster |
| `b8e054d57f02` | `stock.quant` import: lots first, column whitelist, auto-apply skips wizards | 4 | Stock-import cluster |
| `2215dc931a16` | `stock.location.complete_name` restarts at view locations | 4 | Stock-import cluster |
| `a27d1f2d754e` | Website stock availability is per warehouse | 4 | Stock-import cluster |
| `7046ab28b34d` | Odoo 19 API provisioning: chart install resets currency; `group_ids` ≠ effective groups | 4 | Three unrelated facts; no single owner (mcp vs security) |
| `af6fd9219442` | Odoo.sh "unknown" dependency → refresh the Apps list first | 3 | Singleton, new; no hosting-platform skill |
| `e717d59dee0f` | Missing manifest `depends` hidden locally; fresh-DB install before promotion | 4 | Singleton, new. `reviewer/references/module_manifest.md` is the likely home once it recurs |
| `2234f3eb4543` | Warehouse install hooks: blanking a `*_pull_id` pointer twice orphans rules | 5 | Severity is real (silent wrong operation type), but ownership is ambiguous: no stock skill, and `upgrade` owns migrations, not install hooks |
| `4ca7a638cb25` | Portal QWeb: render datetimes with the widget | 3 | Singleton, no severity |
| `401cd2d9e660` | Don't gate controls on quantity truthiness; HTML `max` is a hint | 4 | Framework-neutral and QWeb-shaped at once; ambiguous owner |
| `294df522757c` | Backend buttons need `groups` matching the method's ACL | 4 | Singleton, no security severity (the failure is an AccessError, not exposure) |
| `a01e339760ed` | Browser-pane UAT stalls when the Claude window is hidden | 4 | Specific to one host app; `qa-browser` would own it if it recurs |
| `9976b08273f3` | Global group toggles through the UI; production writes scoped to exactly what was authorized | 3 | The "don't route around a guard" half is already shipped in `odoo/mcp`; the production-scope half is a working convention |

## Rejected — project-specific, never crosses into a plugin

These stay in `LESSONS.md` → Project-Specific Lessons, where they are already
recorded. They were not migrated to project memory in this run.

| id | lesson |
|---|---|
| `d611390d4e89` | Medline Odoo 19 stock spike findings (the generic "spike on a scratch DB first" habit is not new) |
| `c62f492c12ef` | Medline operation milestones move only on `_signal` |
| `a9f5463e8b65` | Medline portal mobile-stack class placement |
| `cabc5b8169cd` | Cluster2 Settings blocked by Webkul marketplace required fields |
| `ce729edf314e` | Cluster2 submodule re-pin bot |
| `d4c6d3219097` | ApiaryAndHoney Odoo.sh staging rebuild wiped UAT setup |
| `24f35bf6a98d` | Company Odoo repo standard (addons-only root, vendored OCA, branch flow) |

Also excluded from this batch because they are not generic: `22b4477d76d0` (check
the manifest author before saying "vendor"), `2fb162c55c55` (Excel Data
Validation) and `e87b922af7a2` (Azure DevOps default branch). They were not
analyzed this run and remain candidates.

---

## Counts for this run

| | |
|---|---|
| Candidates in | 348 |
| Analyzed | 31 |
| **Absorbed** | **9** → 5 skills (+1 reference), 2 plugins, 12 files, +108 / −9 lines |
| Deferred | 15 |
| Rejected (project-specific) | 7 |
| Already covered | 0 |
| Gates passed | `validate_plugin.py` exit 0 on both touched plugins · `validate_marketplace.py` exit 0 (no architecture errors) · `validate_evals.py` 0 FAIL/0 WARN · 0 deletions · no frontmatter touched, all descriptions byte-unchanged · noun sweep clean on every added line |
| Size | `mcp` +13.2% (129→146), `upgrade` +7.9% (354→382), `security` +4.6% (393→411), `defensive-failure-design` +4.7% (172→180). None over 15%, all under the 500-line cap |
