---
name: pm-report-writing
description: |
  PM report and document quality standards — enforces specificity, self-explanatory cells, consistent labels, and stakeholder email drafting with 3-version pattern. Use when generating status reports, proposals, email drafts, or any table-based PM deliverable.


  <example>
  Context: User asks to write a status report
  user: "Write a status report for the training program across departments"
  assistant: "I will use the pm-report-writing skill to generate a report with specific labels (platform names, phase details), consistent status markers across all rows, and self-explanatory cells."
  <commentary>Core trigger - status report generation with quality enforcement.</commentary>
  </example>

  <example>
  Context: User asks to draft an email to stakeholders
  user: "Draft an email to the managers about the project update"
  assistant: "I will use the pm-report-writing skill to provide 3 email versions (formal, concise, action-oriented) with 'Dear All' addressing, and bullet-pointed attachment descriptions."
  <commentary>Email drafting trigger - 3-version pattern with attachment listing.</commentary>
  </example>

  <example>
  Context: User asks to create a project summary table
  user: "Create a summary table of all department progress"
  assistant: "I will use the pm-report-writing skill to ensure every cell is self-explanatory, status labels are identical across rows for the same state, and no cell requires the author to explain it."
  <commentary>Table quality trigger - consistent labels and standalone cells.</commentary>
  </example>

  <example>
  Context: User asks to prepare a proposal document
  user: "Prepare a project proposal for the board"
  assistant: "I will use the pm-report-writing skill to ensure the document stands alone — every term is defined, every number has context, and the reader doesn't need the author in the room."
  <commentary>Proposal trigger - standalone document quality.</commentary>
  </example>
license: "MIT"
metadata:
  version: "1.0.0"
  priority: 80
  filePattern:
    - "**/researches/**"
    - "**/reports/**"
    - "**/deliverables/**"
    - "**/tasks/**"
    - "**/proposals/**"
  bashPattern: []
  promptSignals:
    phrases:
      - "write report"
      - "draft email"
      - "status update"
      - "prepare summary"
      - "stakeholder communication"
      - "project update"
      - "progress report"
      - "send email"
      - "board report"
    minScore: 6
---

# PM Report Writing Standards

## Core Principles

Every document you generate must pass this test: **Can the reader (CEO, Operations Manager, Engineering Manager) understand every cell, label, and status without the author in the room?**

## Rule 1: Be Specific, Not Vague

| Bad | Good |
|-----|------|
| "Core training completed" | "Udemy training completed" |
| "System configured" | "Azure DevOps board configured with 4 sprints" |
| "Meeting held" | "Kickoff meeting with 12 attendees on Mar 15" |
| "Tools set up" | "Jenkins CI/CD pipeline deployed to staging" |

Always name the platform, tool, system, or deliverable explicitly.

## Rule 2: Reports Must Stand Alone

The reader should NEVER need the author present to explain what a cell means. Before finalizing any document, read each cell and ask: "Would someone unfamiliar with this project understand this?"

If the answer is no, rewrite it with:
- Full context (not abbreviations)
- Specific quantities (not "some" or "several")
- Named deliverables (not "the document")

## Rule 3: Every Cell Self-Explanatory

For tables, EVERY cell must be independently comprehensible:
- No empty cells or `--` for completed items
- No ambiguous abbreviations without first defining them
- No cell that requires cross-referencing another cell to understand

## Rule 4: Same State = Same Label

When multiple rows/departments share the same status, use IDENTICAL wording:

| Bad | Good |
|-----|------|
| Row 1: "Phase completed" | Row 1: "Training completed" |
| Row 2: "Training done" | Row 2: "Training completed" |
| Row 3: "Finished" | Row 3: "Training completed" |

Scan all rows in the same column and enforce identical labels for identical states.

## Rule 5: No Lazy Status Labels

Never use these without specifics:

| Banned | Replacement |
|--------|-------------|
| "Ongoing" | "Phase 2: User acceptance testing (target: Apr 15)" |
| "In Progress" | "Sprint 3/6: 14 of 22 stories completed (64%)" |
| "Continues independently" | "Certification prep continues independently (lab practice & exam scheduling)" |
| "TBD" | "Phase 2: scope to be defined in Apr 5 planning session" |

Every status must show **intentional planning**, not vagueness.

## Email Drafting Standards

### Rule: Always Provide 3 Versions

When drafting emails for stakeholders, always provide:

1. **Formal** — Full detail, structured sections, suitable for board/executive audience
2. **Concise** — Professional but brief, suitable for busy managers
3. **Action-oriented** — Direct, focuses on what the reader needs to do next

### Addressing

- **Multiple managers**: Use "Dear All" — avoids hierarchy issues. Let To/CC fields handle addressing.
- **Single recipient**: Use their title + name ("Dear Dr. Ahmad")

### Attachments

NEVER just say "please find attached." Always list what the attachment contains:

```
Attached: Q1 Progress Report
- Department-level training completion status (5 departments)
- Budget utilization summary (82% of allocated)
- Risk register with 3 open items
- Next quarter timeline and milestones
```

## Quality Checklist (Run Before Finalizing)

Before completing any PM document, verify:

- [ ] Every cell is self-explanatory without the author present
- [ ] Same state uses identical wording across all rows
- [ ] No "Ongoing" / "TBD" / "In Progress" without specific next steps
- [ ] Platform/tool/system names are explicit (not generic)
- [ ] Numbers have context (not just "15" but "15 of 22 completed")
- [ ] Abbreviations defined on first use
- [ ] For emails: 3 versions provided, attachments listed with bullet points
