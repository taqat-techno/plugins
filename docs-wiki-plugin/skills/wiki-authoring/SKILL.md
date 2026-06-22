---
name: wiki-authoring
description: Content templates and authoring conventions for wiki pages — SOP, runbook, role guide, onboarding, release-and-handover, user manual, hub page, workflow doc, workflow-journey page, architecture overview, decision record, plus a recommended page set for a business/product wiki. Each template names its required sections, its audience, its last-reviewed convention, and the anti-patterns the template prevents. Activates when creating a new wiki page (via /wiki-new) or significantly restructuring an existing page.
version: 0.4.0
last_reviewed: 2026-06-22
owns:
  - page-template catalogue (SOP / runbook / role-guide / onboarding / release-handover / user-manual / hub-page / workflow / workflow-journey / architecture / decision-record)
  - hub-page template (one-line purpose + responsibilities table + optional orientation map + curated links + summary-not-source note)
  - workflow-journey-page template (actors + overview flow + one focused diagram + parity notes + authoritative-detail pointer)
  - the master-hub-vs-journey-page content distinction (master swimlane + index on the hub; focused diagrams + deferred rules on journeys)
  - recommended page-set catalogue for a business/product wiki (which template fills each page)
  - last-reviewed convention (date + reviewer; surfaced at page top)
  - audience-declaration convention (who the page is for; surfaced at page top)
  - canonical-section ordering per template
  - linkable subsection convention (anchor-friendly headings)
  - tenant/client neutralization discipline (per-hit classify-then-act; never a blind global find/replace)
defers_to:
  - wiki-structure (filename + URL slug rules; sidebar placement; IA hierarchy/tree-depth/sidebar order; Azure real-page mechanic; internal-link form)
  - wiki-mermaid (diagrams inside any page; orientation maps + focused diagrams; the master swimlane placement rule)
  - wiki-plantuml (the master swimlane artifact and its render/embed pipeline)
  - wiki-safe-updates (the workflow for writing a new page)
  - wiki-link-validation (cross-page links inside templates)
  - wiki-source-of-truth (the summary-not-source doctrine; which page is authoritative)
  - project domain expertise (the content; the skill provides shape, not substance)
user_invocable: false
---

# wiki-authoring

## Purpose

A wiki of varied authors converges on bad shapes — pages that mix topic and history, pages that bury the SOP under a brain dump, runbooks that explain context before steps. This skill ships a small catalogue of templates that match the page's purpose: an SOP looks like an SOP, a runbook reads like a runbook, an onboarding page is for new hires.

The templates are starting points. The point is consistency: a reader who has read one SOP can find their way through any other.

## When to use

Activate when:

- Creating a new wiki page (via `/wiki-new <Page-Name> --template <type>`).
- Migrating an existing wiki page into a template (e.g., the page started ad-hoc and has grown into "the SOP").
- Reviewing an inconsistent page against its template.

Skip when:

- The page is genuinely freeform (Home, Index, About). Use the lightweight conventions only (last-reviewed + audience).

## Inputs

- The page's purpose (which template).
- The page's audience.
- The page's domain content (the user provides; the skill does not invent).
- The project's last-reviewed convention (date format; reviewer attribution).

## Universal conventions (every page)

Every wiki page starts with:

```markdown
# <Page Title>

> **Audience:** <who this is for — engineers / operators / business / mixed>
> **Last reviewed:** <YYYY-MM-DD> by <name> · **Reviewed every:** <interval>

<one-paragraph summary; 2-4 sentences max>

---
```

- **Page Title** matches the basename (per `wiki-structure`).
- **Audience** is the first thing the reader sees. If the page is for them, they continue; if not, they leave knowing the page is not theirs.
- **Last reviewed** is the date someone actually read the whole page and confirmed it; not the last edit timestamp.
- **Reviewed every** sets the cadence (monthly for runbooks, quarterly for SOPs, yearly for architecture).
- **Summary** is the page's first paragraph and answers "what is this page".

After the summary, the body follows the template.

## Tenant / client neutralization

Before a page is published or shared beyond the team that owns a name, every real tenant / client / customer / product name in it must be handled — but **not** by a blind global find/replace. Each occurrence plays a different role, so each hit is classified, then acted on:

