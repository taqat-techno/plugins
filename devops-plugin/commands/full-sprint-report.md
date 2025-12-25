---
title: 'Full Sprint Report'
read_only: true
type: 'command'
description: 'Generate comprehensive sprint report using HYBRID CLI + MCP approach. Combines CLI speed for data gathering with MCP richness for details and test results.'
---

# Full Sprint Report

Generate a comprehensive sprint report using **both CLI and MCP** for optimal data gathering. This command demonstrates hybrid mode - using CLI for fast bulk queries and MCP for rich details.

## Usage

```
/full-sprint-report [project] [team]
/full-sprint-report "Relief Center" "Relief Center Team"
```

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `project` | No | From config | Project name |
| `team` | No | Default team | Team name |

---

## Report Sections

The full sprint report includes:

1. **Sprint Overview** - Name, dates, progress
2. **Work Item Summary** - By state and type
3. **Team Velocity** - Story points completed
4. **Bug Analysis** - Open bugs, severity breakdown
5. **Build Health** - Recent build status
6. **Test Results** - Test pass rate
7. **PR Status** - Open and merged PRs
8. **Risks & Blockers** - Items needing attention
9. **Next Steps** - Recommendations

---

## Execution Flow (Hybrid)

Claude will execute these steps using both CLI and MCP:

### Step 1: Get Current Iteration (CLI)

```bash
# Fast CLI query for iteration details
az boards iteration team list \
    --project "Relief Center" \
    --team "Relief Center Team" \
    --timeframe current \
    --output json
```

**Returns:** Iteration name, path, start/end dates

---

### Step 2: Query Sprint Work Items (CLI)

```bash
# Bulk query via CLI is faster for large item counts
az boards query --wiql "
SELECT [System.Id], [System.Title], [System.State],
       [System.WorkItemType], [System.AssignedTo],
       [Microsoft.VSTS.Scheduling.StoryPoints]
FROM WorkItems
WHERE [System.IterationPath] = '$ITERATION_PATH'
  AND [System.TeamProject] = 'Relief Center'
" --output json
```

**Returns:** All work items with key fields

---

### Step 3: Get Work Item Details (MCP)

```javascript
// MCP for rich details on specific items
mcp__azure-devops__wit_get_work_items_batch_by_ids({
    project: "Relief Center",
    ids: [/* item IDs from step 2 */],
    fields: ["System.Title", "System.State", "System.Description"]
})
```

**Returns:** Full work item details including description

---

### Step 4: Get Team Capacity (MCP)

```javascript
// MCP-only feature
mcp__azure-devops__work_get_team_capacity({
    project: "Relief Center",
    team: "Relief Center Team",
    iterationId: "iteration-guid"
})
```

**Returns:** Team member capacities and days off

---

### Step 5: Get Recent Builds (CLI)

```bash
# CLI for build history
az pipelines runs list \
    --project "Relief Center" \
    --top 10 \
    --output json
```

**Returns:** Last 10 builds with status

---

### Step 6: Get Test Results (MCP)

```javascript
// MCP-only feature for test results
mcp__azure-devops__testplan_show_test_results_from_build_id({
    project: "Relief Center",
    buildid: lastBuildId
})
```

**Returns:** Test execution results from latest build

---

### Step 7: Get Active PRs (MCP)

```javascript
// MCP for PR details with threads
mcp__azure-devops__repo_list_pull_requests_by_repo_or_project({
    project: "Relief Center",
    status: "Active"
})
```

**Returns:** Open PRs with review status

---

### Step 8: Get Security Alerts (MCP)

```javascript
// MCP-only feature
mcp__azure-devops__advsec_get_alerts({
    project: "Relief Center",
    repository: "main-repo",
    states: ["Active"],
    severities: ["High", "Critical"],
    confidenceLevels: ["high"]
})
```

**Returns:** Active security vulnerabilities

---

## Sample Report Output

