# lessons-to-plugins — recommendations

Regenerated 2026-10-19. Supersedes the 2026-09-27 edition.

This run took the newest batch: lessons `/lessons` added on 2026-10-17 to 2026-10-19.
25 of them were analyzed: 22 Odoo-routed, plus 3 framework-neutral. 8 were absorbed
into one skill's references (`odoo/reviewer`). Everything below is what could
**not** or should **not** be absorbed, with the reason. Six lessons from the same
dates (`e2c30a0ae9bc`, `7267fac29f2c`, `a80eee2784b1`, `aeeff69aff29`,
`ec20ab3f35d1`, `069df40d60a8`: React auth sync, research fan-out, review alerts,
user preferences) were not analyzed this run and stay candidates.

> **Status:** odoo 2.13.1. The ledger is written after the commit (P9).

---

## Corpus state after this run

| | |
|---|---|
| Lessons in corpus | 568 (h2 = 146, h3 = 383) |
| Ledger entries | 218 (193 + 8 absorbed + 13 deferred + 4 rejected) |
| Candidates remaining | 385 (397 - 12 resolved; the 13 deferred stay live) |
| Analyzed this run | 25 |

---

## New-plugin / new-skill candidates

### Visual-parity measurement — carried over, owner APPROVED, **not implemented**

Unchanged since 2026-09-12. Six lessons (`120cd969880a`, `b32c36cb624f`,
`836d0b726568`, `fe6001629221`, `c71dee5fe6bd`, `96f6a39b6852`) are approved for a
new `react-kit` skill that owns visual-reference comparison. It still needs a
dedicated run. `13da2cc4aafe` and `74e9f3e0fb2c` sit in the same neighbourhood.

### Odoo stock / import / inventory mechanics — watch, now two dates

The 2026-09-27 stock-import cluster (`e9c3012df980`, `35bab7c43af8`, `b8e054d57f02`,
`2215dc931a16`, `a27d1f2d754e`) gained two related lessons on 2026-10-17:
`f40fb543b813` (17.0 products default to Consumable; type locks after the first done
move) and `b8074a3d5fc7` (reservation follows `child_of`, hand-typed MO quantities do
not). The cluster is now 7 lessons over 2 dates, which meets the new-skill count and
date rules, but every incident is still from **one client's databases**. Recommended:
an `odoo` stock/inventory-data skill once one incident from another project lands.
Needs a human decision on whether one project is enough.

---

## Human decisions outstanding

### `974976b81547` — Needs Review upstream

`db_name` set together with a non-empty `dbfilter` reportedly makes every request do a
DB lookup ("Connection Pool Is Full"). It extends the shipped `dbfilter` rule in
`odoo/stack-doctor/references/db-safety.md`, but it was observed once, from a
generated conf. Confirm against `odoo/http.py` before shipping.

### `850b4ed0adad` — Needs Review upstream

A command and a skill with the same name in one plugin may shadow each other (10 of
20 skill invocations failed with "Unknown skill"). The root cause (name collision vs
plugin not enabled) was not confirmed. If confirmed, the owner is
`claude-plugin-builder` (a house rule plus a validator check).

### `25e279e68077` and the `lessons_index.py` section-attribution defect

Both carried over unchanged from 2026-09-27.

---

## Absorbed this run