- **Active-target prose** (a tenant name in present-tense descriptive prose, incidental to a fact true of any tenant) → **neutralize** to a deterministic placeholder (`<TENANT>`, `Tenant-A`), mapping every spelling variant of the same real name to the same placeholder.
- **Legacy reference / provenance** (a name inside a quoted record, incident log, ADR-context paragraph, or an example that anchors a rule) → **preserve byte-identical**; the rule or audit trail depends on it. If exposure is a concern, escalate whether the whole record belongs in a shared wiki — do not scrub the name.
- **Operator / platform context** (the operating company, a vendor, a tool, the owning team) → **preserve**; neutralizing it would make the doc wrong.

The full classification, the determinism rules, the decision flow, and the output plan live in `references/neutralization-discipline.md`. Apply the plan through `wiki-safe-updates` diff-preview so the owner sees which lines changed and which were deliberately left intact.

## Template catalogue

### Template: SOP (Standard Operating Procedure)

**Audience:** operators, support, on-call. People who execute the procedure on a normal day.

```markdown
# <Procedure Name> SOP

> **Audience:** <e.g., on-call engineers>
> **Last reviewed:** <YYYY-MM-DD> by <name> · **Reviewed every:** quarterly

<one-paragraph summary>

---

## When to run this

<the trigger conditions — exact phrasing of what the user sees / hears before running>

## Before you start

<prerequisites — access, tools, knowledge>

## Procedure

1. <action — imperative voice>
2. <action>
3. <action — include expected outcome per step>

## How to know it worked

<verification — the specific signal that confirms success>

## If it does not work

<the most common failure modes + first response, with link to escalation>

## Escalation

<who to contact, in what order, with what context>

## Audit log

<which audit-log entries this procedure produces — for post-hoc reconstruction>

## Related

<links to: related runbooks, the architecture page, the policy page>
```

### Template: Runbook (single procedure, often emergency)

**Audience:** on-call. People who need to execute under stress.

```markdown
# <Action> Runbook

> **Audience:** on-call
> **Last reviewed:** <YYYY-MM-DD> by <name> · **Reviewed every:** monthly

<one-paragraph summary including: "when this is the right runbook">

---

## TL;DR

<the 3-5 commands the user runs if they have no time to read>

## Trigger

<exact alert text, log signal, or user complaint that brings someone here>

## Pre-flight checks

1. <quick check>
2. <quick check>

## Steps

1. <command — code block — expected output>
2. <command — code block — expected output>

## Verification

<exact command + expected output that confirms recovery>

## If steps fail

| Step | Failure | Next action |
|------|---------|-------------|
| 2 | <symptom> | <action> |
| 3 | <symptom> | <action> |

## After recovery

<post-mortem expectations, link to incident template>

## Related

<links to: related runbooks, the architecture page>
```

Runbook differences from SOP: TL;DR at top (stress reading), pre-flight checks are critical, failure table is dense.

### Template: Role guide

**Audience:** people in that role.

```markdown
# <Role Name> Guide

> **Audience:** <role>
> **Last reviewed:** <YYYY-MM-DD> by <name> · **Reviewed every:** quarterly

<one-paragraph summary of what the role does and where it fits>

---

## Responsibilities

<bullet list of what this role owns; what they decide; what they do not>

## Permissions

<what the role can do in each system; link to permission matrix>

## Day-to-day

<a typical week: what tasks recur, which other roles they collaborate with>

## Tools

<accounts, dashboards, CLI tools the role uses; how to get access>

## Common scenarios

<3-5 recurring situations with the right action for each>

## Escalation paths

<who to ask when stuck, in what order>

## Onboarding into this role

<link to onboarding page; checklist of first-30-days items>

## Related

<links to: adjacent role guides, the SOPs this role runs>
```

### Template: Onboarding

**Audience:** new hires (engineer, operator, manager — pick one per page).

```markdown
# <Role> Onboarding

> **Audience:** new <role>
> **Last reviewed:** <YYYY-MM-DD> by <name> · **Reviewed every:** quarterly

<one-paragraph summary: what you will be able to do at the end of this page>

---

## Week 1 — Access + orientation

- [ ] Get access to <system>
- [ ] Read <link to role guide>
- [ ] Shadow <person>
- [ ] Run <first-day-no-stakes task>

## Week 2 — First independent work

- [ ] <task>
- [ ] <task>

## Week 3 — Production responsibility

- [ ] <task>

## Reference

- <link to role guide>
- <link to SOPs you will run>
- <link to runbooks you will need>
- <link to architecture overview>

## People

| Role | Person | When to ask |
|------|--------|-------------|
| <role> | <name> | <topic> |
```

