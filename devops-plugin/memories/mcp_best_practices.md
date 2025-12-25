# Azure DevOps MCP Best Practices

> **Purpose**: This memory provides Claude with best practices for using Azure DevOps MCP tools effectively. Use these patterns for optimal user experience and reliable results.

## Quick Reference

| Domain | Key Tools | Best For |
|--------|-----------|----------|
| Work Items | `wit_*` | Interactive queries, single item ops |
| Repositories | `repo_*` | PR reviews, threads, comments |
| Pipelines | `pipelines_*` | Build status, run pipelines |
| Test Plans | `testplan_*` | Test management (MCP only) |
| Search | `search_*` | Code, wiki, work item search |
| Security | `advsec_*` | Security alerts (MCP only) |
| Wiki | `wiki_*` | Documentation |
| Core | `core_*` | Projects, teams, iterations |

---

## 1. Tool Categories

### 1.1 Work Item Tools (`wit_*`)

| Tool | Purpose | Parameters |
|------|---------|------------|
| `wit_my_work_items` | Get user's work items | project, type, includeCompleted |
| `wit_get_work_item` | Get single work item | project, id, expand |
| `wit_create_work_item` | Create work item | project, workItemType, fields |
| `wit_update_work_item` | Update work item | id, updates |
| `wit_add_child_work_items` | Create child items | parentId, project, items |
| `wit_get_work_items_batch_by_ids` | Get multiple items | project, ids, fields |
| `wit_update_work_items_batch` | Batch update | updates |
| `wit_add_work_item_comment` | Add comment | project, workItemId, comment |
| `wit_work_items_link` | Link work items | project, updates |

### 1.2 Repository Tools (`repo_*`)

| Tool | Purpose | Parameters |
|------|---------|------------|
| `repo_list_repos_by_project` | List repositories | project |
| `repo_list_pull_requests_by_repo_or_project` | List PRs | repositoryId, status |
| `repo_get_pull_request_by_id` | Get PR details | repositoryId, pullRequestId |
| `repo_create_pull_request` | Create PR | repositoryId, sourceRefName, targetRefName, title |
| `repo_update_pull_request` | Update PR | repositoryId, pullRequestId, ... |
| `repo_list_pull_request_threads` | Get PR threads | repositoryId, pullRequestId |
| `repo_create_pull_request_thread` | Create thread | repositoryId, pullRequestId, content |
| `repo_reply_to_comment` | Reply to comment | repositoryId, pullRequestId, threadId, content |
| `repo_resolve_comment` | Resolve thread | repositoryId, pullRequestId, threadId |

### 1.3 Pipeline Tools (`pipelines_*`)

| Tool | Purpose | Parameters |
|------|---------|------------|
| `pipelines_get_builds` | List builds | project, top |
| `pipelines_get_build_status` | Get build status | project, buildId |
| `pipelines_run_pipeline` | Run pipeline | project, pipelineId |
| `pipelines_get_build_log` | Get build logs | project, buildId |

### 1.4 Test Plan Tools (`testplan_*`) - MCP Only

| Tool | Purpose | Parameters |
|------|---------|------------|
| `testplan_list_test_plans` | List test plans | project |
| `testplan_create_test_plan` | Create test plan | project, name, iteration |
| `testplan_create_test_case` | Create test case | project, title, steps |
| `testplan_add_test_cases_to_suite` | Add to suite | project, planId, suiteId, testCaseIds |
| `testplan_show_test_results_from_build_id` | Get test results | project, buildid |

### 1.5 Search Tools (`search_*`) - MCP Only

| Tool | Purpose | Parameters |
|------|---------|------------|
| `search_code` | Search code | searchText, project, repository |
| `search_wiki` | Search wiki | searchText, project |
| `search_workitem` | Search work items | searchText, project, state |

### 1.6 Security Tools (`advsec_*`) - MCP Only

| Tool | Purpose | Parameters |
|------|---------|------------|
| `advsec_get_alerts` | Get security alerts | project, repository, alertType |
| `advsec_get_alert_details` | Get alert details | project, repository, alertId |

---

## 2. Common Patterns

### 2.1 Get User's Work Items

```javascript
// Get active tasks assigned to current user
mcp__azure-devops__wit_my_work_items({
    project: "Relief Center",
    type: "assignedtome",
    includeCompleted: false,
    top: 50
})
```

### 2.2 Get Work Item with Relations

```javascript
// Get work item with child items
mcp__azure-devops__wit_get_work_item({
    project: "Relief Center",
    id: 123,
    expand: "relations"
})
```

### 2.3 Create Work Item with Fields

```javascript
// Create a task with all required fields
mcp__azure-devops__wit_create_work_item({
    project: "Relief Center",
    workItemType: "Task",
    fields: [
        { name: "System.Title", value: "Implement login feature" },
        { name: "System.Description", value: "Add user authentication", format: "Html" },
        { name: "System.AssignedTo", value: "ahmed@taqatechno.com" },
        { name: "Microsoft.VSTS.Common.Priority", value: "2" }
    ]
})
```

