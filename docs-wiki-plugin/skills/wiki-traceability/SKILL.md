---
name: wiki-traceability
description: Owns the navigation-only bidirectional traceability model linking backlog work items <-> wiki workflow pages <-> Figma design nodes <-> specification source pages, plus the central Epic->Feature Traceability Matrix page. Activates when building or validating PBI traceability blocks, the matrix page, per-workflow Traceability tables, any backlog-wiki-design linking pass, or when grounding derived backlog stories in real requirement ids and classifying their readiness. Defers the navigation-only / not-a-source-of-truth principle to wiki-source-of-truth and all write governance to wiki-safe-updates.
version: 0.1.0
last_reviewed: 2026-06-22
owns:
  - the navigation-only bidirectional traceability link model (backlog work item <-> wiki workflow page <-> Figma node <-> specification source page)
  - the reverse-link compactness rule (a wiki page links the parent FEATURE work item, never every child story)
  - the central Epic->Feature Traceability Matrix page contract plus its mandatory navigation-only banner
  - the Figma node URL format and the colon->dash node-id conversion
  - the Figma share-token omission rule (the &t= token is sensitive and is never embedded/committed/propagated)
  - the harvest-don't-invent rule (the Figma node index is built from the canonical file first; only ids present in it are emitted)
  - the exact/lane-level/pending coverage classification and the three-count report
  - the requirement-id grounding rule (every derived story cites a harvested, verbatim-in-index requirement id)
  - the closed readiness enum and its quote-backed Ready bar (classify by the action required, never by the existing status string)
  - the traceability-block anchor placement (which visible heading anchors a re-run; the underlying Azure HTML-comment-stripping rule is owned by wiki-safe-updates)
  - the Description-only patch scope for a per-PBI block (business fields untouched and verified unchanged)
  - the deterministic pre-write validation of the full generated mapping before any bulk write