### Template: Release and handover

**Audience:** the team taking over (could be the same team after a release; could be a different team after a handover).

```markdown
# <Release / Project> — Release & Handover

> **Audience:** <team taking over>
> **Last reviewed:** <YYYY-MM-DD> by <name>

<one-paragraph summary: what shipped, what was handed over, when>

---

## What shipped

<feature list with links to each feature's doc>

## What is in scope going forward

<who owns what after this handover>

## Known issues at handover

| Issue | Severity | Mitigation | Tracker |
|-------|----------|------------|---------|
| <issue> | <H/M/L> | <workaround> | <link> |

## Open questions

<things the team-taking-over should investigate>

## Operational artifacts

- Dashboards: <links>
- Alerts: <links>
- Runbooks: <links>
- SOPs: <links>

## Contacts during transition

<who to call for the first N weeks if something breaks>
```

### Template: User manual

**Audience:** end users (could be internal users of a tool, or external customers).

```markdown
# <Product / Feature> — User Manual

> **Audience:** <end-user role>
> **Last reviewed:** <YYYY-MM-DD> by <name>

<one-paragraph summary of what the product / feature does>

---

## Quick start

<3 steps from zero to first success>

## How to <common task 1>

<step by step with screenshots; one screenshot per step max>

## How to <common task 2>

...

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| <symptom> | <cause> | <action> |

## FAQ

**Q: <common question>**
A: <answer with link if longer than 2 sentences>

## Glossary

<terms specific to this product>

## Getting help

<how to escalate within the product OR contact support>
```

### Template: Hub page

**Audience:** anyone navigating into a section — they need orientation, not the rules themselves.

A hub is a section landing page. On Azure DevOps wikis a parent IS a real page (not a folder), so a section that exists must have a real landing page (the why and the IA mechanic are owned by `wiki-structure`). The hub's job is to orient and route, never to carry the rules its children own.

```markdown
# <Section Name>

> **Audience:** <who navigates here>
> **Last reviewed:** <YYYY-MM-DD> by <name> · **Reviewed every:** quarterly

<one-line purpose of this section>

---

## What is in here / who should read it

| Child page | What it covers | Who should read it |
|------------|----------------|--------------------|
| <child page link> | <one line> | <role> |

## Orientation map

<optional — a compact Mermaid map at hub altitude only (a few nodes), NEVER a full state machine; see wiki-mermaid>

## In this section

- <curated link to each child page>
- <curated link to the matching workflow-journey page(s)>

---

> This hub summarises; the authoritative rules live on the child pages. (The "summary, not source" doctrine is owned by `wiki-source-of-truth`.)
```

Three hard rules:

- A hub is **never** blank.
- A hub is **never** a bare link list — it carries the purpose, the responsibilities table, and the curated links.
- A hub **never** restates a child's rule body — it points to the child.

Keep internal links in the adapter's form (the link syntax is owned by `wiki-structure`).

### Template: Workflow doc

> **For a multi-workflow wiki where rules live on separate spec pages,** use the **Workflow-journey page** template (below) for each per-workflow child and read **"Workflow hub vs journey pages"** — so authors do not put rule bodies on journey pages. The "Workflow doc" template below is for a single self-contained process.

**Audience:** anyone in the workflow.

```markdown
# <Workflow Name>

> **Audience:** all participants
> **Last reviewed:** <YYYY-MM-DD> by <name>

<one-paragraph summary of the workflow and its outcome>

---

## Overview

<diagram of the workflow — use wiki-mermaid TD flowchart; if the workflow crosses multiple actor lanes, use a wiki-plantuml swimlane instead>

> **Diagram order on a workflow page:** a single-actor process flow → `wiki-mermaid` `flowchart TD`; a multi-actor handoff (who does what across lanes) → `wiki-plantuml` swimlane; a request/response exchange → `wiki-mermaid` `sequenceDiagram`; an explicit lifecycle → `wiki-mermaid` `stateDiagram-v2`. Mermaid renders inline; a swimlane is a pre-rendered image (see `wiki-plantuml`).

## Participants

| Role | Responsibility |
|------|----------------|
| <role> | <what they do> |

## Steps

1. **<step name>** — <role> does <action>. Output: <artifact>. Time: <typical duration>.
2. **<step name>** — ...

## Hand-offs

<what gets passed between roles at each step boundary>

## Variants

<known variants on this workflow and when to use each>

## Related

<links to SOPs for individual steps>
```

