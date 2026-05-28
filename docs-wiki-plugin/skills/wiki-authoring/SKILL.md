---
name: wiki-authoring
description: Content templates and authoring conventions for wiki pages — SOP, runbook, role guide, onboarding, release-and-handover, user manual, workflow doc, architecture overview, decision record. Each template names its required sections, its audience, its last-reviewed convention, and the anti-patterns the template prevents. Activates when creating a new wiki page (via /wiki-new) or significantly restructuring an existing page.
version: 0.2.0
last_reviewed: 2026-05-28
owns:
  - page-template catalogue (SOP / runbook / role-guide / onboarding / release-handover / user-manual / workflow / architecture / decision-record)
  - last-reviewed convention (date + reviewer; surfaced at page top)
  - audience-declaration convention (who the page is for; surfaced at page top)
  - canonical-section ordering per template
  - linkable subsection convention (anchor-friendly headings)
defers_to:
  - wiki-structure (filename + URL slug rules; sidebar placement)
  - wiki-mermaid (diagrams inside any page)
  - wiki-safe-updates (the workflow for writing a new page)
  - wiki-link-validation (cross-page links inside templates)
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

### Template: Workflow doc

**Audience:** anyone in the workflow.

```markdown
# <Workflow Name>

> **Audience:** all participants
> **Last reviewed:** <YYYY-MM-DD> by <name>

<one-paragraph summary of the workflow and its outcome>

---

## Overview

<diagram of the workflow — use wiki-mermaid TD flowchart>

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
  7. Workflow doc (multi-party process)
  8. Architecture overview (engineering reference)
  9. Decision record (why we chose X)
  Or: freeform (no template)
```

Default to "freeform" only when the page genuinely does not fit a template (Home, Index, About).

## Safety gates

- **Never** auto-populate the page body with placeholder content the user did not provide. The template is structure; the user supplies substance.
- **Never** assume "Last reviewed" is today's date. Either ask the user or leave a placeholder.
- **Never** include real PII / customer identifiers / secrets in template examples (the templates above use placeholders intentionally).
- **Never** prescribe a wiki page when a code-side comment / commit message / PR description is the right place.
- **Never** lock a page into one template after creation — pages evolve; allow the maintainer to restructure.

## Validation checklist

Before saving a new page:

- [ ] Audience declared at top.
- [ ] Last-reviewed line present (date may be placeholder).
- [ ] One-paragraph summary present.
- [ ] Template's required sections present (even if empty placeholders).
- [ ] Diagrams (if any) follow `wiki-mermaid` rules.
- [ ] Internal links follow `wiki-structure` convention.
- [ ] Filename matches the page title per `wiki-structure`.

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

## Portability rationale

Templates are content shape, not platform behavior. They render identically on GitHub Wiki, GitLab, Azure DevOps, MkDocs.

The skill does not depend on:

- A specific markdown extension set
- A specific table renderer
- A specific diagram tool (beyond `wiki-mermaid`)

## Cross-references

- `wiki-structure` — filename rules; sidebar placement.
- `wiki-mermaid` — diagrams inside any template.
- `wiki-safe-updates` — workflow for the actual write.
- `wiki-link-validation` — verifies cross-references in templates.
- `wiki-code-vs-docs-discrepancy` — applied if the page makes a claim contradicted by code.
- `/wiki-new` (command) — invokes this skill.