```markdown
# Sprint Report: Sprint 15

**Project:** Relief Center
**Team:** Relief Center Team
**Period:** Dec 15 - Dec 28, 2025
**Generated:** Dec 25, 2025

---

## Sprint Overview

| Metric | Value |
|--------|-------|
| Total Items | 25 |
| Completed | 18 (72%) |
| In Progress | 5 |
| Blocked | 2 |

### Progress Bar
[████████████████████░░░░░░░░] 72%

---

## Work Item Summary

### By State

| State | Count | % |
|-------|-------|---|
| Done | 18 | 72% |
| Active | 3 | 12% |
| In Progress | 2 | 8% |
| Blocked | 2 | 8% |

### By Type

| Type | Total | Done | Remaining |
|------|-------|------|-----------|
| User Story | 5 | 4 | 1 |
| Task | 15 | 12 | 3 |
| Bug | 5 | 2 | 3 |

---

## Team Velocity

| Metric | Value |
|--------|-------|
| Story Points Planned | 34 |
| Story Points Completed | 26 |
| Velocity | 76% |

### Team Contribution

| Team Member | Points | Items |
|-------------|--------|-------|
| Ahmed | 10 | 5 |
| Mahmoud | 8 | 4 |
| Eslam | 8 | 6 |

---

## Bug Analysis

| Severity | Open | Closed | Total |
|----------|------|--------|-------|
| Critical (1) | 1 | 0 | 1 |
| High (2) | 2 | 1 | 3 |
| Medium (3) | 0 | 1 | 1 |

### Critical Bugs (Require Immediate Attention)

1. **[Bug #456]** Login fails on mobile devices
   - Priority: 1 - Critical
   - Assigned: Ahmed
   - State: Active

---

## Build Health

### Last 10 Builds

| Result | Count |
|--------|-------|
| Succeeded | 8 |
| Failed | 2 |
| Success Rate | 80% |

### Recent Failures

| Build | Date | Reason |
|-------|------|--------|
| #234 | Dec 24 | Test failure in AuthTests |
| #230 | Dec 22 | Compilation error |

---

## Test Results

**Latest Build:** #235 (Dec 25, 2025)

| Metric | Value |
|--------|-------|
| Total Tests | 156 |
| Passed | 148 |
| Failed | 5 |
| Skipped | 3 |
| Pass Rate | 94.9% |

### Failed Tests

1. `AuthTests.LoginWithSpecialChars` - AssertionError
2. `APITests.TimeoutHandling` - Timeout exceeded
3. `UITests.MobileResponsive` - Element not found

---

## Pull Request Status

### Active PRs

| PR | Title | Author | Reviewers | Status |
|----|-------|--------|-----------|--------|
| #45 | Feature: User Dashboard | Ahmed | Mahmoud, Eslam | Waiting review |
| #44 | Fix: Login validation | Eslam | Ahmed | Approved |

### Merged This Sprint

- 12 PRs merged
- Average review time: 18 hours

---

## Security Alerts

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High | 2 |
| Medium | 5 |

### High Severity Alerts

1. **CVE-2025-1234** - Dependency vulnerability in `lodash`
   - Fix: Update to version 4.17.21

---

## Risks & Blockers

### Blocked Items

1. **[Task #789]** Deploy to production
   - Blocker: Waiting for security approval
   - Days blocked: 3

2. **[Task #790]** API integration
   - Blocker: Third-party API downtime
   - Days blocked: 1

### Risks

1. **Critical bug not resolved** - May impact release
2. **2 failing tests** - Need investigation
3. **Security vulnerabilities** - Should be patched

---

## Recommendations

### Immediate Actions

1. ⚠️ Fix critical bug #456 before sprint end
2. ⚠️ Investigate and fix failing tests
3. ⚠️ Update vulnerable dependencies

### For Next Sprint

1. Plan capacity for bug fixes
2. Include security patching tasks
3. Review blocked items with stakeholders

---

## Summary

| Category | Status |
|----------|--------|
| Progress | 🟡 On Track (72%) |
| Quality | 🟡 Needs Attention |
| Build Health | 🟢 Good (80%) |
| Test Coverage | 🟢 Good (95%) |
| Security | 🟡 Review Needed |

**Overall Sprint Health:** 🟡 Yellow - Minor issues to address

---

*Report generated by Claude Code with Azure DevOps Plugin v2.0*
*Using hybrid CLI + MCP approach*
```

---

## Why Hybrid Approach?

| Data Source | Tool Used | Reason |
|-------------|-----------|--------|
| Iteration details | CLI | Fast, simple query |
| Bulk work items | CLI | Faster for large datasets |
| Work item details | MCP | Rich field access |
| Team capacity | MCP | MCP-only feature |
| Build history | CLI | Fast listing |
| Test results | MCP | MCP-only feature |
| PR details | MCP | Thread/comment access |
| Security alerts | MCP | MCP-only feature |

---

## Customization

### Filter by Work Item Type

```
/full-sprint-report --type "Bug"
```

### Include Specific Sections Only

```
/full-sprint-report --sections "progress,bugs,tests"
```

### Export to File

```
/full-sprint-report --output sprint15-report.md
```

---

## Related Commands

- `/sprint` - Quick sprint summary (MCP only)
- `/standup` - Daily standup notes
- `/build-status` - Build health check
- `/my-tasks` - Personal task list