### 2.4 Update Work Item

```javascript
// Update state and add comment
mcp__azure-devops__wit_update_work_item({
    id: 123,
    updates: [
        { path: "/fields/System.State", value: "Active" },
        { path: "/fields/System.AssignedTo", value: "mahmoud@taqatechno.com" }
    ]
})
```

### 2.5 Batch Update Work Items

```javascript
// Update multiple work items at once
mcp__azure-devops__wit_update_work_items_batch({
    updates: [
        { id: 123, path: "/fields/System.State", value: "Done" },
        { id: 124, path: "/fields/System.State", value: "Done" },
        { id: 125, path: "/fields/System.State", value: "Done" }
    ]
})
```

---

## 3. Pull Request Workflows

### 3.1 Create PR with Work Items

```javascript
// Create PR and link to work items
mcp__azure-devops__repo_create_pull_request({
    repositoryId: "my-repo-id",
    sourceRefName: "refs/heads/feature/login",
    targetRefName: "refs/heads/main",
    title: "Feature: User Login",
    description: "## Summary\n- Added login page\n- JWT authentication",
    workItems: "123 456"
})
```

### 3.2 Review PR - Get Threads

```javascript
// Get all comment threads on PR
mcp__azure-devops__repo_list_pull_request_threads({
    repositoryId: "my-repo-id",
    pullRequestId: 45
})
```

### 3.3 Add Review Comment

```javascript
// Create new comment thread on specific file
mcp__azure-devops__repo_create_pull_request_thread({
    repositoryId: "my-repo-id",
    pullRequestId: 45,
    content: "Consider using async/await here for better readability",
    filePath: "/src/auth/login.js",
    rightFileStartLine: 42,
    status: "Active"
})
```

### 3.4 Reply to Comment

```javascript
// Reply to existing thread
mcp__azure-devops__repo_reply_to_comment({
    repositoryId: "my-repo-id",
    pullRequestId: 45,
    threadId: 100,
    content: "Good point, I'll refactor this."
})
```

### 3.5 Resolve Thread

```javascript
// Mark thread as resolved
mcp__azure-devops__repo_resolve_comment({
    repositoryId: "my-repo-id",
    pullRequestId: 45,
    threadId: 100
})
```

### 3.6 Set Auto-Complete

```javascript
// Enable auto-complete with squash merge
mcp__azure-devops__repo_update_pull_request({
    repositoryId: "my-repo-id",
    pullRequestId: 45,
    autoComplete: true,
    deleteSourceBranch: true,
    mergeStrategy: "Squash"
})
```

---

## 4. Search Operations (MCP Only)

### 4.1 Search Code

```javascript
// Search for code patterns
mcp__azure-devops__search_code({
    searchText: "async function authenticate",
    project: ["Relief Center"],
    repository: ["relief-center-api"],
    top: 10
})
```

### 4.2 Search Work Items

```javascript
// Search work items by text
mcp__azure-devops__search_workitem({
    searchText: "login bug",
    project: ["Relief Center"],
    state: ["Active", "New"],
    workItemType: ["Bug"],
    top: 20
})
```

### 4.3 Search Wiki

```javascript
// Search wiki pages
mcp__azure-devops__search_wiki({
    searchText: "API documentation",
    project: ["Relief Center"],
    top: 10
})
```

---

## 5. Test Management (MCP Only)

### 5.1 Create Test Plan

```javascript
// Create test plan for sprint
mcp__azure-devops__testplan_create_test_plan({
    project: "Relief Center",
    name: "Sprint 15 Test Plan",
    iteration: "Relief Center\\Sprint 15",
    description: "Test plan for sprint 15 features"
})
```

### 5.2 Create Test Case

```javascript
// Create test case with steps
mcp__azure-devops__testplan_create_test_case({
    project: "Relief Center",
    title: "Verify user login",
    steps: "1. Navigate to login page|Login page displayed\n2. Enter valid credentials|Fields accept input\n3. Click login button|User redirected to dashboard",
    priority: 1
})
```

### 5.3 Get Test Results

```javascript
// Get test results from build
mcp__azure-devops__testplan_show_test_results_from_build_id({
    project: "Relief Center",
    buildid: 456
})
```

---

## 6. Security Alerts (MCP Only)

### 6.1 Get All Alerts

```javascript
// Get security alerts for repository
mcp__azure-devops__advsec_get_alerts({
    project: "Relief Center",
    repository: "relief-center-api",
    alertType: "Dependency",
    severities: ["High", "Critical"],
    states: ["Active"],
    confidenceLevels: ["high"]
})
```

### 6.2 Get Alert Details

```javascript
// Get specific alert details
mcp__azure-devops__advsec_get_alert_details({
    project: "Relief Center",
    repository: "relief-center-api",
    alertId: 123
})
```

