---
name: devops
description: "Azure DevOps integration skill for TaqaTechno organization. Manages work items, pull requests, pipelines, repositories, wiki, test plans, and security alerts through the official Microsoft Azure DevOps MCP server. Use when user asks about: tasks, bugs, PRs, builds, sprints, standups, code reviews, deployments, or any Azure DevOps operations."
version: "1.0.0"
author: "TAQAT Techno"
license: "MIT"
allowed-tools:
  - Read
  - Write
  - Bash
  - WebFetch
metadata:
  organization: "TaqaTechno"
  mcp-server: "@azure-devops/mcp"
  tools-count: "100+"
  domains: "core,work,work-items,repositories,pipelines,test-plans,wiki,search,advanced-security"
---

# Azure DevOps Integration Skill

A comprehensive skill for managing Azure DevOps resources through natural language, powered by the official Microsoft Azure DevOps MCP server.

## Configuration

- **Organization**: TaqaTechno
- **MCP Server**: `@azure-devops/mcp` (Official Microsoft)
- **Authentication**: Personal Access Token (PAT)
- **Tools Available**: 100+ across 10 domains

## When to Use This Skill

Activate this skill when user requests:
- Work item operations (create, update, query bugs/tasks/stories)
- Pull request management (create, review, merge PRs)
- Pipeline/build operations (run, monitor, debug builds)
- Sprint/iteration management (summaries, planning, standups)
- Repository browsing (branches, commits, file content)
- Wiki documentation (read, create, update pages)
- Code/work item search
- Test plan management
- Security alert monitoring

## Tool Reference by Domain

### Core Domain (3 tools)
Always use these first to establish context.

| Tool | Description | Example Use |
|------|-------------|-------------|
| `mcp_ado_core_list_projects` | List all projects | "Show all projects" |
| `mcp_ado_core_list_project_teams` | Get teams in project | "List teams in ProjectX" |
| `mcp_ado_core_get_identity_ids` | Look up user identities | "Find user Ahmed" |

### Work Items Domain (24 tools)
Most commonly used for task management.

| Tool | Description | Example Use |
|------|-------------|-------------|
| `mcp_ado_workitems_get_workitem` | Get work item by ID | "Show task #1234" |
| `mcp_ado_workitems_list_workitems` | List with filters | "Show all bugs" |
| `mcp_ado_workitems_create_workitem` | Create new item | "Create bug: Login fails" |
| `mcp_ado_workitems_update_workitem` | Update existing | "Update #1234 to Done" |
| `mcp_ado_workitems_delete_workitem` | Delete item | "Delete task #1234" |
| `mcp_ado_workitems_query_workitems` | Run WIQL query | "My active items" |
| `mcp_ado_workitems_link_workitems` | Link items together | "Link #123 to #456" |
| `mcp_ado_workitems_add_comment` | Add comment | "Comment on #1234" |
| `mcp_ado_workitems_get_comments` | Get comments | "Show comments on #1234" |

### Work Domain (7 tools)
For sprint and iteration management.

| Tool | Description | Example Use |
|------|-------------|-------------|
| `mcp_ado_work_get_iterations` | List iterations | "Show all sprints" |
| `mcp_ado_work_get_current_iteration` | Current sprint | "Current sprint info" |
| `mcp_ado_work_get_team_capacity` | Team capacity | "Team capacity this sprint" |
| `mcp_ado_work_get_backlog_items` | Backlog items | "Show backlog" |

### Repositories Domain (19 tools)
For code and PR management.

| Tool | Description | Example Use |
|------|-------------|-------------|
| `mcp_ado_repos_list_repositories` | List repos | "Show all repos" |
| `mcp_ado_repos_get_repository` | Repo details | "Info on MyRepo" |
| `mcp_ado_repos_list_branches` | List branches | "Branches in MyRepo" |
| `mcp_ado_repos_get_commits` | Commit history | "Recent commits" |
| `mcp_ado_repos_get_file_content` | Read file | "Show README.md" |
| `mcp_ado_repos_create_pull_request` | Create PR | "Create PR to main" |
| `mcp_ado_repos_get_pull_request` | PR details | "Show PR #45" |
| `mcp_ado_repos_list_pull_requests` | List PRs | "Open PRs" |
| `mcp_ado_repos_update_pull_request` | Update PR | "Update PR title" |
| `mcp_ado_repos_add_pr_comment` | Comment on PR | "Add review comment" |
| `mcp_ado_repos_complete_pull_request` | Merge PR | "Merge PR #45" |

### Pipelines Domain (13 tools)
For CI/CD operations.

