---
name: pm-consolidation
description: |
  Multi-source analysis consolidation — conflict tracking with numbered IDs, color-coded source attribution, 3-tier gap classification, and governance-first recommendations. Use when merging multiple independent analyses into a consolidated output. Requires Opus for judgment-heavy conflict identification.


  <example>
  Context: User has two analysis reports to merge
  user: "Consolidate the S1 and S2 analysis files into a unified report"
  assistant: "I will use the pm-consolidation skill to build an independent HUB output with numbered conflicts (CF-01..CF-N), color-coded source attribution, and gap classifications — without modifying the source files."
  <commentary>Core trigger - multi-source consolidation project.</commentary>
  </example>

  <example>
  Context: User asks about conflicting findings
  user: "S1 says 200 tables but S2 says 185 — which is right?"
  assistant: "I will use the pm-consolidation skill to track this as a numbered conflict (CF-XX), show both positions side-by-side, and present it for governance decision — not auto-resolve it."
  <commentary>Conflict trigger - present both sides neutrally for governance.</commentary>
  </example>

  <example>
  Context: User wants to classify gaps
  user: "Categorize all the gaps found across the analyses"
  assistant: "I will use the pm-consolidation skill to classify each gap as Blocking (must fix before go-live), Important (should fix soon), or Deferrable (nice to have), with rationale for each classification."
  <commentary>Gap classification trigger - 3-tier severity classification.</commentary>
  </example>

  <example>
  Context: User wants to apply a recommendation
  user: "Apply the recommendation from Section 4 to the source analysis"
  assistant: "I will NOT modify the source analysis. Recommendations stay as recommendations until governance approves. I'll add it to the HUB output's recommendation section instead."
  <commentary>Governance guard trigger - never auto-apply recommendations to source files.</commentary>
  </example>
license: "MIT"
metadata:
  version: "1.0.0"
  priority: 55
  model: opus
  filePattern:
    - "**/*consolidat*"
    - "**/*hub*"
    - "**/S1/**"
    - "**/S2/**"
    - "**/*merged*"
  bashPattern: []
  promptSignals:
    phrases:
      - "consolidate analyses"
      - "merge sources"
      - "conflict tracking"
      - "gap classification"
      - "multi-source"
      - "HUB output"
      - "source attribution"
      - "governance"
    minScore: 6
---

# PM Consolidation Standards

## Rule 39: NEVER Modify Source Files

This is absolute. In consolidation projects:

- **Source analyses** (S1, S2, etc.) are READ-ONLY
- Keep all source analyses untouched (e.g., S1: 468 files, S2: 21 files)
- Build an **independent consolidated output** (HUB v3.0)
- This preserves original analysis integrity for audit trails

If you need to reference a source finding, quote it — don't edit it.

### Directory Structure

```
project/
├── S1/                    # Source Analysis 1 (READ-ONLY)
│   ├── analysis.html
│   └── data/
├── S2/                    # Source Analysis 2 (READ-ONLY)
│   ├── analysis.html
│   └── data/
├── HUB/                   # Consolidated Output (WRITE HERE)
│   ├── hub_v3.0.html
│   ├── conflicts/
│   ├── gaps/
│   └── recommendations/
└── .pm-protected-paths    # Protects S1/, S2/ from edits
```

## Rule 40: Track Conflicts with Numbered IDs

Number every conflict for traceability:

### Conflict Format

```html
<div class="conflict" id="CF-01">
    <h4>CF-01: Database Object Count Discrepancy</h4>
    <div class="source-s1">
        <span class="badge bg-primary">S1</span>
        <p>Total database objects: 468 (including views, triggers, functions)</p>
    </div>
    <div class="source-s2">
        <span class="badge bg-warning">S2</span>
        <p>Total database objects: 421 (tables and views only, excluding functions)</p>
    </div>
    <div class="resolution-status">
        <span class="badge bg-secondary">Pending Governance Decision</span>
        <p><strong>Root cause:</strong> Different scope definitions for "database object"</p>
        <p><strong>Impact:</strong> Migration effort estimate varies by ~11%</p>
    </div>
</div>
```

### Conflict Registry Table

