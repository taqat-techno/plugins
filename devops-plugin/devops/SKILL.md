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

## ⚠️ CRITICAL: Correct Tool Selection

### DEFAULT: Always Query by Project First

**ALWAYS** start by listing projects, then query each project:

```
# Step 1: Get all projects
mcp_ado_core_list_projects()

# Step 2: Query EACH project (required!)
mcp_ado_workitems_query_workitems({
  "project": "ProjectName",  // ← ALWAYS REQUIRED
  "query": "SELECT ... FROM WorkItems WHERE ..."
})
```

### Getting Work Items by AssignedTo (My Tasks)

**WRONG** ❌: `search_workitem` with filters - This is TEXT SEARCH only!
```javascript
// WRONG - Returns 0 results! search_workitem is for TEXT SEARCH, not field filtering
mcp__azure-devops__search_workitem({
  "searchText": "*",
  "assignedTo": ["@Me"],     // IGNORED! Not a query filter!
  "state": ["New", "Active"] // IGNORED! Not a query filter!
})
```

**CORRECT** ✅: Use `wit_my_work_items` (RECOMMENDED - Fastest!)
```javascript
// Step 1: Get work item IDs for each project
mcp__azure-devops__wit_my_work_items({
  "project": "Relief Center",
  "type": "assignedtome",
  "includeCompleted": false,
  "top": 100
})

// Step 2: Get full details for the returned IDs
mcp__azure-devops__wit_get_work_items_batch_by_ids({
  "project": "Relief Center",
  "ids": [1746, 1828, 1651],  // IDs from step 1
  "fields": ["System.Id", "System.Title", "System.State", "System.WorkItemType", "System.TeamProject"]
})
```

**ALTERNATIVE** ✅: Use WIQL query with project scope
```javascript
// Must specify project - queries cannot be truly global
mcp__azure-devops__wit_get_query_results_by_id({
  "project": "Relief Center",
  "id": "assignedtome"  // Use predefined query
})
```

### Tool Purpose Summary
| Task | Correct Tool | Wrong Tool |
|------|--------------|------------|
| List all projects | `core_list_projects` (FIRST!) | - |
| **My assigned work items** | `wit_my_work_items` ⭐ (FASTEST!) | ❌ `search_workitem` |
| Filter by state/type | `wit_my_work_items` or WIQL | ❌ `search_workitem` |
| Search text in items | `search_workitem` | - |
| Get single item by ID | `wit_get_work_item` | - |
| Get multiple items by IDs | `wit_get_work_items_batch_by_ids` | - |
| **Add comment/mention** | `wit_add_work_item_comment` | ❌ `wit_update_work_item` with System.History |

### Adding Comments and Mentions

**WRONG** ❌: Using `update_work_item` with `System.History`
```
# WRONG - System.History is read-only/append-only, mentions don't work properly
update_work_item({
  "workItemId": 1385,
  "additionalFields": {"System.History": "<a href='mailto:...'>Name</a>"}
})
```

**CORRECT** ✅: Use `mcp_ado_workitems_add_comment` for comments
```
# CORRECT - Use dedicated comment tool
mcp_ado_workitems_add_comment({
  "id": 1385,
  "text": "Mentioning @<6011f8b0-...> for review."  // Use GUID format
})
```

### User Mention Format in Azure DevOps

To mention a user, you need their **Identity GUID**:

1. **First, get user identity**:
```
mcp_ado_core_get_identity_ids({
  "searchFilter": "General",
  "filterValue": "ahmed"
})
```

2. **Use the GUID in mention**:
```
# Format: @<GUID>
mcp_ado_workitems_add_comment({
  "id": 1385,
  "text": "@<6011f8b0-xxxx-xxxx-xxxx-xxxxxxxxxxxx> please review this."
})
```

### Common Mention Patterns

| Action | Tool | Format |
|--------|------|--------|
| Add comment | `add_comment` | Plain text or HTML |
| Mention user | `add_comment` | `@<GUID>` where GUID from `get_identity_ids` |
| Update field | `update_workitem` | Only for actual field updates |
| Get user GUID | `get_identity_ids` | Search by name/email |

### Automatic Mention Processing

When adding comments with @mentions, follow this process:

1. **Detect @mentions in text**:
   - Pattern: `@username`, `@firstname.lastname`, `@email`
   - Example: "Please review this @mahmoud @eslam.hafez"

2. **Resolve each mention to GUID**:
   ```
   For each @mention found:
     mcp__azure-devops__core_get_identity_ids({
       "searchFilter": "extracted_username"
     })
   ```