### Template: Workflow-journey page

**Audience:** anyone tracing one end-to-end journey through the system.

A journey page is a **child of a master workflow hub**. It traces one journey at journey altitude and **defers every rule** to its owning specification page. This is distinct from the "Workflow doc" above: a **Workflow doc** is a single self-contained multi-party process; a **Workflow-journey page** is one of many children under a master workflow hub, and the rules live on a separate spec page. Cross-link the two when a wiki uses both shapes.

```markdown
# <Journey Name>

> **Audience:** anyone tracing this journey
> **Last reviewed:** <YYYY-MM-DD> by <name>

<one-paragraph summary of the journey and its outcome>

> Part of <master workflow hub link>.

---

## Actors

<the actors in this journey and what each contributes>

## Overview flow

1. <ordered/numbered step at journey altitude — actor does action, hands off to next>
2. <step>

## Diagram

<ONE focused diagram for this journey — NOT the master swimlane; see wiki-mermaid for a focused diagram or wiki-plantuml for a single focused swimlane>

## Parity notes

<where the as-built behaviour differs from the documented intent>

---

> **Authoritative detail:** <link to the owning specification page>
```

**Refusal rule:** a journey page DEFERS every rule to its owning specification page. It **must not** emit a rule body, a contract, a state machine, or an event list — it references them through the "Authoritative detail" pointer. If the journey seems to need a rule, link to the spec page that owns it.

### Template: Architecture overview

**Audience:** engineers (existing + new + cross-team).

```markdown
# <System> Architecture

> **Audience:** engineers
> **Last reviewed:** <YYYY-MM-DD> by <name> · **Reviewed every:** yearly (or after major change)

<one-paragraph summary: what the system does at the architectural level>

---

## High-level diagram

<wiki-mermaid LR flowchart with subgraphs by tier>

## Components

| Component | Responsibility | Runtime | Owner |
|-----------|---------------|---------|-------|
| <name> | <one-line> | <how it runs> | <team / person> |

## Data flow

<wiki-mermaid sequenceDiagram for the primary user flow>

## Persistence

<databases, caches, queues; consistency assumptions>

## External integrations

<third-party services with role + criticality + failure-mode>

## Non-functional

<scale, latency, availability, security posture — link to specifics>

## Source of truth for...

<which behaviour is documented here vs in code; see wiki-code-vs-docs-discrepancy>

## Decision records

<links to ADRs that explain why this shape>
```

### Template: Decision record (ADR)

**Audience:** future maintainers wondering "why".

```markdown
# ADR-<NN> — <Title>

> **Status:** <proposed | accepted | superseded by ADR-MM>
> **Date:** <YYYY-MM-DD>
> **Authors:** <names>

## Context

<what problem is this decision solving; what constraints were in play>

## Options considered

### Option 1 — <name>

Pros:
Cons:

### Option 2 — <name>

Pros:
Cons:

## Decision

<the option chosen, in one paragraph>

## Consequences

Positive:
Negative:

## When to revisit

<conditions that would invalidate this decision>
```

ADRs are short, immutable once accepted, and live in a dedicated `decisions/` namespace inside the wiki (where the wiki flavour supports it) OR with the `ADR-NN-` prefix on flat-namespace wikis.

## Workflow hub vs journey pages

When a wiki documents many workflows, split them into a **master workflow hub** plus per-workflow **journey pages** (the journey-page template above). The two carry different content:

- **Master workflow hub** — holds the SINGLE master end-to-end swimlane (the one diagram covering the full lifecycle across all actor lanes) exactly once, and an index table mapping each workflow to its journey page and its authoritative specification page.

  | Workflow | Journey page | Authoritative spec page |
  |----------|--------------|-------------------------|
  | <name> | <journey page link> | <spec page link> |

  The master swimlane lives on the hub only — never duplicated onto children (the swimlane placement rule is owned by `wiki-mermaid`; rendering/embedding the swimlane artifact is owned by `wiki-plantuml` / `wiki-mermaid`).