| ID | Topic | S1 Position | S2 Position | Impact | Status |
|----|-------|-------------|-------------|--------|--------|
| CF-01 | DB object count | 468 | 421 | Migration scope | Pending |
| CF-02 | Module dependencies | 12 circular | 8 circular | Build order | Pending |
| CF-03 | API versioning | v1 deprecated | v1 still active | Breaking changes | Pending |

Show **both positions without auto-resolution**. Let governance decide.

## Rule 41: Color-Coded Source Attribution

Every data point must be traceable to its origin:

| Color | Source | CSS Class | Badge |
|-------|--------|-----------|-------|
| Blue | S1 (primary analysis) | `.source-s1` | `bg-primary` |
| Orange | S2 (secondary analysis) | `.source-s2` | `bg-warning` |
| Purple | Merged (agreed by both) | `.source-merged` | `bg-purple` |
| Green | New (discovered during consolidation) | `.source-new` | `bg-success` |

### CSS Implementation

```css
.source-s1 { border-left: 4px solid #0d6efd; background: #e8f0fe; padding: 8px 12px; }
.source-s2 { border-left: 4px solid #fd7e14; background: #fff3e0; padding: 8px 12px; }
.source-merged { border-left: 4px solid #6f42c1; background: #f3e8ff; padding: 8px 12px; }
.source-new { border-left: 4px solid #198754; background: #e8f5e9; padding: 8px 12px; }
```

Readers can trace ANY claim to its origin by color alone.

## Rule 42: 3-Tier Gap Classification

Classify every gap found during consolidation:

### Tier Definitions

| Tier | Label | Criteria | Action Required |
|------|-------|----------|----------------|
| **1** | **Blocking** | Cannot proceed to next phase without resolving | Immediate governance decision |
| **2** | **Important** | Should be resolved before go-live | Schedule in upcoming sprint |
| **3** | **Deferrable** | Nice to have, no operational impact | Add to backlog |

### Gap Format

```html
<div class="gap gap-blocking" id="GAP-01">
    <span class="badge bg-danger">BLOCKING</span>
    <h5>GAP-01: No disaster recovery procedure documented</h5>
    <p><strong>Source:</strong> <span class="badge bg-primary">S1</span> identified, <span class="badge bg-warning">S2</span> did not assess</p>
    <p><strong>Impact:</strong> Compliance requirement — cannot deploy without DR plan</p>
    <p><strong>Recommendation:</strong> Commission DR assessment before Phase 2</p>
</div>
```

### Why 3 Tiers?

Simple enough to prevent analysis paralysis. More than 3 tiers (Critical/High/Medium/Low/Cosmetic) leads to endless debates about whether something is "Medium" or "High". Three tiers force clear decisions:
- Can we proceed? → **Blocking**
- Should we fix soon? → **Important**
- Can it wait? → **Deferrable**

## Rule 48: Recommendations Stay as Recommendations

**NEVER auto-apply analysis recommendations to source files.**

The workflow is:
1. Technical teams **provide analysis** (findings, gaps, conflicts)
2. Analysis team **presents recommendations** (in the HUB output)
3. Governance board **decides** which recommendations to implement
4. Implementation team **applies** approved recommendations

You are step 2. You present. You do not decide or apply.

### Recommendation Format

```html
<div class="recommendation" id="REC-01">
    <h5>REC-01: Standardize Database Object Counting Methodology</h5>
    <p><strong>Based on:</strong> CF-01 (DB object count discrepancy)</p>
    <p><strong>Proposal:</strong> Adopt S1 methodology (include views, triggers, functions) as the standard</p>
    <p><strong>Rationale:</strong> More comprehensive scope reduces risk of missing migration items</p>
    <p><strong>Effort:</strong> 2 person-days to recount using standardized methodology</p>
    <span class="badge bg-info">Awaiting Governance Approval</span>
</div>
```

## Consolidation Checklist

Before delivering any consolidated output:

- [ ] Source files (S1, S2) remain completely unmodified
- [ ] `.pm-protected-paths` created to prevent accidental edits
- [ ] All conflicts numbered (CF-01..CF-N) with both positions shown
- [ ] Color-coded source attribution on every data point
- [ ] Gaps classified as Blocking / Important / Deferrable
- [ ] Recommendations presented neutrally (not auto-applied)
- [ ] Conflict registry table with all conflicts summarized
- [ ] HUB output is self-contained and independent of source files
