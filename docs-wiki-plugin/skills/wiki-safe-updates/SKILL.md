---
name: wiki-safe-updates
description: add the plan-first/dry-run preview, deterministic content-preserving edits, governed safe move/rename/delete + link repointing, pre-write dataset validation, and live-wiki/work-item-as-approval-needing-publish — while KEEPING the "still advisory and non-blocking for plain GitHub-wiki pushes / Help, not gates" framing.
version: 1.1.0
last_reviewed: 2026-06-22
owns:
  - diff-preview suggestion (optional)
  - revert-based rollback tip
  - one-purpose-per-commit tip
  - retired-folder awareness
  - optional reference check before deleting a page
  - plan-first/dry-run preview for multi-step restructures
  - deterministic content-preserving edit recipe (fetch then targeted replace then re-fetch verify)
  - safe move/rename/delete + link-repoint ordering (specific-child-paths first, bare-parent last)
  - pre-write validation of generated/derived datasets against source
  - stop-and-report gate at the write boundary (advisory)
  - live-wiki/work-item write treated as an approval-gated publish + per-target delete instruction
  - Azure visible-heading idempotency marker (HTML-comment sentinels get stripped)
  - post-pass validation-checklist runner concept (references + composes the owning skills' checks)
defers_to:
  - wiki-structure (structural conventions a write may follow; pagemoves/newOrder/%2D/link-form mechanics)
  - wiki-link-validation (optional pre-push broken-link sweep; the resolution-based stale re-scan)
  - wiki-source-of-truth (the never-silently-pick-a-side / provenance judgement)
  - wiki-code-vs-docs-discrepancy (optional code-vs-wiki drift report)
  - references/safe-doc-deletion.md (capture-check + cross-ref sweep — the childless rule layers on top)
  - project release SOP (any project-specific wiki-publishing convention)
user_invocable: false
---

# wiki-safe-updates

## Purpose

Helpful, **optional** tips for working on a GitHub wiki. None of this blocks you — the
plugin imposes **no gates** on writing, pushing, force-pushing, or deleting. Use what's
useful; skip what isn't. A GitHub wiki publishes the moment its repo is pushed
(`git push` is the deploy), so these tips just help avoid the common foot-guns.

## Tips

**Preview before a big overwrite (optional).** For a large edit to an existing page it
can help to glance at the diff first so a wrong edit is easy to catch — but writing the
file directly is completely fine when you already know what you want.

**Rollback with revert (keeps history).** If a change goes wrong:

```
git -C <wiki-repo-path> revert <commit-sha>
git -C <wiki-repo-path> push
```

`git reset --hard` and force-push also work if you prefer them — your call. `revert` is
just friendlier because it preserves the published history.

**One purpose per commit (optional, tidier rollback).** Keeping content edits, renames,
and sidebar/navigation changes in separate commits makes a single `revert` clean. Mixed
commits are fine too.

**Retired-folder awareness.** Folders intentionally archived (`_archived/`,
`_deprecated/`, `historical/`, `_old/`, `attic/`) hold non-current content. The audit
skills skip them so they aren't flagged as "drift":

```json
{ "retiredFolders": ["_archived/", "_deprecated/", "_legacy/"] }
```

**Before deleting a page (optional sanity check).** Deleting a page breaks any inbound
links to it. If you'd like, grep for references first — `references/safe-doc-deletion.md`
has a checklist — but it's a suggestion, not a requirement. On tree-namespace flavours
(Azure DevOps), there is no "empty folder" to delete: a section is a real page, so move
every child out first and delete only the now-CHILDLESS page. That childless precondition
layers on top of the `references/safe-doc-deletion.md` capture-check + cross-reference
sweep — it does not replace them.

## Pushing

Pushing the wiki is **unrestricted** — there is no approval gate and no force-push block.
Push whenever you're ready:

```
git -C <wiki-repo-path> push origin master
```

### Scoped carve-out: live-wiki / work-item writes are approval-gated publishes

The unrestricted posture above is for the **GitHub-wiki git-push path**: the push *is* the
deploy, and the skill stays advisory ("Help, not gates"). That does not change.

One scoped boundary sits on top of it. A write that goes **directly to a LIVE wiki via
REST/MCP** (e.g. an Azure DevOps wiki `wiki_create_or_update_page` / REST PUT / `pagemoves`),
or a write to an **Azure DevOps WORK ITEM**, is itself the publish — there is no separate
local commit a reviewer could read first. Treat those as **publishes that need explicit
owner approval before the write**. A plan-first approval (see below) covers a whole batch in
one go. **Deletes are stricter:** a delete needs an explicit **per-target** instruction, not
a blanket batch approval.

| Write path | Posture |
|---|---|
| GitHub-wiki `git push` (commit-then-push deploy) | Advisory / unrestricted — unchanged. The push is the deploy; preview is a help, not a gate. |
| Live-wiki write via REST/MCP (Azure/live) | Approval-gated publish — the live write is the deploy; get explicit owner approval first (plan-first covers the batch). |
| Azure DevOps work-item write | Approval-gated publish — same approval before writing the Description/field. |
| Any delete (page or work item) | Approval-gated publish AND an explicit per-target instruction — never a blanket approval. |

This mirrors the `wiki-plantuml` swimlane pipeline, whose `publish_update.py` enforces an
explicit `--approve` step before the live publish (cross-referenced below). This skill stays
advisory for plain GitHub-wiki pushes; the approval gate applies only to the live-wiki /
work-item publish path.

## PLAN-FIRST / DRY-RUN mode (optional, for multi-step restructures)

For any operation touching **more than one page** or repointing links — a move, rename,
restructure, bulk repoint, or a traceability pass — produce the FULL plan **before writing
anything**. The plan is the unit of approval: nothing is written until the owner approves it.

The plan lists, in dependency order:

1. **Ordered operations** — creates → moves → deletes → link-rewrites → reorders. Ordering is
   load-bearing and is reviewed: a delete only appears **after** its children have been moved
   out (delete a childless page), and link-rewrites follow the moves that change the paths.
2. **Per-page diffs** — what each touched page gains or loses.
3. **Counts** — pages moved, links to repoint, deletes.
4. **Risks** — anything that might change business meaning (surface it; see Stop-and-report).

This keeps the advisory posture: it is a **strong default, not a hard gate**. A plain one-page
edit still just writes directly — the "writing the file directly is completely fine" tip above
stands. Plan-first kicks in only when an operation fans out across pages or rewrites links.

## Deterministic, content-preserving edits

When an edit must change only specific spans of an existing page, do NOT hand-reconstruct the
page. Use the deterministic recipe:

1. **FETCH** the current page content.
2. **Targeted string-replace** of exactly the spans that must change (e.g. the old link, the
   old path) — and nothing else.
3. **WRITE** the result.
4. **RE-FETCH** and confirm the business text is **byte-unchanged except for the intended
   spans**.

This is how 1,516 links were repointed across a wiki with **zero business-text drift**,
verified by re-fetch. The re-fetch is the proof: a preview catches the *wrong* edit before
writing, but only a post-write re-fetch catches silent platform **normalization** (HTML
rewrites, entity changes). This recipe **extends** the "preview before a big overwrite" tip —
preview is the pre-write half, re-fetch-verify is the post-write half.

## Safe move / rename / delete + automatic link repointing

A move or rename changes a page's path, so **every inbound link must be repointed in the same
change set** — the platform does not auto-rewrite them (Azure DevOps especially never
auto-repoints inbound links on a move). The `pagemoves` / `newOrder` / MCP-reversed-order /
`%2D` basename / human-provisioned-wiki mechanics are owned by **wiki-structure**'s Azure
adapter — reference it, do not restate.

Net-new and **load-bearing here**: when applying the link replacements, apply
**specific-child-paths FIRST, the bare-parent-path LAST**, so rewriting `/Parent` does not
mangle the already-correct `/Parent/Child` links.

- After any move / rename / delete, **RE-SCAN to ZERO stale** old-path references. (Defer the
  resolution-based scan mechanism itself to **wiki-link-validation**.)
- Delete only a **CHILDLESS** page (move children out first — see the delete tip above).
- A link whose target no longer exists is **REPORTED, never silently dropped**.

## Pre-write validation of generated / derived datasets

Before **bulk-writing** any large generated or derived dataset — a harvested Figma node index,
a PBI→page mapping, a link map — **VALIDATE it deterministically against its source FIRST**:

- every entry is **verbatim-present** in the source,
- no **invented** entries,
- paths are **well-formed**.

This caught fabricated Figma nodes (`1863-4852`) and malformed spec paths produced by a
sub-agent **before** the live write reached the wiki / PBIs. Never trust a sub-agent's
generated dataset as input to a live write without source-validation. Coverage may be partial
by nature — report the exact / lane / pending counts honestly; never fake completeness.

## Stop-and-report on possible business-meaning change

Any edit that **MIGHT change business meaning** is **halted and surfaced**, not applied.
Reorganisation is **move + relink + additive orientation only**. This skill owns only the
**STOP at the write boundary**; the which-way-it-resolves / provenance judgement is deferred
to **wiki-source-of-truth**.

Concretely, this gate surfaces (it does not auto-resolve):

- a hub / summary page that is starting to **restate a child's authoritative rules**;
- an edit touching **acceptance criteria, scope, backlog hierarchy, work-item State, Story
  Points, or tags**;
- any **Figma design change**.

## Azure idempotency marker must be a visible heading (azure-specific)

On Azure DevOps, saving a page or a work-item Description **NORMALIZES the HTML and STRIPS HTML
comments** (and rewrites self-closing tags / entities). So an idempotency sentinel — the marker
a re-run keys off to avoid double-appending — must be a **VISIBLE heading** (e.g. a
`## Traceability` heading), **NOT an HTML comment**. A comment marker vanishes silently on save,
so the next run does not see it and **double-appends**. Verify a single sample after the first
write before going bulk.

## Post-pass validation-checklist runner (concept, advisory)

After any restructure / repoint / traceability pass, run the post-pass checklist and emit
pass/fail with **evidence counts** — the "did the plan land cleanly" counterpart to plan-first.
Do NOT duplicate the individual checks; they live in their owning skills (resolution-based link
audit in **wiki-link-validation**, structural checks in **wiki-structure**, and so on). This
runner **references and composes** them.

Two checks this skill asserts post-write directly:

- **0 stale old-path references** remain (the re-scan after a repoint).
- **All reads SUCCEEDED** before declaring any "0 findings" — a page that failed to load must
  never be silently counted as clean.

## Validation checklist

Before declaring a multi-page change done:

- [ ] Plan approved **before** any multi-page write (plan is the unit of approval).
- [ ] Re-fetch confirmed business text **unchanged** except the intended spans.
- [ ] **0 stale** old-path references after any repoint (re-scan).
- [ ] Generated / derived datasets **source-validated** before the bulk write.
- [ ] Idempotency markers are **visible headings** (Azure), not HTML comments.
- [ ] Deletes operated on **childless** pages and each had an explicit **per-target**
      instruction.
- [ ] **All reads succeeded** (no silently-skipped pages) before any "0 findings."

## Anti-patterns (and why)

| Anti-pattern | Why it's wrong | Correct |
|---|---|---|
| Run a 290-link repoint to a live wiki ungated | A live-wiki REST/MCP write is itself the publish; there is no commit a reviewer reads first | Plan-first; get explicit owner approval for the batch before writing |
| HTML-comment idempotency marker on Azure | Azure strips HTML comments on save; the next run can't see it and double-appends | Use a visible `## Traceability`-style heading; verify a sample first |
| Delete a section page that still has children | On tree-namespace flavours a section is a real page; deleting it orphans the subtree | Move every child out first; delete only the now-childless page (per-target instruction) |

## Cross-references

- `wiki-plantuml` — its swimlane publish (page edit + the committed image / `/.attachments` upload) routes through this skill's diff-preview before push; `publish_update.py` enforces an explicit `--approve` step. (This skill itself stays advisory; the swimlane pipeline supplies the approval gate. The live-wiki/work-item carve-out above mirrors that `--approve` framing.)
- `wiki-structure` — structural conventions a write may follow; owns the Azure pagemoves / newOrder / `%2D` basename / MCP-reversed-order / human-provisioned-wiki and internal-link-form mechanics this skill references but never restates.
- `wiki-link-validation` — optional pre-push broken-link sweep; owns the resolution-based stale re-scan this skill calls for after a repoint.
- `wiki-source-of-truth` — owns the never-silently-pick-a-side / provenance judgement; this skill only STOPs at the write boundary and defers the resolution.
- `wiki-code-vs-docs-discrepancy` — optional code-vs-wiki drift report.
- `wiki-vs-stray-docs` — suggests (does not force) keeping team docs in the wiki.
- `references/safe-doc-deletion.md` — optional pre-deletion checklist (capture-check + cross-reference sweep); the childless-page precondition layers on top of it.
- `wiki-link-auditor` (agent) — automates the optional pre-push link validation.