| Tool | Description | Example Use |
|------|-------------|-------------|
| `mcp_ado_pipelines_list_pipelines` | List pipelines | "Show all pipelines" |
| `mcp_ado_pipelines_get_pipeline` | Pipeline details | "Info on CI-Main" |
| `mcp_ado_pipelines_run_pipeline` | Run pipeline | "Run CI pipeline" |
| `mcp_ado_pipelines_list_builds` | List builds | "Recent builds" |
| `mcp_ado_pipelines_get_build` | Build details | "Build #789 info" |
| `mcp_ado_pipelines_get_build_logs` | Build logs | "Logs for #789" |
| `mcp_ado_pipelines_get_build_changes` | Build changes | "Changes in #789" |
| `mcp_ado_pipelines_cancel_build` | Cancel build | "Cancel build #789" |

### Test Plans Domain (11 tools)
For test management.

| Tool | Description | Example Use |
|------|-------------|-------------|
| `mcp_ado_testplan_list_test_plans` | List plans | "Show test plans" |
| `mcp_ado_testplan_create_test_plan` | Create plan | "Create test plan" |
| `mcp_ado_testplan_list_test_cases` | List cases | "Test cases in plan" |
| `mcp_ado_testplan_create_test_case` | Create case | "Create test case" |
| `mcp_ado_testplan_get_test_results` | Test results | "Results for sprint" |

### Wiki Domain (6 tools)
For documentation.

| Tool | Description | Example Use |
|------|-------------|-------------|
| `mcp_ado_wiki_list_wikis` | List wikis | "Show all wikis" |
| `mcp_ado_wiki_get_page` | Get page | "Show API docs page" |
| `mcp_ado_wiki_create_page` | Create page | "Create new wiki page" |
| `mcp_ado_wiki_update_page` | Update page | "Update installation docs" |

### Search Domain (3 tools)
For finding content.

| Tool | Description | Example Use |
|------|-------------|-------------|
| `mcp_ado_search_code` | Search code | "Find 'authenticate'" |
| `mcp_ado_search_wiki` | Search wiki | "Search for deployment" |
| `mcp_ado_search_workitem` | Search items | "Find login bugs" |

### Advanced Security Domain (2 tools)
For security monitoring.

| Tool | Description | Example Use |
|------|-------------|-------------|
| `mcp_ado_advsec_get_alerts` | Security alerts | "Show security alerts" |
| `mcp_ado_advsec_get_alert_details` | Alert details | "Details on alert #1" |

## Common Workflows

### 1. Daily Standup Preparation

```
Workflow:
1. Query my active work items
2. Identify completed items (yesterday)
3. Identify in-progress items (today)
4. Check for blockers
5. Summarize in standup format
```

**WIQL Query:**
```sql
SELECT [System.Id], [System.Title], [System.State], [System.AssignedTo]
FROM WorkItems
WHERE [System.AssignedTo] = @Me
  AND [System.State] <> 'Closed'
  AND [System.State] <> 'Removed'
ORDER BY [Microsoft.VSTS.Common.Priority]
```

**Output Format:**
```
## Daily Standup - [Date]

### Yesterday
- Completed task #1234: Fix login bug
- Reviewed PR #45

### Today
- Working on task #1235: Add validation
- Code review for PR #46

### Blockers
- None / Waiting for API access
```

### 2. Sprint Summary

```
Workflow:
1. Get current iteration info
2. Query all sprint work items
3. Calculate progress (completed vs total)
4. Identify at-risk items
5. Generate summary report
```

**WIQL Query:**
```sql
SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType]
FROM WorkItems
WHERE [System.IterationPath] UNDER @CurrentIteration
ORDER BY [System.WorkItemType], [System.State]
```

### 3. Pull Request Review

```
Workflow:
1. Get PR details
2. Get linked work items
3. Review code changes
4. Add review comments
5. Approve or request changes
```

### 4. Build Failure Investigation

```
Workflow:
1. Get failed build details
2. Get build logs
3. Identify error patterns
4. Suggest fixes
5. Link to work item if needed
```

### 5. Bug Creation

```
Workflow:
1. Create bug work item with:
   - Title (clear, descriptive)
   - Description (what happened)
   - Repro Steps (how to reproduce)
   - Expected vs Actual behavior
   - Severity (1-4)
   - Priority (1-4)
2. Link to related items
3. Assign to appropriate developer
```

## WIQL Query Templates