| id | Owner | Rule (short) |
|---|---|---|
| `a48542b816f7` | `odoo/reviewer` `security_pitfalls.md` | Elevation needs a trigger RPC cannot send (private method, identity-compared sentinel); `context.get()` guarding `sudo()` is a finding |
| `b4d35115c51c` | `odoo/reviewer` `security_pitfalls.md` | An app's Administrator group can bypass agreed scoping (rule exemptions, `implied_ids`); grant a narrow manager group instead |
| `e50f8dd60ba5` | `odoo/reviewer` `orm_patterns.md` (partial: mechanism already shipped) | Tests that assign a stored compute go through `write()` and hide the dead hook; test through the business flow |
| `c4235ecfb04c` | `odoo/reviewer` `orm_patterns.md` | Custom per-line `stock.move` fields must be in `_prepare_merge_moves_distinct_fields` |
| `4f970f76392b` | `odoo/reviewer` `orm_patterns.md` | On 17.0 a filter on `display_name` is dropped and matches everything; tied search-view priorities resolve by name |
| `b8117d9913dd` | `odoo/reviewer` `orm_patterns.md` | A "missing" method lives on another module declaring the same `_name`; check which one is installed (two incidents) |
| `14224c8530b7` | `odoo/reviewer` `v20_deltas.md` | `ir.access` permissions are OR-ed, so a narrowing must be on every granting row; child rows chain off the parent's grant |
| `332d2b33b7fd` | `odoo/reviewer` `v20_deltas.md` | Verified table of models and fields removed or renamed in 20 |

All 20.0 facts were re-verified against the local 20.0 source before shipping.

## Deferred (stay live, re-scored next run)

| id | lesson | Score | Why |
|---|---|---|---|
| `6431bb56193c` | Fast WSL Odoo testing: core on WSL's disk, template-DB clones | 6 | Score qualifies, but the owner `odoo/test` `SKILL.md` is 1,940 lines; it needs a `references/` extraction first. Do it as a dedicated edit |
| `243cdaf0d237` | Per-website view copies survive upgrades and call removed templates | 5 | Severity real (500s), owner ambiguous: website/theme skills vs reviewer |
| `e67ac3873aad` | `gh issue create` drops labels/assignee without triage access | 5 | Two incidents, but no plugin owns GitHub issue filing |
| `fa6df3c04113` | Outbound sync: `ir.cron._trigger()` after validate, not a push inside it | 4 | Singleton, < 14 days |
| `d23f81eaf976` | Wizards driven over RPC/MCP get no onchange | 4 | Singleton, < 14 days; `odoo/mcp` is the likely home |
| `99add7ca8cfb` | Triage access complaints by dialog title and field `groups` | 4 | Singleton, no severity |
| `f5962377f9b3` | `pos_sale` cancels the delivery as the cashier; restrictive picking rules break payment | 4 | Generic part ("trace which core steps run without sudo") is close to shipped guidance; re-score on recurrence |
| `e8b05d620210` | Extend a code-defined role with a second UI role | 3 | The upgrade-revert half is already shipped in `odoo/upgrade`; the remainder is OCA-module specific |
| `f40fb543b813` | Products default to Consumable; type locks after done moves | 3 | Stock cluster, see above |
| `b8074a3d5fc7` | Reservation follows `child_of`; typed quantities do not | 3 | Stock cluster, see above |
| `ec36277219ed` | Don't edit a bash script while a run of it executes | 3 | Singleton, < 14 days, no incident (prevented) |
| `974976b81547` | `db_name` + `dbfilter` → pool exhaustion | — | Needs Review upstream |
| `850b4ed0adad` | Same-name command and skill shadow each other | — | Needs Review upstream |

## Rejected — project-specific, never crosses into a plugin

| id | lesson |
|---|---|
| `1a2148e9732b` | Reviewing a teammate's code-in-issue handovers for one project board |
| `13e80ce50a4a` | One client's access-change loop (staging test, prod command, reference page) |
| `fc1672892891` | One client's "sell from one location" decision; no OCA module exists |
| `9125c38f4684` | One client's stale pickings from editing settled orders (config, not code) |

---

## Counts for this run

| | |
|---|---|
| Candidates in | 397 |
| Analyzed | 25 |
| **Absorbed** | **8** → 1 skill (3 references), 1 plugin |
| Deferred | 13 |
| Rejected (project-specific) | 4 |
| Gates passed | `validate_plugin.py odoo-plugin` exit 0 · `validate_marketplace.py` exit 0 · 0 deletions · no `SKILL.md` or description touched · noun sweep clean on every added line |
| Size | `v20_deltas.md` +42% (66→94, **flagged**: new removed-names table), `orm_patterns.md` +5.1% (661→695), `security_pitfalls.md` +3.3% (365→377) |