defers_to:
  - wiki-source-of-truth (owns the navigation-only / no-second-source / no-backlog-leakage principle this skill applies via the matrix banner)
  - wiki-safe-updates (owns diff preview, approval, and rollback for every wiki and work-item write; also owns the Azure HTML-normalization/comment-stripping gotcha this skill's anchor placement applies)
  - wiki-structure (owns the page-ID URL link form and the Azure adapter the matrix/reverse links consume)
  - wiki-link-validation (owns the resolution-based validation of the emitted links)
  - wiki-mermaid (owns the Azure-safe fence rules any matrix orientation map follows)
user-invocable: false
---

# wiki-traceability

## Purpose

Traceability is a **navigation-only layer** that wires four artifacts together so a reader can jump between them:

```
backlog work item  <->  wiki workflow page  <->  Figma design node  <->  specification source page
```

The whole value is **one click from a PBI to its screen, its journey, and its rules** — and back. The whole risk is that one of those artifacts quietly becomes an authoritative copy of another (a matrix that mirrors backlog state; a block that restates acceptance criteria). This skill owns the **link model** and the **matrix contract** that keep the layer navigational. It does **not** own page authoring, structure, or governance.

Tagline: **navigation, not duplication.**

This skill owns the *mechanics*. The underlying *principle* — that no artifact is a second source of truth, and that the backlog stays outside the wiki — is owned by `wiki-source-of-truth`; this skill **applies** it (via the matrix banner) rather than re-deriving it. Every write goes through `wiki-safe-updates`.

## When to use

Activate when:

- Writing or refreshing a per-PBI `Traceability` block on a work item.
- Building or refreshing the central `Traceability-Matrix` page.
- Adding per-workflow `## Traceability` tables to wiki workflow pages.
- Harvesting Figma node ids for traceability linking.
- Grounding derived backlog stories in requirement ids, or classifying their readiness.
- Running a `build-traceability` or `validate-traceability` pass.

Skip when:

- Authoring page content (use `wiki-authoring`).
- Moving / renaming / restructuring pages (use `wiki-structure`).
- Reconciling code-vs-docs drift (use `wiki-code-vs-docs-discrepancy`).

## Inputs (adapter)

Every value is a **named input**; nothing project-, tenant-, or file-specific is baked into the skill.

1. **`backlog_map`** — the mapping PBI / user story <-> parent Feature <-> Epic. Drives the matrix grouping and the reverse-link target.
2. **`page_id_map`** — a resolvable wiki target per page. The Azure page-ID URL form (`/{pageId}/{Slug}`) is **owned by `wiki-structure`** and only **consumed** here; this skill emits links in that form, it does not define it.
3. **`figma_file`** — `FILE_KEY` + `FILE_NAME` + the **harvested node index** (the list of real node ids present in the canonical file). Harvesting is **mandatory** — see "Figma node linking rules."
4. **`spec_owner_map`** — which specification page is authoritative for a given rule set. The *authority judgement itself* (which page owns a rule) is **deferred to `wiki-source-of-truth`**; this skill only consumes the resulting pointer.

## The bidirectional link model

Two directions, each with a fixed, ordered link set.

| Direction | From | Links to (ordered) | Why |
|---|---|---|---|
| **Forward** | PBI / user story | 1. primary workflow page · 2. most-specific real Figma node · 3. Product-Specification source page · 4. *(optional)* secondary workflow page | A reader on a backlog item reaches its journey, its screen, and its authoritative rules. |
| **Reverse** | wiki page | 1. the parent **Feature** work item · 2. related Figma node(s) · 3. the spec page | A reader on a wiki page reaches the backlog (via the Feature), the design, and the rules — without the wiki enumerating every story. |

**Forward** links are per-story: the **most-specific real** Figma node (not a lane-level fallback unless no exact frame exists), the authoritative spec page, and a secondary workflow link **only** for genuinely cross-cutting stories.

**Reverse** links target the **parent Feature** work item, **not** every child story. The Feature already parents its stories, so linking it gives one navigational hop into the backlog while keeping the wiki out of the business of enumerating backlog items — that enumeration lives in the backlog, where delivery state belongs.

**Compactness rationale:** linking the Feature (not each story) keeps the wiki from mirroring the backlog. Backlog membership and delivery state are owned by the backlog; the wiki only needs a doorway into it. (The no-backlog-mirror principle is owned by `wiki-source-of-truth` — applied here, not re-derived.)

## The central Traceability Matrix page

Exactly **one** page (`Traceability-Matrix`). Grouped **Epic -> Feature**. Carries a coverage column (`exact` / `lane` / `pending`).

**Mandatory top banner** (verbatim intent):

> **Navigation only — NOT a source of truth.** The backlog owns delivery state; the specification pages own the rules. This page only links them.

Column sketch:

| Epic | Feature | Workflow page | Spec page | Figma coverage |
|---|---|---|---|---|
| (epic) | (feature work item link) | (workflow page link) | (spec page link) | exact / lane / pending |

The matrix carries **links only** — to Feature work items, the Figma file, workflow pages, and spec pages. It **never** carries rule text, acceptance criteria, or mirrored backlog state (State, Story Points, assignment). It must not become a backlog mirror or a rules summary. (This applies `wiki-source-of-truth`'s no-second-source / no-backlog-leakage doctrine — do not re-derive that doctrine here; cite it.)

## Figma node linking rules

**Node URL format:**

```
https://www.figma.com/design/<FILE_KEY>/<FILE_NAME>?node-id=<NODE-ID-WITH-DASHES>
```

- **Colon -> dash conversion:** an API/Figma node id `15:31` becomes the URL parameter `node-id=15-31`. The colon in the id is always written as a dash in the URL.
- **The `&t=<SHARE_TOKEN>` is OMITTED — hard safety gate.** The `&t=` parameter is a **sensitive per-share view/tracking token**, NOT part of node addressing. The `node-id` alone resolves. **Never embed, commit, or propagate** a pasted `&t=` token across generated links. This skill enforces omission directly — it does **not** rely solely on the hook. (`agent-safety-guards:agent-safety` is the enforcing hook that flags a leaked token; this gate is the in-skill belt to its braces.)
- **Harvest, never invent.** Build the node index from the canonical file **first** (e.g. `get_metadata` on the file's canvases), and emit **only ids present in that index**. A fabricated id (such as `1863-4852`) must be caught by deterministic pre-write validation and **never shipped**.

**Coverage classification:**

| Class | When | Label |
|---|---|---|
| `exact` | a real frame for the story exists | direct node link |
| `lane` | only a workflow-level frame exists, no exact screen | must be labelled `Workflow-level Figma coverage — exact screen pending` |
| `pending` | no screen exists at all (e.g. backend-only story) | flag as needing an exact frame; never fake one |

Always report the **three counts** (exact / lane / pending). **Never imply full coverage when it is partial** — partial coverage is reported, not rounded up.

## Requirement-id grounding and readiness classification

When a backlog is **derived** from the specification pages, each story needs the same two things a Figma link needs — a real anchor, and an honest label for what is still missing. (The story's business-facing *body* is owned by `wiki-authoring`; this section owns only its anchor and its readiness class.)

**Ground every story in a real requirement id — harvest, never invent.** Build the requirement-id index from the specification pages **first**, and emit only ids present in that index. This is the Figma harvest rule applied to requirements, and it fails the same way: a plausible-looking id that no page defines passes a skim and survives review, so the story keeps a traceability label that dissolves at exactly the moment someone follows it to confirm the requirement. A story with no real id is reported as ungrounded — never given a manufactured one.

**Readiness is a closed enum, never free text:**

| Class | What it means | Action that clears it |
|---|---|---|
| `Ready` | a local source directly answers the blocker | none — proceed |
| `Needs Source Confirmation` | an existing catalogue / criteria set must be checked against the live design frame | verify against the frame |
| `Needs Design` | no layout or RTL treatment exists yet | author the design |
| `Needs Business Decision` | the answer is a business call nobody has made | route to the owner |

Two bars keep the enum honest:

- **`Ready` requires a verbatim quote.** Mark a story `Ready` only when a local source **directly** answers the blocker *and* the exact quoted line plus its source path is recorded. A source that is merely *about* the topic is not an answer. Without the quote, fall back to the conservative class. Readiness is consumed downstream as a go signal, so a story marked `Ready` on an inferred answer is pulled into a sprint and the gap surfaces mid-implementation, where it costs the most.
- **Classify by the action required — not by the status string already on the item.** Judge which of the four actions actually unblocks the story, and classify against the blocker that **drives** readiness, not a resolvable side thread. An item labelled "Ready" that still needs a layout is `Needs Design`. Never invent behaviour to make a blocker disappear.

## Per-PBI block: idempotency and patch scope (`azure-devops` specific)

- **The idempotency anchor MUST be a VISIBLE heading** (e.g. a `Traceability` heading). Azure **strips HTML comments on save**, so a comment sentinel (`<!-- traceability -->`) cannot anchor a re-run — it would vanish and the block would be appended again. (The platform HTML-normalization gotcha is owned by `wiki-safe-updates`.)
- **Exactly ONE block per PBI.** A re-run **locates the visible heading and replaces the block in place** — it never appends a second block.
- **Patch ONLY the work-item Description.** Acceptance criteria, State, Parent, Tags, Story Points, and Priority are left **untouched** AND **verified unchanged** by a before/after field comparison.
- **Verify a SAMPLE before bulk.** Confirm the patch is correct and business-field-preserving on a sample of PBIs before patching the full set.
- **Write governance is deferred.** Diff preview, approval, and rollback for the Description patch are owned by `wiki-safe-updates`.

## Deterministic pre-write validation

Before **any** bulk write, validate the **full generated mapping** deterministically against the source:

- every **Figma id** is verbatim-in-index (catches fabricated nodes like `1863-4852`);
- every **wiki link** is in resolvable form (the page-ID URL form owned by `wiki-structure`);
- every **spec path** is real;
- every **requirement id** is verbatim-in-index (catches plausible-looking ids no specification page defines);
- every **PBI** is mapped exactly once.

This is the gate that catches fabricated nodes and malformed paths **before** they reach live PBIs or the live wiki. On any unresolved entry, **stop and report** — never silently drop an entry and never guess a replacement.

## Safety gates

- **Never** change a PBI business field — Description-only, and verified unchanged.
- **Never** invent or guess a Figma node id — harvest from the canonical file and emit only indexed ids.
- **Never** embed, commit, or propagate a Figma `&t=` share token — omit it.
- **Never** let the matrix or a per-PBI block restate rules / acceptance criteria or mirror backlog state — navigation-only (principle owned by `wiki-source-of-truth`).
- **Never** imply full coverage when it is partial — report exact/lane/pending counts.
- **Never** emit a requirement id that is not in the harvested spec index — report the story as ungrounded instead.
- **Never** mark a story `Ready` without an exact quoted line plus its source path — fall back to the conservative class.
- **Never** take readiness from the item's existing status string — classify by the action that actually unblocks it, and never invent behaviour to clear a blocker.
- **Never** write more than one block per PBI — locate the heading and replace in place.
- **Never** use an HTML-comment sentinel as the idempotency anchor on Azure — use a visible heading.
- **Never** bulk-write before deterministic pre-write validation **and** a sample verify.
- **All** writes go through `wiki-safe-updates`' diff-preview + approval gate.

## Validation checklist

Run after any traceability pass:

- [ ] Exactly one block per PBI, anchored by a **visible heading** (no duplicate appended blocks).
- [ ] Business fields unchanged on a verified sample (AC / State / Parent / Tags / Story Points / Priority — before/after comparison).
- [ ] Every Figma id is **verbatim-in-index**, and **no `&t=` token** appears in any emitted node URL.
- [ ] Coverage `exact` / `lane` / `pending` counts **sum to the backlog size**, and partial coverage is flagged (never reported as full).
- [ ] The matrix carries the **navigation-only banner**, the **Epic -> Feature** grouping, and a **coverage column** — and **no rule text**.
- [ ] Reverse links target **parent Features**, not every child story.
- [ ] Every derived story cites a requirement id that is **verbatim-in-index**; ungrounded stories are reported, not labelled.
- [ ] Every readiness value is one of the four enum classes, and every `Ready` carries an exact quoted line + source path.
- [ ] All wiki links resolvable (defer the resolution audit to `wiki-structure` / `wiki-link-validation`).
- [ ] Deterministic pre-write validation passed (every id/link/path/PBI accounted for).

## Anti-patterns (and why)

| Anti-pattern | Why it's wrong | Correct |
|---|---|---|
| HTML-comment sentinel as the idempotency anchor on Azure | Azure strips HTML comments on save; the anchor vanishes and the block is re-appended | A visible `Traceability` heading as the anchor |
| Guessed / invented Figma node id | A fabricated id (e.g. `1863-4852`) links nowhere and ships a lie | Harvest the node index first; emit only indexed ids |
| Pasted `&t=` share token in a node URL | The token is a sensitive per-share view/tracking token, not addressing — a leak | `?node-id=<dashes>` only; omit the token |
| Matrix copies acceptance criteria / backlog state | The matrix becomes a competing second source and a stale backlog mirror | Links only; banner; rules + state stay on their owners |
| Reverse link enumerates every child story | The wiki starts mirroring the backlog | Link the parent Feature (one hop into the backlog) |
| Reporting 100% coverage with 12 screenless stories | Implies design exists where it does not | Report exact/lane/pending counts; flag pending |
| Bulk-patching 350 PBIs with no sample check | One bad mapping or field change multiplies across the backlog before anyone notices | Sample-verify, then bulk; deterministic pre-write validation first |
| Plausible-looking requirement id that no specification page defines | Passes a skim and survives review; the label dissolves exactly when someone follows it to confirm the requirement | Harvest the id index from the spec pages; emit only indexed ids, report the rest as ungrounded |
| Marking a story `Ready` because a source discusses the topic | Readiness is a go signal — the story enters a sprint and the gap surfaces mid-implementation, at the most expensive moment | Record the exact quoted line + path, or fall back to the conservative class |
| Readiness copied from the label the item already carries | The label reflects a past state, not the action that unblocks the story now | Classify by the action required, against the blocker that drives readiness |

## Cross-references

- `wiki-source-of-truth` — owns the navigation-only / no-second-source / no-backlog-leakage principle this skill **applies** (via the matrix banner); do not re-derive it here.
- `wiki-safe-updates` — owns diff preview + approval + rollback for every wiki **and** work-item write (the Description patch, the matrix page, the per-workflow tables).
- `wiki-structure` — owns the page-ID / absolute link form and the Azure adapter the matrix and reverse links rely on (consumed, not redefined, here).
- `wiki-link-validation` — owns the resolution-based validation of the links this skill emits.
- `wiki-mermaid` — owns the Azure-safe fence rules any matrix orientation map must follow.
- `wiki-authoring` — owns the business-facing shape of a derived story body (no technical nouns; technical detail fenced under `Out-of-Scope` / `Notes`; the per-Feature story cap); this skill owns only its requirement-id anchor and readiness class.
- `agent-safety-guards:agent-safety` — the hook that flags a leaked Figma share token (the enforcing complement to this skill's in-skill omission gate).