- **Child journey pages** — focused diagrams only; they defer every rule to the spec page, carry the "Authoritative detail: <spec page>" pointer, and carry a "Part of <hub>" backlink.

Single-source rules:

- The master swimlane appears on the hub only.
- Rule statements are single-sourced on the spec pages and only *referenced* from journeys — never restated.
- Prefer **moving** an existing strong workflow page under the hub over re-creating a near-duplicate.

## Recommended page set for a business/product wiki

Catalogue-level guidance on which TEMPLATE fills each page (this is not a hierarchy spec — the tree nesting, sidebar/`.order`, depth, move/rename/repoint mechanics, and the section-label choice are owned by `wiki-structure` and `wiki-source-of-truth`). The exact section set is adapted per project.

| Page role | Template to use |
|-----------|-----------------|
| Product-Specification landing | Hub page (the top of the business tree) |
| Each themed section | Hub page |
| Workflows-Overview master hub | Hub page carrying the master swimlane + workflow index (see "Workflow hub vs journey pages") |
| Each per-workflow page | Workflow-journey page (defers rules to its spec page) |
| Technical-Reference | Architecture overview |
| Development-SOPs index | Hub page; each SOP under it uses the SOP template |

Defer the actual tree nesting, sidebar ordering, depth, and the "Business-Source-of-Truth vs Product-Specification" label choice to `wiki-structure` (IA) and `wiki-source-of-truth` (which page is authoritative).

## Decision framework

When the user invokes `/wiki-new` without a template, ask:

```
What kind of page is this?
  1. SOP (procedure operators follow)
  2. Runbook (emergency response steps)
  3. Role guide (what someone in role X does)
  4. Onboarding (first weeks in role X)
  5. Release / handover (what shipped, who owns now)
  6. User manual (how to use a product)
  7. Hub page (section landing / orientation)
  8. Workflow doc (single self-contained multi-party process)
  9. Workflow-journey page (child of a workflow hub that defers rules to a spec page)
  10. Architecture overview (engineering reference)
  11. Decision record (why we chose X)
  Or: freeform (no template)
```

Disambiguator: pick **Workflow doc** for one self-contained process; pick **Workflow-journey page** when the workflow is one of many under a master hub and its rules live on a separate specification page.

Default to "freeform" only when the page genuinely does not fit a template (Home, Index, About).

## Safety gates

- **Never** auto-populate the page body with placeholder content the user did not provide. The template is structure; the user supplies substance.
- **Never** assume "Last reviewed" is today's date. Either ask the user or leave a placeholder.
- **Never** include real PII / customer identifiers / secrets in template examples (the templates above use placeholders intentionally).
- **Never** neutralize tenant/client names with a blind global find/replace — classify each hit first (active prose → neutralize; provenance → preserve byte-identical; operator/platform → preserve). See `references/neutralization-discipline.md`.
- **Never** prescribe a wiki page when a code-side comment / commit message / PR description is the right place.
- **Never** lock a page into one template after creation — pages evolve; allow the maintainer to restructure.
- **Never** emit a blank or link-only hub — a hub carries purpose + responsibilities table + curated links + the "summary, not source" note.
- **Never** restate a child's authoritative rule body on a hub or journey page — point to the owning page.
- **Never** place the master swimlane on a child journey page — it lives on the master workflow hub only.
- **Never** let a journey page emit a rule / contract / state-machine / event body — use an "Authoritative detail: <spec page>" pointer.

## Validation checklist

Before saving a new page:

- [ ] Audience declared at top.
- [ ] Last-reviewed line present (date may be placeholder).
- [ ] One-paragraph summary present.
- [ ] Template's required sections present (even if empty placeholders).
- [ ] Diagrams (if any) follow `wiki-mermaid` rules.
- [ ] Internal links follow `wiki-structure` convention.
- [ ] Filename matches the page title per `wiki-structure`.
- [ ] Any real tenant/client name was classified per `references/neutralization-discipline.md` (no blind global replace); provenance lines preserved byte-identical.
- [ ] (Hub) non-empty — purpose + responsibilities table + curated links + "summary, not source" note.
- [ ] (Hub) every child is reachable from the hub and backlinks to it.
- [ ] (Journey) linked from the master workflow hub index and carries the "Authoritative detail: <spec page>" pointer.
- [ ] (Workflow set) the master swimlane appears exactly once (on the hub).
- [ ] No rule body / contract / state machine / event list on any hub or journey page.