3. **Convert to HTML anchor format** (better UI rendering):
   ```html
   <a href="#" data-vss-mention="version:2.0,guid:GUID">@DisplayName</a>
   ```

4. **Add comment with processed text**:
   ```
   mcp__azure-devops__wit_add_work_item_comment({
     "project": "ProjectName",
     "workItemId": 1234,
     "comment": "Please review <a href=\"#\" data-vss-mention=\"version:2.0,guid:abc-123\">@Mahmoud Elshahed</a>",
     "format": "html"
   })
   ```

### TaqaTechno Team Members (Quick Reference)

| Name | Email | Use |
|------|-------|-----|
| Ahmed Abdelkhaleq | alakosha@pearlpixels.com | @ahmed |
| Eslam Hafez Mohamed | ehafez@pearlpixels.com | @eslam |
| Yussef Hussein | yhussein@pearlpixels.com | @yussef |
| Sameh Abdlal | sabdlal@pearlpixels.com | @sameh |
| Mahmoud Elshahed | melshahed@pearlpixels.com | @mahmoud |

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
For finding content via **TEXT SEARCH** (searching within content).

⚠️ **CRITICAL WARNING**: These tools search TEXT/CONTENT only! They do NOT filter by fields like AssignedTo!
- **For filtering by AssignedTo**: Use `mcp_ado_workitems_query_workitems` with WIQL
- **For text search in work item content**: Use `mcp_ado_search_workitem`

| Tool | Description | Example Use |
|------|-------------|-------------|
| `mcp_ado_search_code` | Search code content | "Find 'authenticate' in code" |
| `mcp_ado_search_wiki` | Search wiki content | "Search for deployment in wiki" |
| `mcp_ado_search_workitem` | Search work item text/titles | "Find items mentioning 'login'" |

**NEVER use `mcp_ado_search_workitem` to filter by AssignedTo, State, or other fields!**

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

## Work Item Hierarchy Rules

### MANDATORY: Enforce This Hierarchy

```
Epic (Strategic Initiative)
  └── Feature (Functional Area)
        └── User Story / PBI (Requirement)
              ├── Task (Technical Work)
              └── Bug (Defect)
```

### Creation Rules

| Creating | Must Have Parent | Parent Type |
|----------|-----------------|-------------|
| **Task** | REQUIRED | Bug OR User Story/PBI |
| **Bug** | RECOMMENDED | User Story/PBI (or standalone) |
| **User Story/PBI** | REQUIRED | Feature |
| **Feature** | REQUIRED | Epic |
| **Epic** | None | Top-level |

### Validation Before Creation

Before creating a work item, ALWAYS:

1. **For Task**:
   - Ask: "Which Bug or User Story should this task be under?"
   - If no parent specified, prompt user to:
     a) Select existing Bug/PBI
     b) Create new Bug/PBI first
   - NEVER create orphan tasks

2. **For User Story/PBI**:
   - Ask: "Which Feature should this story be under?"
   - If no Feature exists, prompt to create one
   - If no Feature specified, list available Features

3. **For Feature**:
   - Ask: "Which Epic should this feature be under?"
   - List available Epics in project
   - Create Epic first if needed

### Linking After Creation

Always link child to parent immediately:
```
mcp__azure-devops__wit_work_items_link({
  "project": "ProjectName",
  "updates": [{
    "id": CHILD_ID,
    "linkToId": PARENT_ID,
    "type": "child"
  }]
})
```

### Example Workflow: Creating a Task

```
User: "Create task: Fix login button"

Claude:
1. Ask: "Which User Story or Bug should this task be under?"
2. User provides parent ID or creates new PBI
3. Create task
4. Link task to parent
5. Confirm: "Task #1234 created under PBI #1000"
```

### User Story Format (What? How? Why?)

When creating User Stories or PBIs, ALWAYS structure with:

1. **WHAT?** (Requirements)
   - What needs to be done?
   - What is the deliverable?
   - What are the acceptance criteria?

2. **HOW?** (Approach)
   - How will this be implemented?
   - What technical approach?
   - What components are affected?

3. **WHY?** (Business Value)
   - Why is this needed?
   - What problem does it solve?
   - What value does it deliver?

**Template:**
```markdown
## What (Requirements)
[Description of what needs to be done]

### Acceptance Criteria
- [ ] Criteria 1
- [ ] Criteria 2
- [ ] Criteria 3

## How (Implementation Approach)
[Technical approach description]

### Affected Components
- Component 1
- Component 2

## Why (Business Value)
[Business justification]

### Impact
- User benefit
- Business benefit
```

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
