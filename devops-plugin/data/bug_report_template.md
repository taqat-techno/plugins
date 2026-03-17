# Official Bug Report Template

**Source**: TaqaTech QA Team — Bug Reporting Framework v1.0

This template is used for:
- **Bugs** (created by QA/QC)
- **[Dev-Internal-fix] Tasks** (created by developers when Rule 8 blocks bug creation)

Both types use the same structured body format to ensure consistency and traceability.

---

## Title Format

```
[Module/Feature] - [What is broken] - [Where it happens]
```

**Examples**:
- `Beneficiary Report - Country Column Missing from Export - Admin Panel`
- `Login Module - Timeout Error on Mobile - Login Page`
- `Payment API - Wrong Currency Conversion - Checkout Flow`

---

## Body Template (Blank)

```
SEVERITY: [1-Critical | 2-High | 3-Medium | 4-Low]

REPRO STEPS:
Environment: [Production / Staging / Dev] | [Browser/Tool] | [Date tested]
Endpoint/Page: [URL or screen name]

Steps:
1. [First action]
2. [Second action]
3. [Observe the result]

Expected: [What should happen]
Actual: [What actually happens]

Evidence: [Screenshot link / Postman response / error log]

ACCEPTANCE CRITERIA:
- [ ] [Fix condition 1]
- [ ] [Fix condition 2]
- [ ] [Regression test passed]
```

---

## Severity Quick Guide

| Severity | When to Use | Examples |
|----------|-------------|---------|
| **1 - Critical** | System down, data loss, security breach | Server crash, database corruption, auth bypass |
| **2 - High** | Major feature broken, no workaround | Payment fails, login broken, data not saving |
| **3 - Medium** | Feature partially broken, workaround exists | Export missing column, filter not working |
| **4 - Low** | Cosmetic issue, typo, minor UI glitch | Alignment off, typo in label, wrong icon |

---

## Good Example

```
TITLE: Beneficiary Report - Country Column Missing from Export - Admin Panel

SEVERITY: 3 - Medium

REPRO STEPS:
Environment: Production | Chrome 120 | 2026-01-13
Endpoint/Page: Admin Panel > Reports > Beneficiary List

Steps:
1. Login as Admin
2. Navigate to Reports > Beneficiary List
3. Click "Export to Excel"
4. Open the exported file
5. Observe: Country column is not present in the export

Expected: Exported file includes a "Country" column as defined in the
          requirements document (Section 3.2 - Beneficiary Data Fields)
Actual: Export contains all columns except "Country" - the column is
        completely missing from the output

Evidence: [Screenshot of exported file showing missing column]

ACCEPTANCE CRITERIA:
- [ ] Country column appears in the Beneficiary List export
- [ ] Column displays correct country data for all beneficiary records
- [ ] Existing exports are not affected by the fix
```

---

## Poor vs Good Comparison

### POOR (avoid this)

| Field | What was written |
|-------|-----------------|
| Title | Contry Column Not add |
| Repro Steps | kindly add Country column as in requirements |
| Acceptance Criteria | N/A |

**Problems**: Typo in title, no repro steps, no environment, no expected/actual, no acceptance criteria, no evidence, sounds like a feature request.

### GOOD (use this format)

| Field | Rewritten |
|-------|-----------|
| Title | Beneficiary Report - Country Column Missing from Export - Admin Panel |
| Repro Steps | Full structured format with environment, steps, expected/actual |
| Acceptance Criteria | Checkboxes with specific, testable conditions |

---

## Agent Guidance: Gathering Bug Info

When a user wants to report a bug, gather information in this order:

1. **What module/feature?** → First part of title
2. **What's broken?** → Second part of title
3. **Where does it happen?** → Third part of title
4. **How severe?** → Show severity guide, let user pick
5. **Environment?** → Production/Staging/Dev, browser, date
6. **Steps to reproduce?** → Numbered list of actions
7. **Expected vs Actual?** → What should happen vs what does happen
8. **Evidence?** → Screenshots, logs, API responses
9. **Acceptance criteria?** → When is this fixed? (at least 1 + regression)

If the user provides partial info, fill what you can and ask for the rest.
If creating a `[Dev-Internal-fix]` Task, use the same template for the Task description.

---

*TaqaTech QA Team — Bug Reporting Framework v1.0*
*Referenced by: commands/create.md, rules/business_rules.md*