## Output format

For `/wiki-new`:

```
PROPOSED NEW PAGE — <path>
  Template: <type>
  Audience (provided): <role>
  Last-reviewed placeholder: YYYY-MM-DD by <name>
  Sections scaffolded: <list>
  Diagrams placeholder: <count>
  Cross-references to other pages: <count> (verified existing | <N> point to TBD)
  Apply (via wiki-safe-updates)? [yes / no / edit]
```

## Anti-patterns (and why)

| Anti-pattern | Why it's wrong | Correct |
|---|---|---|
| 1000-word SOP with context before the procedure | Operator scrolls past context to reach steps | Steps first; context after |
| Runbook with the verification command at the bottom | Operator runs steps and does not know it worked | TL;DR at top; verification near top |
| Role guide that lists every permission down to the byte | Permissions are a code-side fact; document at the right level | Link to permission matrix; describe in role terms |
| Onboarding page with no first-week-no-stakes task | New hire has nothing to do on day 1 | Concrete week-1 task |
| Architecture page maintained as a draw.io export only | Mermaid source missing; rot inevitable | Mermaid in the page |
| ADR rewritten after being accepted | Future readers cannot tell what changed and why | New ADR supersedes old |
| User manual that screenshots every screen | Screenshots go stale fast; multiply edits | Screenshot the few that need pixel-level guidance |
| FAQ as a dumping ground for things nobody actually asks | Wastes reader attention | Only real questions; each linked to where the answer lives in detail |
| `sed s/AcmeCorp/<TENANT>/g` over the whole page to "anonymize" it | Corrupts provenance lines and rule-anchoring examples; changes what the page asserts | Classify each name hit; neutralize active prose, preserve provenance + platform context |
| Hub page that is a bare list of child links | Orients no one; a parent is a real page, not a folder | Purpose + responsibilities table + curated links + "summary, not source" note |
| Hub that copies a child's rule body so readers "don't have to click" | Creates a competing second source; drifts from the child | Summarise and link; the child owns the rule |
| Journey page that restates the spec's contract / state machine | Duplicates the authoritative rules; goes stale silently | Defer via the "Authoritative detail: <spec page>" pointer |
| Master swimlane duplicated onto each journey page | Multiple copies drift; the hub stops being the single map | Master swimlane on the hub only; focused diagrams on journeys |

## Portability rationale

Templates are content shape, not platform behavior. They render identically on GitHub Wiki, GitLab, Azure DevOps, MkDocs.

The skill does not depend on:

- A specific markdown extension set
- A specific table renderer
- A specific diagram tool (beyond `wiki-mermaid`)

## Cross-references

- `wiki-structure` — filename rules; sidebar placement; IA hierarchy and tree-depth; the Azure real-page mechanic; the internal-link form for hub and journey links.
- `wiki-source-of-truth` — owns the "summary, not source" doctrine that hubs and journey pages cite; which page is authoritative.
- `wiki-mermaid` — diagrams inside any template (flowchart/sequence/state, rendered inline); orientation maps and focused diagrams; the master-swimlane placement rule. Already cross-referenced.
- `wiki-plantuml` — BPMN-style swimlanes for multi-actor workflow pages (pre-rendered image); owns the master swimlane artifact and its render/embed pipeline. Already cross-referenced.
- `wiki-safe-updates` — workflow for the actual write.
- `wiki-link-validation` — verifies cross-references in templates.
- `wiki-code-vs-docs-discrepancy` — applied if the page makes a claim contradicted by code.
- `references/neutralization-discipline.md` — per-hit classification for tenant/client names (neutralize / preserve-provenance / preserve-platform).
- `wiki-source-of-truth` — pairs with neutralization: current-state pages neutralize active prose; provenance / decision records preserve the named event.
- `/wiki-new` (command) — invokes this skill.