### My Active Work Items
```sql
SELECT [System.Id], [System.Title], [System.State]
FROM WorkItems
WHERE [System.AssignedTo] = @Me
  AND [System.State] <> 'Closed'
  AND [System.State] <> 'Removed'
ORDER BY [Microsoft.VSTS.Common.Priority]
```

### Bugs in Current Sprint
```sql
SELECT [System.Id], [System.Title], [System.State], [Microsoft.VSTS.Common.Severity]
FROM WorkItems
WHERE [System.WorkItemType] = 'Bug'
  AND [System.IterationPath] UNDER @CurrentIteration
ORDER BY [Microsoft.VSTS.Common.Severity]
```

### Recently Updated Items
```sql
SELECT [System.Id], [System.Title], [System.ChangedDate], [System.ChangedBy]
FROM WorkItems
WHERE [System.ChangedDate] >= @Today - 7
ORDER BY [System.ChangedDate] DESC
```

### Unassigned Items
```sql
SELECT [System.Id], [System.Title], [System.WorkItemType]
FROM WorkItems
WHERE [System.AssignedTo] = ''
  AND [System.State] = 'New'
ORDER BY [System.CreatedDate] DESC
```

### Items by Tag
```sql
SELECT [System.Id], [System.Title]
FROM WorkItems
WHERE [System.Tags] CONTAINS 'urgent'
  AND [System.State] <> 'Closed'
```

### High Priority Items
```sql
SELECT [System.Id], [System.Title], [System.State]
FROM WorkItems
WHERE [Microsoft.VSTS.Common.Priority] <= 2
  AND [System.State] <> 'Closed'
ORDER BY [Microsoft.VSTS.Common.Priority]
```

## Work Item Types

| Type | Use For | Key Fields |
|------|---------|------------|
| **Epic** | Large initiatives | Title, Description, Business Value |
| **Feature** | Functional areas | Title, Description, Target Date |
| **User Story** | User requirements | Title, Description, Acceptance Criteria |
| **Task** | Technical work | Title, Description, Remaining Work |
| **Bug** | Defects | Title, Repro Steps, Severity, Priority |
| **Issue** | Blockers | Title, Description, Resolution |
| **Test Case** | Test scenarios | Title, Steps, Expected Results |

## Response Formatting

When presenting Azure DevOps data, use consistent formatting:

### Work Items
```
[Bug] #1234: Fix login button not responding
   State: Active | Priority: 2 | Severity: 2
   Assigned: Ahmed | Sprint: Sprint 15
```

### Pull Requests
```
PR #45: Add user authentication
   Author: Ahmed | Status: Active
   Reviewers: 2/3 approved | Comments: 5
   Linked: User Story #100
```

### Builds
```
Build #789: CI-Main
   Status: Succeeded | Duration: 5m 23s
   Trigger: PR merge | Branch: main
   Tests: 150 passed, 0 failed
```

### Pipelines
```
Pipeline: CI-Main (ID: 12)
   Last Run: Succeeded | Duration: 5m
   Trigger: Continuous Integration
   Stages: Build -> Test -> Deploy
```

## Error Handling

| Error Code | Cause | Solution |
|------------|-------|----------|
| 401 | Unauthorized | PAT expired - regenerate token |
| 403 | Forbidden | Insufficient permissions - check PAT scopes |
| 404 | Not Found | Invalid ID - verify project/item exists |
| VS403507 | Field validation | Check required fields |
| TF401019 | Item not found | Work item may be deleted |

## Best Practices

1. **Always start with context**
   - List projects first if unsure
   - Verify project name before operations

2. **Use appropriate work item types**
   - Bug for defects
   - Task for technical work
   - User Story for requirements

3. **Link related items**
   - Link bugs to user stories
   - Link tasks to parent stories
   - Link PRs to work items

4. **Include all required fields**
   - Title (always required)
   - Description (highly recommended)
   - Priority/Severity (for bugs)
   - Acceptance Criteria (for stories)

5. **Use WIQL for complex queries**
   - More powerful than simple filters
   - Supports date math (@Today - 7)
   - Supports hierarchy (UNDER)

6. **Monitor builds proactively**
   - Check build status after PR merge
   - Get logs for failed builds
   - Link build failures to bugs

## Integration Notes

This skill works with the Azure DevOps MCP server configured at:
- Settings: `C:\Users\ahmed\.claude\settings.json`
- Guides: `C:\odoo\AZURE_DEVOPS_MCP_CLAUDE_GUIDE.md`
- User Guide: `C:\odoo\AZURE_DEVOPS_USER_GUIDE.md`

The MCP server provides direct access to Azure DevOps REST APIs through a standardized protocol, enabling natural language interaction with all DevOps resources.
