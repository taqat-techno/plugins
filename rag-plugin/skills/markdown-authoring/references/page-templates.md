# Page templates

Five Markdown templates tuned for the ragtools chunker. Each template produces 3–6 clean heading-anchored chunks. Every section sits in the sweet spot of 150–250 words so the whole section becomes one chunk within the 256-token embedding window.

Source: `references/rag-md-guidelines.md` §4.

## Concept page

Use for: READMEs, "what is X" pages, domain-concept explainers, glossary entries.

```markdown
# <Concept name>

## What it is

<1 paragraph, 80–120 words. Ends with a single definition sentence that names the concept precisely.>

## Why it exists

<1 paragraph, 80–120 words. What problem does it solve? What was broken before this existed?>

## Key rules

<Bulleted invariants. Each bullet a complete sentence. Rules that future authors or operators must honor.>

## Related concepts

<Links to sibling pages. Use descriptive anchor text — the link text goes into a chunk, so it carries semantic weight.>
```

Produces 3–4 tight, heading-anchored chunks. Good retrieval on queries like "what is X" / "why does X exist" / "rules for X".

## SOP page (walkthrough)

Use for: step-by-step procedures, deploy guides, configuration walkthroughs, installation procedures.

```markdown
# SOP: <action>

## Purpose

<1 paragraph — what this procedure accomplishes. Not "the deploy process" but "how to deploy a new version of service X to staging".>

## Preconditions

<Bulleted checklist — what must be true before starting.>

## Step 1 — <verb + noun>

<Prose explaining what to do and why. Code block if needed (under 60 lines).>

## Step 2 — <verb + noun>

<Same pattern.>

## Step 3 — <verb + noun>

<Same pattern.>

## Validation

<How to confirm it worked. Specific checks — "curl /health returns 200" not "the service is running".>

## Failure modes

<Table or bulleted list of known failures + links to runbooks.>
```

Every step becomes its own chunk under a named leaf heading. Query "how do I do step 2 of SOP X?" lands on Step 2 directly.

## Reference page

Use for: API references, config-key reference, field lists, error-code catalogs.

```markdown
# <Area> reference

## <Table 1 — categorical slice, ≤ 10 rows>

<Short intro sentence explaining what the table covers.>

| Field | Type | Description |
|---|---|---|
| ... |

## <Table 2 — another categorical slice, ≤ 10 rows>

<Short intro sentence.>

| Field | Type | Description |
|---|---|---|
| ... |
```

Each `##` holds one short table → one chunk per table. Never dump a 50-row table under one heading — it becomes one paragraph to the splitter and gets shredded.

## Runbook / troubleshooting page

Use for: incident response, known-failure playbooks, "X is broken, what do I do" pages.

```markdown
# Runbook: <symptom>

## Symptom

<1 paragraph — user-visible evidence. What the operator sees that triggered them to open this runbook.>

## Likely causes

<Bulleted list of possible root causes, each with one-sentence explanation.>

## Diagnosis

### Check <X>

<How to confirm or rule out cause A. Code block if needed.>

### Check <Y>

<How to confirm or rule out cause B.>

## Recovery

### If <cause A>

<Steps to recover. Typed-confirmation gates on anything destructive.>

### If <cause B>

<Steps to recover.>

## Prevention

<1 paragraph — how to avoid the symptom in the future.>
```

Each diagnostic check and each recovery branch becomes its own `###` chunk. Query "how do I diagnose cause A" lands directly on that sub-section.

## Architecture page

Use for: component design docs, system overviews, decision records collections.

```markdown
# <Component> architecture

## What it is

<1 paragraph — the component's role in one sentence plus context.>

## How it fits in the system

<1 paragraph — upstream callers, downstream dependencies, data flow.>

## Key decisions

### Decision — <name>

<Rationale for a load-bearing choice. What were the alternatives, why this one.>

### Decision — <name>

<Same pattern.>

## Failure modes

<Known ways this component breaks. Link to runbooks.>

## Code paths

<Key file:line references for future maintainers.>
```

Decisions become independent chunks, each retrievable by name. Query "decision about X" lands on the right decision directly.

## General notes on applying the templates

- **Adapt, don't copy blindly.** The templates are shapes, not mandates. If your content genuinely needs a different structure, use it — just keep the 8 hard rules.
- **Unused sections are OK.** If a page genuinely has no preconditions, drop the `## Preconditions` section rather than write "None". Empty sections still become chunks and dilute retrieval.
- **File naming matters.** Use kebab-case filenames that match the topic: `service-configuration.md`, not `Service Configuration.md` or `serviceConfiguration.md`. Consistent paths survive renames and make citations legible.
- **Reserved section names across pages.** When multiple pages use the same vocabulary (`## Purpose`, `## Preconditions`, `## Validation`, `## Failure modes`, `## Related`), retrieval becomes predictable — the same prompt can hit the same named heading across files.

## See also

- `rag-md-guidelines.md` §4 — the canonical page-template source this file is derived from
- `rag-md-guidelines.md` §6 — unified knowledge-base standard (file naming, reserved sections, terminology dictionary)
- `anti-patterns.md` — what to avoid when filling in the templates
