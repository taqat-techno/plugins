# Azure DevOps MCP - Complete Reference

This document provides a complete reference for all Azure DevOps MCP tools and WIQL query syntax.

## Table of Contents

1. [Tool Reference](#tool-reference)
2. [WIQL Query Syntax](#wiql-query-syntax)
3. [Work Item Fields](#work-item-fields)
4. [Error Codes](#error-codes)
5. [API Limits](#api-limits)

---

## Tool Reference

### Core Domain (3 tools)

#### `mcp_ado_core_list_projects`
Lists all projects in the organization.

**Parameters:**
- `stateFilter` (optional): Filter by state (All, WellFormed, CreatePending, Deleting, New)
- `top` (optional): Number of results to return
- `skip` (optional): Number of results to skip

**Returns:** Array of project objects with id, name, description, state

---

#### `mcp_ado_core_list_project_teams`
Lists teams within a project.

**Parameters:**
- `projectId` (required): Project ID or name
- `top` (optional): Number of results
- `skip` (optional): Number to skip

**Returns:** Array of team objects with id, name, description

---

#### `mcp_ado_core_get_identity_ids`
Looks up user identities. **USE THIS to get user GUIDs for mentions!**

**Parameters:**
- `searchFilter` (required): Filter type - use `"General"` for name/email search
- `filterValue` (required): Value to search for (name or email)

**Returns:** Array of identity objects with `id` (GUID), `displayName`, `uniqueName`

**Example - Find user for mention:**
```
mcp_ado_core_get_identity_ids({
  "searchFilter": "General",
  "filterValue": "mahmoud"
})

# Returns:
{
  "id": "6011f8b0-xxxx-xxxx-xxxx-xxxxxxxxxxxx",  // ← Use this GUID for @mentions
  "displayName": "Mahmoud Elshahed",
  "uniqueName": "melshahed@pearlpixels.com"
}
```

**Common searchFilter values:**
- `"General"` - Search by display name or email (most common)
- `"DisplayName"` - Search by display name only
- `"MailAddress"` - Search by email only

---

### Work Items Domain (24 tools)

#### `mcp_ado_workitems_get_workitem`
Gets a single work item by ID.

**Parameters:**
- `id` (required): Work item ID
- `expand` (optional): Fields to expand (All, Relations, Fields, Links, None)

**Returns:** Work item object with all fields

---

#### `mcp_ado_workitems_list_workitems`
Lists work items with filters.

**Parameters:**
- `ids` (required): Array of work item IDs
- `fields` (optional): Array of field names to return
- `expand` (optional): Relations to expand

**Returns:** Array of work item objects

---

#### `mcp_ado_workitems_create_workitem`
Creates a new work item.

**Parameters:**
- `project` (required): Project name
- `type` (required): Work item type (Bug, Task, User Story, etc.)
- `title` (required): Work item title
- `description` (optional): Description HTML
- `assignedTo` (optional): User to assign
- `areaPath` (optional): Area path
- `iterationPath` (optional): Iteration/sprint path
- `priority` (optional): Priority (1-4)
- `severity` (optional): Severity for bugs (1-4)
- `tags` (optional): Comma-separated tags

**Returns:** Created work item object with ID

---

#### `mcp_ado_workitems_update_workitem`
Updates an existing work item.

**Parameters:**
- `id` (required): Work item ID
- `fields` (required): Object of field name-value pairs to update

**Returns:** Updated work item object

---

#### `mcp_ado_workitems_delete_workitem`
Deletes a work item.

**Parameters:**
- `id` (required): Work item ID
- `destroy` (optional): Permanently delete (default: false, moves to recycle bin)

**Returns:** Success confirmation

---

#### `mcp_ado_workitems_query_workitems`
Runs a WIQL query.

**Parameters:**
- `query` (required): WIQL query string
- `project` (optional): Project to scope query

**Returns:** Array of matching work items

---

#### `mcp_ado_workitems_link_workitems`
Links two work items together.

**Parameters:**
- `sourceId` (required): Source work item ID
- `targetId` (required): Target work item ID
- `linkType` (required): Type of link (Parent, Child, Related, etc.)
- `comment` (optional): Link comment

**Returns:** Success confirmation

---

#### `mcp_ado_workitems_add_comment`
Adds a comment to a work item. **USE THIS for mentions instead of update_work_item!**

**Parameters:**
- `id` (required): Work item ID
- `text` (required): Comment text (HTML supported)

**Returns:** Created comment object

**⚠️ IMPORTANT - For User Mentions:**
1. First get user GUID using `mcp_ado_core_get_identity_ids`
2. Use format `@<GUID>` in the comment text

**Example - Mention a user:**
```
# Step 1: Get user identity
mcp_ado_core_get_identity_ids({
  "searchFilter": "General",
  "filterValue": "mahmoud"
})
# Returns: { "id": "6011f8b0-xxxx-xxxx-xxxx-xxxxxxxxxxxx", ... }

# Step 2: Add comment with mention
mcp_ado_workitems_add_comment({
  "id": 1385,
  "text": "@<6011f8b0-xxxx-xxxx-xxxx-xxxxxxxxxxxx> please review this work item."
})
```

**DO NOT USE** `update_work_item` with `System.History` for comments/mentions!

---

#### `mcp_ado_workitems_get_comments`
Gets comments on a work item.

**Parameters:**
- `id` (required): Work item ID
- `top` (optional): Number of comments
- `order` (optional): asc or desc

**Returns:** Array of comment objects

---

### Repositories Domain (19 tools)

#### `mcp_ado_repos_list_repositories`
Lists all repositories.

**Parameters:**
- `project` (optional): Filter by project

**Returns:** Array of repository objects

---

#### `mcp_ado_repos_get_repository`
Gets repository details.

**Parameters:**
- `repositoryId` (required): Repository ID or name
- `project` (optional): Project name

**Returns:** Repository object with details

---

#### `mcp_ado_repos_list_branches`
Lists branches in a repository.

**Parameters:**
- `repositoryId` (required): Repository ID or name
- `filter` (optional): Branch name filter

**Returns:** Array of branch objects

---

#### `mcp_ado_repos_get_commits`
Gets commit history.

**Parameters:**
- `repositoryId` (required): Repository ID
- `branch` (optional): Branch name
- `top` (optional): Number of commits
- `skip` (optional): Number to skip
- `author` (optional): Filter by author
- `fromDate` (optional): Start date
- `toDate` (optional): End date

**Returns:** Array of commit objects

---

#### `mcp_ado_repos_get_file_content`
Reads file content from repository.

**Parameters:**
- `repositoryId` (required): Repository ID
- `path` (required): File path
- `version` (optional): Branch or commit

**Returns:** File content as string

---

#### `mcp_ado_repos_create_pull_request`
Creates a new pull request.

**Parameters:**
- `repositoryId` (required): Repository ID
- `sourceRefName` (required): Source branch (refs/heads/...)
- `targetRefName` (required): Target branch (refs/heads/...)
- `title` (required): PR title
- `description` (optional): PR description
- `reviewers` (optional): Array of reviewer IDs
- `workItemRefs` (optional): Array of work item IDs to link

**Returns:** Created PR object with ID

---

#### `mcp_ado_repos_get_pull_request`
Gets pull request details.

**Parameters:**
- `repositoryId` (required): Repository ID
- `pullRequestId` (required): PR ID

**Returns:** PR object with all details

---

#### `mcp_ado_repos_list_pull_requests`
Lists pull requests.

**Parameters:**
- `repositoryId` (required): Repository ID
- `status` (optional): active, completed, abandoned, all
- `creatorId` (optional): Filter by creator
- `reviewerId` (optional): Filter by reviewer
- `top` (optional): Number of results

**Returns:** Array of PR objects

---

#### `mcp_ado_repos_update_pull_request`
Updates a pull request.

**Parameters:**
- `repositoryId` (required): Repository ID
- `pullRequestId` (required): PR ID
- `title` (optional): New title
- `description` (optional): New description
- `status` (optional): New status

**Returns:** Updated PR object

---

#### `mcp_ado_repos_add_pr_comment`
Adds comment to pull request.

**Parameters:**
- `repositoryId` (required): Repository ID
- `pullRequestId` (required): PR ID
- `content` (required): Comment content
- `threadContext` (optional): File and line context for inline comments

**Returns:** Created comment thread

---

#### `mcp_ado_repos_complete_pull_request`
Completes/merges a pull request.

**Parameters:**
- `repositoryId` (required): Repository ID
- `pullRequestId` (required): PR ID
- `deleteSourceBranch` (optional): Delete branch after merge
- `mergeStrategy` (optional): noFastForward, rebase, squash

**Returns:** Completed PR object

---

### Pipelines Domain (13 tools)

#### `mcp_ado_pipelines_list_pipelines`
Lists all pipelines.

**Parameters:**
- `project` (required): Project name

**Returns:** Array of pipeline definitions

---

#### `mcp_ado_pipelines_get_pipeline`
Gets pipeline details.

**Parameters:**
- `project` (required): Project name
- `pipelineId` (required): Pipeline ID

**Returns:** Pipeline definition object

---

#### `mcp_ado_pipelines_run_pipeline`
Runs a pipeline.

**Parameters:**
- `project` (required): Project name
- `pipelineId` (required): Pipeline ID
- `branch` (optional): Branch to build
- `variables` (optional): Pipeline variables

**Returns:** Pipeline run object

---

#### `mcp_ado_pipelines_list_builds`
Lists builds.

**Parameters:**
- `project` (required): Project name
- `definitions` (optional): Filter by pipeline IDs
- `statusFilter` (optional): all, completed, inProgress, notStarted
- `resultFilter` (optional): succeeded, failed, canceled
- `top` (optional): Number of results
- `branchName` (optional): Filter by branch

**Returns:** Array of build objects

---

#### `mcp_ado_pipelines_get_build`
Gets build details.

**Parameters:**
- `project` (required): Project name
- `buildId` (required): Build ID

**Returns:** Build object with full details

---

#### `mcp_ado_pipelines_get_build_logs`
Gets build logs.

**Parameters:**
- `project` (required): Project name
- `buildId` (required): Build ID
- `logId` (optional): Specific log ID

**Returns:** Build logs as text

---

#### `mcp_ado_pipelines_get_build_changes`
Gets changes included in build.

**Parameters:**
- `project` (required): Project name
- `buildId` (required): Build ID

**Returns:** Array of changes/commits

---

#### `mcp_ado_pipelines_cancel_build`
Cancels a running build.

**Parameters:**
- `project` (required): Project name
- `buildId` (required): Build ID

**Returns:** Cancelled build object

---

### Test Plans Domain (11 tools)

#### `mcp_ado_testplan_list_test_plans`
Lists test plans.

**Parameters:**
- `project` (required): Project name
- `owner` (optional): Filter by owner
- `includePlanDetails` (optional): Include full details

**Returns:** Array of test plan objects

---

#### `mcp_ado_testplan_create_test_plan`
Creates a new test plan.

**Parameters:**
- `project` (required): Project name
- `name` (required): Plan name
- `areaPath` (optional): Area path
- `iteration` (optional): Iteration path
- `startDate` (optional): Plan start date
- `endDate` (optional): Plan end date

**Returns:** Created test plan object

---

#### `mcp_ado_testplan_list_test_cases`
Lists test cases.

**Parameters:**
- `project` (required): Project name
- `planId` (required): Test plan ID
- `suiteId` (required): Test suite ID

**Returns:** Array of test case objects

---

#### `mcp_ado_testplan_create_test_case`
Creates a new test case.

**Parameters:**
- `project` (required): Project name
- `title` (required): Test case title
- `steps` (optional): Array of test steps
- `expectedResult` (optional): Expected result

**Returns:** Created test case work item

---

#### `mcp_ado_testplan_get_test_results`
Gets test results.

**Parameters:**
- `project` (required): Project name
- `runId` (required): Test run ID

**Returns:** Array of test result objects

---

### Wiki Domain (6 tools)

#### `mcp_ado_wiki_list_wikis`
Lists all wikis.

**Parameters:**
- `project` (optional): Filter by project

**Returns:** Array of wiki objects

---

#### `mcp_ado_wiki_get_page`
Gets wiki page content.

**Parameters:**
- `project` (required): Project name
- `wikiIdentifier` (required): Wiki ID or name
- `path` (required): Page path
- `version` (optional): Version/branch

**Returns:** Page content as markdown

---

#### `mcp_ado_wiki_create_page`
Creates a new wiki page.

**Parameters:**
- `project` (required): Project name
- `wikiIdentifier` (required): Wiki ID
- `path` (required): Page path
- `content` (required): Page content (markdown)
- `comment` (optional): Creation comment

**Returns:** Created page object

---

#### `mcp_ado_wiki_update_page`
Updates a wiki page.

**Parameters:**
- `project` (required): Project name
- `wikiIdentifier` (required): Wiki ID
- `path` (required): Page path
- `content` (required): New content
- `comment` (optional): Update comment

**Returns:** Updated page object

---

### Search Domain (3 tools)

#### `mcp_ado_search_code`
Searches code across repositories.

**Parameters:**
- `searchText` (required): Search query
- `project` (optional): Filter by project
- `repository` (optional): Filter by repository
- `path` (optional): Filter by path
- `branch` (optional): Filter by branch

**Returns:** Array of code search results

---

#### `mcp_ado_search_wiki`
Searches wiki pages.

**Parameters:**
- `searchText` (required): Search query
- `project` (optional): Filter by project

**Returns:** Array of wiki search results

---

#### `mcp_ado_search_workitem`
Searches work items.

**Parameters:**
- `searchText` (required): Search query
- `project` (optional): Filter by project
- `filters` (optional): Additional filters

**Returns:** Array of work item search results

---

### Advanced Security Domain (2 tools)

#### `mcp_ado_advsec_get_alerts`
Gets security alerts.

**Parameters:**
- `project` (required): Project name
- `repository` (required): Repository name
- `alertType` (optional): Filter by type

**Returns:** Array of security alert objects

---

#### `mcp_ado_advsec_get_alert_details`
Gets security alert details.

**Parameters:**
- `project` (required): Project name
- `repository` (required): Repository name
- `alertId` (required): Alert ID

**Returns:** Alert object with full details

---

## WIQL Query Syntax

### Basic Structure
```sql
SELECT [Field1], [Field2]
FROM WorkItems
WHERE [Condition]
ORDER BY [Field]
```

### Operators
| Operator | Description | Example |
|----------|-------------|---------|
| `=` | Equals | `[System.State] = 'Active'` |
| `<>` | Not equals | `[System.State] <> 'Closed'` |
| `>`, `<` | Greater/Less than | `[Priority] < 3` |
| `>=`, `<=` | Greater/Less or equal | `[Priority] <= 2` |
| `CONTAINS` | String contains | `[System.Tags] CONTAINS 'urgent'` |
| `IN` | In list | `[System.State] IN ('Active', 'New')` |
| `UNDER` | Hierarchical match | `[System.IterationPath] UNDER 'Project\Sprint 1'` |

### Macros
| Macro | Description |
|-------|-------------|
| `@Me` | Current user |
| `@Today` | Today's date |
| `@CurrentIteration` | Current iteration |
| `@Project` | Current project |

### Date Math
```sql
[System.ChangedDate] >= @Today - 7  -- Last 7 days
[System.CreatedDate] <= @Today - 30 -- Older than 30 days
```

---

## Work Item Fields

### System Fields
| Field | Description |
|-------|-------------|
| `System.Id` | Work item ID |
| `System.Title` | Title |
| `System.State` | Current state |
| `System.WorkItemType` | Type (Bug, Task, etc.) |
| `System.AssignedTo` | Assigned user |
| `System.CreatedDate` | Creation date |
| `System.ChangedDate` | Last modified date |
| `System.CreatedBy` | Creator |
| `System.ChangedBy` | Last modifier |
| `System.AreaPath` | Area path |
| `System.IterationPath` | Iteration/Sprint |
| `System.Tags` | Tags |
| `System.Description` | Description |

### Common Fields
| Field | Description |
|-------|-------------|
| `Microsoft.VSTS.Common.Priority` | Priority (1-4) |
| `Microsoft.VSTS.Common.Severity` | Severity (1-4) |
| `Microsoft.VSTS.Common.Activity` | Activity type |
| `Microsoft.VSTS.Scheduling.StoryPoints` | Story points |
| `Microsoft.VSTS.Scheduling.OriginalEstimate` | Original estimate |
| `Microsoft.VSTS.Scheduling.RemainingWork` | Remaining work |
| `Microsoft.VSTS.Scheduling.CompletedWork` | Completed work |

---

## Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| 401 | Unauthorized | Check PAT validity |
| 403 | Forbidden | Check permissions |
| 404 | Not Found | Verify resource exists |
| 429 | Rate Limited | Wait and retry |
| VS403507 | Field validation | Check required fields |
| TF401019 | Item not found | Item may be deleted |
| TF400813 | Invalid area path | Verify path exists |
| TF401027 | Invalid iteration | Verify iteration exists |

---

## API Limits

- **Rate Limit**: 200 requests per minute per user
- **Batch Size**: Max 200 work items per request
- **Query Results**: Max 20,000 results
- **Attachment Size**: Max 130 MB
- **Comment Length**: Max 1 MB