---

## 7. Team and Capacity

### 7.1 Get Team Iterations

```javascript
// Get current iteration
mcp__azure-devops__work_list_team_iterations({
    project: "Relief Center",
    team: "Relief Center Team",
    timeframe: "current"
})
```

### 7.2 Get Team Capacity

```javascript
// Get team capacity for iteration
mcp__azure-devops__work_get_team_capacity({
    project: "Relief Center",
    team: "Relief Center Team",
    iterationId: "sprint-15-guid"
})
```

### 7.3 Update Team Member Capacity

```javascript
// Update capacity for team member
mcp__azure-devops__work_update_team_capacity({
    project: "Relief Center",
    team: "Relief Center Team",
    teamMemberId: "member-guid",
    iterationId: "sprint-15-guid",
    activities: [
        { name: "Development", capacityPerDay: 6 },
        { name: "Testing", capacityPerDay: 2 }
    ],
    daysOff: [
        { start: "2025-12-25", end: "2025-12-25" }
    ]
})
```

---

## 8. Best Practices

### 8.1 Use Appropriate Tools

| Scenario | Best Tool |
|----------|-----------|
| Get my tasks | `wit_my_work_items` |
| Get single item details | `wit_get_work_item` |
| Get multiple items by ID | `wit_get_work_items_batch_by_ids` |
| Query with custom filter | Use CLI `az boards query` |
| Create single item | `wit_create_work_item` |
| Create multiple child items | `wit_add_child_work_items` |
| Update single item | `wit_update_work_item` |
| Update multiple items | `wit_update_work_items_batch` |

### 8.2 Prefer Batch Operations

```javascript
// GOOD: Single batch call
mcp__azure-devops__wit_update_work_items_batch({
    updates: items.map(id => ({
        id: id,
        path: "/fields/System.State",
        value: "Done"
    }))
})

// AVOID: Multiple individual calls (unless necessary)
// items.forEach(id => wit_update_work_item(...))
```

### 8.3 Use Expand Wisely

```javascript
// Only request what you need
mcp__azure-devops__wit_get_work_item({
    project: "Relief Center",
    id: 123,
    expand: "none"  // Fastest
    // expand: "fields"  // Include all fields
    // expand: "relations"  // Include linked items
    // expand: "all"  // Everything (slowest)
})
```

### 8.4 Handle IDs Correctly

```javascript
// Repository IDs are GUIDs, not names
// WRONG:
repositoryId: "my-repo"

// CORRECT: Get ID first
const repos = await mcp__azure-devops__repo_list_repos_by_project({ project: "Relief Center" })
const repoId = repos.find(r => r.name === "my-repo").id
// Then use: repositoryId: repoId
```

### 8.5 Format Descriptions Properly

```javascript
// Use Html format for rich descriptions
mcp__azure-devops__wit_create_work_item({
    project: "Relief Center",
    workItemType: "Bug",
    fields: [
        { name: "System.Title", value: "Login fails on mobile" },
        {
            name: "System.Description",
            value: "<h3>Steps to Reproduce</h3><ol><li>Open app on mobile</li><li>Enter credentials</li><li>Click login</li></ol><h3>Expected</h3><p>User logs in</p><h3>Actual</h3><p>Error message displayed</p>",
            format: "Html"
        }
    ]
})
```

---

## 9. Error Handling

### 9.1 Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `TF401019: Work item does not exist` | Invalid work item ID | Verify ID exists |
| `TF400813: Resource not available` | Wrong project/repo name | Check spelling |
| `VS403403: Forbidden` | Insufficient permissions | Check PAT scopes |
| `TF237121: Cannot change state` | Invalid state transition | Check workflow rules |

### 9.2 Retry Pattern

When MCP calls fail:
1. Check error message
2. Verify parameters
3. If transient error, retry once
4. If permission error, check PAT token

---

## 10. Performance Tips

### 10.1 Limit Result Sets

```javascript
// Always use top parameter for large queries
mcp__azure-devops__wit_my_work_items({
    project: "Relief Center",
    top: 50  // Don't fetch all items
})
```

### 10.2 Cache Repository IDs

When working with multiple PRs in same repo:
1. Get repository ID once
2. Reuse for all subsequent calls

### 10.3 Use Parallel MCP Calls

Claude can make multiple independent MCP calls in parallel:
```javascript
// These can run in parallel
Promise.all([
    mcp__azure-devops__wit_my_work_items({ project: "Relief Center" }),
    mcp__azure-devops__pipelines_get_builds({ project: "Relief Center", top: 5 }),
    mcp__azure-devops__search_code({ searchText: "TODO", project: ["Relief Center"] })
])
```

---

## Related Memories

- `hybrid_routing.md` - When to use CLI vs MCP
- `cli_best_practices.md` - CLI patterns for batch operations
- `automation_templates.md` - Scripts combining CLI and MCP
