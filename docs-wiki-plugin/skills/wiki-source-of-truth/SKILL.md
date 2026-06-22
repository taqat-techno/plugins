---
name: wiki-source-of-truth
description: Owns the source-of-truth doctrine for a project's knowledge — the declared order in which artifacts win, the target-vs-current-state separation (including wiki-ahead-of-code / zero-commit-repo detection), the cross-system planning-vs-code/wiki host split, the single-location rule for config constants, and stale-checkbox distrust. Activates when onboarding a project from its docs and wiki, when auditing whether documentation still matches reality, or when two artifacts disagree and someone must decide which one is authoritative. Resolves conflicts with evidence rather than guessing, and routes per-claim verification to wiki-code-vs-docs-discrepancy.
version: 0.3.0
last_reviewed: 2026-06-22
owns:
  - the declared knowledge-layer ORDER (which artifact wins for "what the system does now")
  - the TARGET/aspirational vs CURRENT-STATE doc separation rule (folder + label)
  - the wiki-ahead-of-code detection signal (a zero-commit / empty repo means a fully-described stack is TARGET, not current)
  - the cross-system source-of-truth split (planning platform vs the host that actually owns code + wiki; empty decoy repos)
  - the single-source-of-truth-location rule for security/config constants
  - stale-checkbox distrust (doc checkboxes and percent-complete are never ground truth for scope)
  - the conflict-resolution decision (doc-fix vs queued-code-change) framing
  - the SOURCE-OF-TRUTH DECLARATION output block and the discrepancy-line format
  - the provenance-preservation rule (a named decision's anchoring record is preserved, not neutralized) feeding tenant/client neutralization
defers_to:
  - wiki-code-vs-docs-discrepancy (the per-claim code-vs-docs check that gathers the evidence)
  - wiki-structure (where pages live and how the wiki tree is shaped)
  - wiki-vs-stray-docs (deciding whether a loose doc belongs in the wiki at all)
  - the project's version-control history and dated reports (the evidence this skill cross-checks against)
user_invocable: false
---

# wiki-source-of-truth

## Purpose

A project's knowledge lives in many artifacts — live code, config, a wiki, current-state docs, forward-looking design docs, READMEs, and inline skills. They drift apart. When two of them disagree, an answer is only as trustworthy as the rule that decided which one to believe. This skill owns that rule: an explicit, project-declared ORDER of authority, plus the doctrine that keeps onboarding from trusting an aspirational handbook as present reality.

## When to use

Activate when:

- Onboarding a new contributor (or yourself) onto a project primarily from its docs and wiki.
- Auditing whether the documentation still matches what the code actually does.
- Two artifacts disagree on a fact and someone must decide which one is authoritative.
- A doc states a security or config constant (token lifetime, rate limit, threshold) and you must know whether to trust it.
- A doc checkbox or "80% complete" line is being used to claim scope is done.

Do NOT use this skill to perform the per-claim code-vs-docs comparison itself — that is owned by `wiki-code-vs-docs-discrepancy`. This skill decides *which way a confirmed conflict resolves* and *which layer is canonical*.

## Inputs (adapter)

Every project-specific value is a NAMED input. Nothing below is hardcoded by the skill.

1. **`layer_order`** — the project's declared ranking of knowledge layers from most to least authoritative for "what the system does now." If the project has not declared one, propose the default below and ask for confirmation before relying on it.
2. **`current_state_location`** — folder(s) / page prefix that hold CURRENT-STATE docs (describe the system as it is).
3. **`target_location`** — folder(s) / page prefix that hold TARGET/aspirational docs (describe a future or intended system).
4. **`target_label`** — the explicit label or banner a doc carries to mark itself aspirational (e.g. a front-matter flag or a heading tag). The skill checks for it; the project defines its exact text.
5. **`config_constant_locations`** — the single code/config location(s) that own each security/config constant (where the real value lives). One entry per constant class.
6. **`history_source`** — the version-control log / commit history used to cross-check scope claims.
7. **`reports_source`** — dated status reports / changelogs used alongside history to verify "is this done."

Default `layer_order` (illustrative — not required; the project supplies the real one):

```
1. live code + runtime config   ← wins for "what the system does NOW"
2. wiki (current-state pages)
3. other current-state docs
4. target / aspirational docs    ← describes intent, NOT present reality
5. inline skills / READMEs
```

## Read-only investigation steps

Do not edit anything during investigation. Gather, then report.

1. **Confirm the declared order.** Read `layer_order`. If absent, surface the default and mark every downstream conclusion as provisional until the project confirms.
2. **Classify each doc as CURRENT-STATE or TARGET.** Use `current_state_location` / `target_location` (folder) and `target_label` (in-doc marker). A doc that is forward-looking but sits in the current-state location, or lacks `target_label`, is a finding — not a fact to trust.
3. **Locate each config constant's owner.** For every constant mentioned in docs, find its real value via `config_constant_locations`. Note any doc literal that diverges from the code value.
4. **Distrust checkboxes.** For any scope claim resting on a checkbox or percent-complete, cross-check `history_source` + `reports_source`. A checked box with no corresponding commit/report is unverified.
5. **Collect, don't decide silently.** For each conflict found, defer the per-claim evidence-gathering to `wiki-code-vs-docs-discrepancy`, then bring the evidence back here for the resolution decision.

## Decision framework

### Conflict resolution: doc vs code

Code wins for "what the system does now." The *fix*, therefore, is usually to the doc — unless a code change is already queued that will make the doc true.

| Situation | Authoritative now | Recommended fix |
|---|---|---|
| Doc describes behavior; code differs; no code change queued | Code | Fix the **doc** to match code |
| Doc describes behavior; code differs; matching code change **is queued** | Doc (forward) | Leave doc; flag that code is mid-change; link the queued change |
| Doc states a config constant; code value differs | Code (`config_constant_locations`) | Fix the **doc** literal; point it at the owning location |
| Two docs disagree, no code touches the topic | Higher layer in `layer_order` | Reconcile the lower-layer doc to the higher one |
| Behavior is undocumented entirely | Code | Add a current-state doc; do NOT invent intent |

Rule of thumb:

```
conflict found
   ├─ is a code change queued that makes the doc true?
   │      ├─ yes → doc is forward; flag code-in-progress, link the change
   │      └─ no  → code is truth NOW → fix the DOC
   └─ never edit code to match a doc unless that code change is explicitly queued
```

### Current-state vs target classification

| Signal | Classify as | Trust for present reality? |
|---|---|---|
| Lives in `current_state_location`, carries no `target_label` | CURRENT-STATE | Yes (still subject to code check) |
| Carries `target_label` (regardless of folder) | TARGET | No — intent only |
| Lives in `target_location` | TARGET | No — intent only |
| Forward-looking content but in `current_state_location` and no label | MISFILED — finding | No — flag for relabel/move |
| Describes a fully-implemented stack, but the repo it describes has **zero commits / is empty** | WIKI-AHEAD-OF-CODE — TARGET in effect | No — the document is the design, not the build |

When a doc is misfiled, the recommended fix is to add `target_label` and/or move it to `target_location` — never to delete the content and never to treat it as present reality in the meantime.

**Wiki-ahead-of-code signal.** A Technical-Reference (or any current-state-located page) that reads as fully built, paired with a repo that has **zero commits**, is the strongest tell that the page is aspirational regardless of where it sits or whether it carries `target_label`: there is no code for it to be current *about*. Classify it as TARGET in effect and recommend the `target_label` even if the author intended it as current-state — the empty repo, not the folder, settles it. Verify the emptiness against `history_source` (no commits) before applying this signal; do not infer "empty" from a failed clone or a wrong repo path. (Repo-population confirmation itself is owned by `wiki-code-vs-docs-discrepancy`.)

### Cross-system source-of-truth split

A project's knowledge layers do not have to live on one host. A common split: one platform is used for **planning only** (e.g. work items / boards on Azure DevOps), while the actual **code and wiki** live on a different host (e.g. `github.com/<org>/<Product>` plus its `/wiki`). The planning platform's own Git repo is then frequently an **empty decoy** — it exists because the platform created it, but nothing was ever pushed there.

The split itself is a **governance finding**, not just a routing detail: if `layer_order` names "the repo" without saying *which* host owns code, every downstream audit risks pointing at the decoy and concluding the project is empty when it is merely hosted elsewhere.

| Symptom | Reading | Action |
|---|---|---|
| Work items live on platform P; no code ever lands there | P is the **planning** layer only | Record P as planning-only in `layer_order`; do not treat its repo as the code authority |
| Platform P's repo has zero commits / no default branch, but a different host has the populated repo + wiki | P's repo is a **decoy**; the other host owns code + wiki | Point all "audit the repo" work at the populated host; flag the decoy so no one re-audits it |
| `layer_order` says "the code" without naming a host, and two hosts exist | ambiguous authority | Surface as a finding; make `layer_order` name the host that actually owns code before resolving any conflict |

The rule: **identify which host owns code and which owns the wiki before resolving any code-vs-doc conflict; point repo audits at the populated host, never the planning system's decoy.** Confirming a given repo is the populated one (vs an empty placeholder) is owned by `wiki-code-vs-docs-discrepancy`; this skill only records the split into `layer_order` and treats it as a governance finding.

### Tenant/client neutralization vs provenance

When a doc is being generalized or shared and contains a real tenant / client / customer name, the source-of-truth layer decides whether the name is incidental or load-bearing — and that decision drives whether it may be neutralized:

| Where the name sits | Source-of-truth role | Neutralization decision |
|---|---|---|
| Current-state prose describing present behavior | incidental to a present-tense fact | NEUTRALIZE to a deterministic placeholder (active-target prose) |
| A decision record / ADR-context / incident log that anchors a named decision | the **evidence** the decision rests on | PRESERVE byte-identical — the named event is provenance |
| Operator / platform / vendor / team context | the context the operator needs | PRESERVE |

The rule: **a named decision's anchoring record is provenance, not active prose.** Neutralizing it would make the decision unverifiable and could turn a true historical statement into a false generic one. Never run a blind global find/replace across a page that mixes current-state prose with provenance. Hand the per-hit classification to `references/neutralization-discipline.md` (owned alongside `wiki-authoring`); this skill only supplies the current-state-vs-provenance judgement it depends on. If a name hit's neutralization would change a config constant or a named decision's meaning, it is no longer cosmetic — route it through the conflict-resolution path above, not a scrub.

## Safety gates

- **Never** silently pick a side on a conflict — always present the evidence and the recommended fix, and let the owner confirm.
- **Never** edit code to make it match a doc unless that exact code change is already explicitly queued.
- **Never** treat a TARGET/aspirational doc as a description of present behavior.
- **Never** treat a fully-described stack as current when the repo it describes has zero commits — that is wiki-ahead-of-code; the page is TARGET in effect.
- **Never** record "the code" in `layer_order` without naming which host owns it when a planning platform and a separate code/wiki host both exist; never point a repo audit at the planning platform's (often empty decoy) repo.
- **Never** trust a doc literal for a security/config constant over the value in `config_constant_locations`.
- **Never** accept a checkbox or percent-complete as proof that scope is done without cross-checking `history_source` + `reports_source`.
- **Never** invent intent for undocumented behavior — document what the code does, not what it "probably" means.
- **Never** print secret values, tokens, or env contents while locating a config constant — reference the location, not the secret.
- **Never** neutralize a tenant/client name inside a decision record / ADR-context / incident log — that record is provenance for a named decision; preserve it byte-identical.

## Validation checklist

- [ ] `layer_order` is declared (or the default was proposed and explicitly confirmed).
- [ ] Every doc reviewed is classified CURRENT-STATE or TARGET, by folder and by `target_label`.
- [ ] No TARGET doc was trusted as present reality; any fully-described page over a zero-commit repo was flagged wiki-ahead-of-code.
- [ ] If a planning platform and a separate code/wiki host both exist, `layer_order` names which host owns code; no repo audit was pointed at the planning platform's decoy repo.
- [ ] Every config constant cited in docs was checked against `config_constant_locations`; divergences are flagged.
- [ ] No scope conclusion rests on a checkbox alone; each was cross-checked against `history_source` + `reports_source`.
- [ ] Each conflict carries evidence and a recommended fix — none was resolved silently.
- [ ] No code was edited to match a doc unless the change was explicitly queued.
- [ ] No secret value was printed during investigation.
- [ ] If any tenant/client name was neutralized, current-state prose was classified separately from provenance records; no anchoring record was scrubbed.

## Output format

The skill emits a SOURCE-OF-TRUTH DECLARATION block, then one discrepancy line per conflict.

```
SOURCE-OF-TRUTH DECLARATION
  layer_order:
    1. <layer>   ← truth for "what the system does now"
    2. <layer>
    3. <layer>
    ...
  current_state_location: <path/prefix>
  target_location:        <path/prefix>   (label: <target_label>)
  config_constants:
    <constant-name> → owner: <config_constant_locations entry>

DISCREPANCIES
  [<id>] <artifact-A> vs <artifact-B>
        claim:    <what each says>
        evidence: <from wiki-code-vs-docs-discrepancy / history / reports>
        truth:    <which layer wins, per layer_order>
        fix:      DOC-FIX <where> | CODE-CHANGE-QUEUED <link> | RELABEL-TARGET <where>
        status:   AWAITING-OWNER-CONFIRMATION
```

Discrepancy line (single-line form, when a compact list is preferred):

```
[<id>] <topic> | doc says <X> | code says <Y> | truth=CODE | fix=DOC-FIX@<path> | confirm?
```

## Anti-patterns

| Anti-pattern | Why it is wrong | Correct |
|---|---|---|
| Trusting a forward-looking handbook as present reality | Onboards people onto a system that does not exist yet | Classify TARGET vs CURRENT-STATE; trust only current-state + code |
| Reading a fully-built-sounding Technical-Reference as current when the repo has zero commits | There is no code for it to be current about; it is the design, not the build | Treat as wiki-ahead-of-code → TARGET in effect; recommend `target_label` |
| Auditing "the repo" on the planning platform when code + wiki actually live on another host | Audits an empty decoy and falsely concludes the project is empty | Record the planning-vs-code/wiki split in `layer_order`; audit the populated host |
| No declared `layer_order`; deciding ad hoc per conflict | Different conflicts resolve inconsistently; no audit trail | Declare the order once; resolve every conflict against it |
| Copying a config constant's value into prose and treating prose as canonical | Two sources for one constant drift; the doc goes stale silently | One owner per constant in `config_constant_locations`; docs point to it |
| Reading a checked box as "this is done" | Checkboxes are edited by hand and lie | Cross-check `history_source` + `reports_source` before claiming scope |
| Editing code so it matches an out-of-date doc | Changes behavior to satisfy stale text; reverses the authority order | Fix the doc; only touch code when that change is explicitly queued |
| Silently picking code-or-doc and moving on | Owner never sees the conflict or the decision | Present evidence + recommended fix; await confirmation |
| Treating undocumented behavior as a bug to "fix" toward an imagined spec | Invents intent the project never stated | Document what the code does; flag the gap, don't guess intent |
| Global find/replace of a client name across a page that includes a decision record | Scrubs the provenance a named decision rests on; makes it unverifiable | Neutralize current-state prose only; preserve the anchoring record byte-identical |

## Portability rationale

The doctrine is project-agnostic. The skill depends only on named adapter inputs — `layer_order`, the two doc locations and their label, the config-constant owners, and the history/reports sources. It assumes no particular language, framework, wiki engine, version-control system, or company. Any project that can state "here is the order in which our artifacts win, and here is where each config constant really lives" can use it unchanged; nothing in the skill's behavior depends on a specific product, domain term, path, or URL.

## Cross-references

- `wiki-code-vs-docs-discrepancy` — performs the per-claim code-vs-docs comparison and supplies the evidence this skill resolves on.
- `wiki-structure` — owns where pages live and the shape of the wiki tree (informs `current_state_location` / `target_location`).
- `wiki-vs-stray-docs` — decides whether a loose document belongs in the wiki at all before it can be classified here.
- `wiki-safe-updates` — applies the DOC-FIX once a conflict's resolution is confirmed; also owns the safe-doc-deletion gate, whose capture-check relies on this skill's "is this decision genuinely captured" judgement.
- `wiki-authoring` › `references/neutralization-discipline.md` — the per-hit tenant/client classification this skill's current-state-vs-provenance judgement feeds into.
