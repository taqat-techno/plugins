---
name: devops
description: |
  Azure DevOps HYBRID integration skill for your Azure DevOps organization. Combines CLI power with MCP convenience for optimal performance. Uses CLI for automation, batch operations, variables, and extensions. Uses MCP for interactive queries, code reviews, test plans, search, and security alerts. Intelligent routing automatically selects the best tool for each task.


  <example>
  Context: User wants to create a work item in Azure DevOps
  user: "Create a user story for the login feature in Azure DevOps"
  assistant: "I will use the devops skill with the Azure DevOps MCP server to create a User Story work item under the correct epic with title, description, and acceptance criteria."
  <commentary>Core trigger - work item creation via Azure DevOps MCP.</commentary>
  </example>

  <example>
  Context: User wants to view their sprint tasks
  user: "Show me my active sprint tasks and their status"
  assistant: "I will use the devops skill to query the current sprint via MCP, filter by assigned user, and display a formatted task board with status and remaining hours."
  <commentary>Sprint management trigger - task visibility.</commentary>
  </example>

  <example>
  Context: User wants to log time on a work item
  user: "Log 3 hours on work item #1234 for today"
  assistant: "I will use the devops skill to record a time entry against work item 1234, update remaining hours, and confirm the log in the timesheet summary."
  <commentary>Time tracking trigger - logging work hours to Azure DevOps.</commentary>
  </example>

  <example>
  Context: User wants automated periodic monitoring of new work assignments
  user: "Start monitoring my tasks every 15 minutes and alert me when I get new work items assigned"
  assistant: "I will run /task-monitor to set the current work item baseline, then you can use /loop 15m /task-monitor to get automatic alerts whenever a new item is assigned to you in Azure DevOps."
  <commentary>Loop-based task monitor trigger - periodic new assignment alerts.</commentary>
  </example>

  <example>
  Context: User wants to check if any new Azure DevOps tasks were assigned since they last checked
  user: "Any new tasks assigned to me since this morning?"
  assistant: "I will use the devops skill to run /task-monitor which fetches a live snapshot from Azure DevOps and shows only items assigned since the last check."
  <commentary>On-demand new assignment diff trigger - task monitor single run.</commentary>
  </example>

  <example>
  Context: User wants to update a work item state
  user: "Mark task #1234 as done, I spent 6 hours on it"
  assistant: "I will use the devops skill to validate the state transition, check required fields (OriginalEstimate, CompletedWork), and update the work item with pre-flight validation."
  <commentary>Update work item trigger - state change with required field validation. See devops/workflows.md Workflow 1.</commentary>
  </example>

  <example>
  Context: User wants to add a comment with mentions
  user: "Comment on #1234 telling @mahmoud to review this"
  assistant: "I will use the devops skill to resolve the @mention to a GUID via API, format as HTML, and post the comment so the mentioned user receives a notification."
  <commentary>Add comment trigger - mention resolution and validated comment posting. See devops/workflows.md Workflow 2.</commentary>
  </example>

  <example>
  Context: User wants to switch project context
  user: "Switch to relief center project"
  assistant: "I will use the devops skill to resolve the project alias and update the session context for all subsequent queries."
  <commentary>Project context switch trigger. See devops/workflows.md Workflow 3.</commentary>
  </example>

  <example>
  Context: User asks about build or CI status
  user: "Any failing builds in our pipeline?"
  assistant: "I will use the devops skill to check recent build status, list successes and failures, and provide quick actions for any failed builds."
  <commentary>Build status trigger - pipeline health check. See devops/workflows.md Workflow 4.</commentary>
  </example>

  <example>
  Context: User wants to create a pull request
  user: "Create a PR from feature/login to main in the relief repo"
  assistant: "I will use the devops skill to resolve the repository name to a GUID, validate both branches exist, and create the pull request."
  <commentary>PR creation trigger - repository resolution and PR creation. See devops/workflows.md Workflow 5.</commentary>
  </example>

  <example>
  Context: User wants to set up CI/CD pipelines
  user: "Set up GitHub Actions for our Odoo project"
  assistant: "I will use the devops skill to determine deployment target (Odoo.sh or self-hosted), then generate the appropriate GitHub Actions workflow files."
  <commentary>CI/CD setup trigger - workflow generation. See devops/workflows.md Workflow 6.</commentary>
  </example>
license: "MIT"
metadata:
  version: "3.0.0"
  author: "TAQAT Techno"
  allowed-tools: "Read, Write, Bash, WebFetch, Glob, Grep"
  organization: "YOUR-ORG"
  mode: "hybrid"
  mcp-server: "@anthropic-ai/azure-devops-mcp"
  cli-extension: "azure-devops"
  cli-min-version: "2.30.0"
  tools-count: "100+ MCP tools + full CLI"
  domains: "core,work,work-items,repositories,pipelines,test-plans,wiki,search,advanced-security"
  cli-exclusive: "variables,extensions,service-connections,project-creation,batch-scripting"
  mcp-exclusive: "test-plans,search,security-alerts,pr-threads,team-capacity"
---

# Azure DevOps Integration Skill (v2.0 - Hybrid Mode)

A comprehensive skill for managing Azure DevOps resources through natural language, leveraging **BOTH** Azure DevOps CLI and MCP Server for optimal performance.

## Configuration

- **Organization**: YOUR-ORG
- **Mode**: **HYBRID** (CLI + MCP)
- **MCP Server**: `@anthropic-ai/azure-devops-mcp` (Official Anthropic)
- **CLI Extension**: `azure-devops` (via Azure CLI)
- **Authentication**: Personal Access Token (PAT)
  - CLI: `AZURE_DEVOPS_EXT_PAT` environment variable
  - MCP: `ADO_PAT_TOKEN` environment variable
- **Tools Available**: 100+ MCP tools + full CLI command set

---

## STEP 0: LOAD USER PROFILE (AUTO — EVERY SESSION)

Before any DevOps operation, check for the user's profile:

```
1. Try to Read ~/.claude/devops.md
2. If found:
   a. Parse YAML frontmatter
   b. Extract: identity (name, email, guid), role, taskPrefix, defaultProject, team
   c. Build team member lookup: Map(alias → {name, email, guid})
      - Include "me", "myself", "I" → current user's identity
   d. Set session context: currentProject = profile.defaultProject
   e. Load statePermissions from profile YAML
      - These permissions are checked BEFORE any state transition
        (see validators/state_transition_validator.md)
   f. Log: "Profile loaded: {displayName} ({role}) — {defaultProject}"
3. If NOT found:
   a. Show suggestion: "No DevOps profile found. Run /init profile for faster operations."
   b. Fall back to API-based resolution (existing behavior)
   c. Continue with the requested operation
```

**Reference**: `devops/profile_generator.md` for full profile structure.

### Profile-Aware Shortcuts

| User Says | Without Profile | With Profile |
|-----------|----------------|--------------|
| "assign to me" | API call to resolve identity | Instant: use `identity.guid` |
| "@mahmoud" | API call to resolve GUID | Cache lookup → instant if found |
| /create "Fix bug" | Infer prefix from keywords | Use `preferences.taskPrefix` from role |
| (session start) | Auto-detect project via API | Use `defaultProject` from profile |

---

## WRITE OPERATION GATE (MANDATORY — READ THIS FIRST)

**Reference**: `guards/write_operation_guard.md`

**CRITICAL**: Before executing ANY operation that creates, updates, or deletes resources in Azure DevOps, you **MUST**:

1. **Gather** all required information (title, parent, sprint, fields)
2. **Investigate** freely using READ operations (queries, fetches, searches)
3. **Present** a confirmation summary showing exactly what will be created/modified
4. **Wait** for explicit user approval ("yes", "go ahead", "create it", etc.)
5. **Only then** execute the MCP/CLI write command

This applies to ALL write operations: `/create` command, "update work item" (skill), "add comment" (skill), "create PR" (skill), pipeline variables via `/cli-run`, extension management via `/cli-run`.

**In Plan Mode**: NEVER execute write operations — only describe what will be created. Investigate, research, and validate freely, but do NOT call any write MCP tool or CLI command. Plan Mode means research and plan only.

**NO EXCEPTIONS.** Even if the user says "create task X" in one sentence — gather the details, present the summary, and get their explicit "yes" before executing.

See `guards/write_operation_guard.md` for the full list of classified operations and confirmation summary templates.

---

## Hybrid Mode: CLI + MCP Integration

This skill leverages **BOTH** Azure DevOps CLI and MCP Server for optimal performance. Claude automatically routes tasks to the best tool based on task characteristics.

### Quick Decision Matrix

| Task Type | Use CLI | Use MCP | Reason |
|-----------|:-------:|:-------:|--------|
| Batch work item updates | **Y** | | CLI scripting faster for loops |
| Single work item query | | **Y** | MCP more convenient |
| Create multiple items | **Y** | | CLI parallel execution |
| PR code review threads | | **Y** | MCP has dedicated tools |
| Create service connections | **Y** | | CLI only feature |
| Install extensions | **Y** | | CLI only feature |
| Manage pipeline variables | **Y** | | CLI only feature |
| Run pipelines | **Y** | Y | CLI better for CI/CD |
| Test plan management | | **Y** | MCP only feature |
| Security alerts | | **Y** | MCP only feature |
| Search code/wiki | | **Y** | MCP only feature |
| Create projects | **Y** | | CLI better |
| Daily standup queries | | **Y** | MCP more natural |
| Sprint reports | | **Y** | MCP queries sufficient |
| Automated scripts | **Y** | | CLI scriptable |
| Team capacity | | **Y** | MCP only feature |
| Interactive conversation | | **Y** | MCP natural language |

### When Claude Uses CLI

| Scenario | CLI Command | Reason |
|----------|-------------|--------|
| Batch updates | `az boards work-item update` in loop | Scriptable |
| Create infrastructure | `az devops project create` | CLI only |
| Variable management | `az pipelines variable` | CLI only |
| Extension management | `az devops extension` | CLI only |
| Automated pipelines | `az pipelines run` | CI/CD integration |
| Parallel operations | Multiple `az` commands with `&` | Performance |

### When Claude Uses MCP

| Scenario | MCP Tool | Reason |
|----------|----------|--------|
| Interactive queries | `wit_my_work_items` | Convenience |
| Code review | `repo_*_pull_request_thread*` | Dedicated tools |
| Test management | `testplan_*` | MCP only |
| Security alerts | `advsec_*` | MCP only |
| Search | `search_*` | MCP only |
| Natural language | All tools | Better UX |

### Hybrid Workflow Example

```
User: "Create 10 tasks for implementing authentication and assign to the team"

Claude's Approach:
1. Use MCP to get team member identities
2. Use CLI batch script to create tasks in parallel
3. Use MCP to verify and report results

Step 1 (MCP):
mcp__azure-devops__core_get_identity_ids({ searchFilter: "mahmoud" })
mcp__azure-devops__core_get_identity_ids({ searchFilter: "eslam" })

Step 2 (CLI):
for i in 1..10; do
  az boards work-item create --title "Auth Task $i" --type Task --assigned-to $TEAM[$i % 2] &
done
wait

Step 3 (MCP):
mcp__azure-devops__wit_my_work_items({ project: "...", top: 10 })
# Confirm creation and report to user
```

### CLI-Only Features

These features are **ONLY available via CLI**, not MCP:

| Feature | CLI Command |
|---------|-------------|
| Create project | `az devops project create` |
| Create repository | `az repos create` |
| Variable groups | `az pipelines variable-group` |
| Pipeline variables | `az pipelines variable` |
| Service connections | `az devops service-endpoint` |
| Extensions | `az devops extension install` |
| Create pipeline | `az pipelines create` |

### MCP-Only Features

These features are **ONLY available via MCP**, not CLI:

| Feature | MCP Tool |
|---------|----------|
| Test plans | `testplan_list_test_plans`, `testplan_create_test_plan` |
| Test cases | `testplan_create_test_case`, `testplan_update_test_case_steps` |
| Test results | `testplan_show_test_results_from_build_id` |
| Code search | `search_code` |
| Wiki search | `search_wiki` |
| Work item search | `search_workitem` |
| Security alerts | `advsec_get_alerts`, `advsec_get_alert_details` |
| PR threads | `repo_list_pull_request_threads` |
| PR thread comments | `repo_list_pull_request_thread_comments` |
| Reply to PR comment | `repo_reply_to_comment` |
| Resolve PR thread | `repo_resolve_comment` |
| Team capacity | `work_get_team_capacity`, `work_update_team_capacity` |
| Batch work item update | `wit_update_work_items_batch` |

---

## CLI Command Reference (Quick Access)

Quick reference for common CLI commands. Use these when Claude selects CLI for a task.

### Work Items (CLI)

```bash
# Create work item
az boards work-item create --title "Task Title" --type Task --project "Project"

# Update work item
az boards work-item update --id 123 --state "In Progress"

# Query work items (WIQL)
az boards query --wiql "SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.AssignedTo] = @Me"

# Show work item details
az boards work-item show --id 123 --output yaml

# Delete work item
az boards work-item delete --id 123 --yes

# Add relation/link
az boards work-item relation add --id 123 --relation-type "System.LinkTypes.Hierarchy-Reverse" --target-id 456
```

### Pull Requests (CLI)

```bash
# List active PRs
az repos pr list --status active --output table

# Create PR
az repos pr create --source-branch feature/login --target-branch main --title "Feature: Login"

# Update PR (auto-complete, squash)
az repos pr update --id 45 --auto-complete true --squash true

# Complete/merge PR
az repos pr update --id 45 --status completed

# Add reviewer
az repos pr reviewer add --id 45 --reviewers user@email.com

# Show PR details
az repos pr show --id 45 --output yaml
```

### Pipelines (CLI)

```bash
# Run pipeline
az pipelines run --name "CI-Build" --branch main

# List builds
az pipelines runs list --top 10 --output table

# Get build status
az pipelines runs show --id 456

# List pipeline definitions
az pipelines list --output table

# Get build logs
az pipelines runs artifact download --build-id 456 --artifact-name drop

# Cancel build
az pipelines build cancel --build-id 456
```

### Repositories (CLI)

```bash
# List repos
az repos list --output table

# Show repo details
az repos show --repository my-repo

# List branches
az repos ref list --repository my-repo --filter heads/

# Create branch
az repos ref create --name refs/heads/feature/new --repository my-repo --object-id <commit-sha>
```

### Infrastructure (CLI Only)

These features are **ONLY available via CLI**:

```bash
# Create project
az devops project create --name "New Project" --description "Description" --process Agile

# Variable groups
az pipelines variable-group list --output table
az pipelines variable-group create --name "Production Secrets" --variables API_URL=https://api.example.com --authorize true
az pipelines variable-group variable create --group-id 1 --name API_KEY --secret true

# Pipeline variables
az pipelines variable create --name ENVIRONMENT --value staging --pipeline-name "CI-Build"
az pipelines variable update --name ENVIRONMENT --value production --pipeline-name "CI-Build"

# Service connections
az devops service-endpoint list --output table
az devops service-endpoint azurerm create --name "Azure Production" --azure-rm-subscription-id "sub-id"

# Extensions
az devops extension search --search-query "timetracker" --output table
az devops extension install --publisher-id ms-devlabs --extension-id workitem-feature-timeline-extension
az devops extension list --output table
```

### Output Formatting

```bash
# Table format (human-readable)
az devops project list --output table

# JSON format (for parsing)
az repos list --output json

# TSV format (for scripts)
az repos list --query "[].name" --output tsv

# YAML format (configuration)
az boards work-item show --id 123 --output yaml

# JMESPath query filtering
az repos list --query "[].{Name:name, ID:id}" --output table
az repos pr list --query "[?status=='active']" --output table
```

### Batch Operations

```bash
# Update multiple work items (sequential)
az boards work-item update --id 1 --state Done && az boards work-item update --id 2 --state Done

# Create multiple work items (parallel)
for i in 1 2 3 4 5; do
  az boards work-item create --title "Task $i" --type Task &
done
wait

# Query and pipe to another command
az boards query --wiql "SELECT [System.Id] FROM WorkItems WHERE [System.State] = 'To Do'" \
  --query "[].id" -o tsv | while read id; do
    az boards work-item update --id $id --state "In Progress"
  done
```

### Environment Setup

```bash
# Configure defaults
az devops configure --defaults organization=https://dev.azure.com/YOUR-ORG project="Project Alpha"

# Check current configuration
az devops configure --list

# Login with PAT
echo $AZURE_DEVOPS_EXT_PAT | az devops login --organization https://dev.azure.com/YOUR-ORG

# Verify authentication
az devops project list
```

---

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
  "project": "Project Alpha",
  "type": "assignedtome",
  "includeCompleted": false,
  "top": 100
})

// Step 2: Get full details for the returned IDs
mcp__azure-devops__wit_get_work_items_batch_by_ids({
  "project": "Project Alpha",
  "ids": [1746, 1828, 1651],  // IDs from step 1
  "fields": ["System.Id", "System.Title", "System.State", "System.WorkItemType", "System.TeamProject"]
})
```

**ALTERNATIVE** ✅: Use WIQL query with project scope
```javascript
// Must specify project - queries cannot be truly global
mcp__azure-devops__wit_get_query_results_by_id({
  "project": "Project Alpha",
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

### 🛡️ Tool Selection Guard (MANDATORY)

**Reference**: See `guards/tool_selection_guard.md` for complete documentation.

Claude MUST apply this guard **BEFORE** executing any work item query tool:

#### Auto-Correction Rules

**Rule 1: Intent Detection**
```
TRIGGER PHRASES → FORCE wit_my_work_items:
- "my tasks" / "my work items" / "assigned to me"
- "my bugs" / "my stories" / "my items"
- "show what I'm working on" / "my current work"

IF user says these AND intended_tool == search_workitem:
  → BLOCK search_workitem
  → USE wit_my_work_items INSTEAD
```

**Rule 2: Filter Parameter Validation**
```
BEFORE executing search_workitem, CHECK:
  - Does call include assignedTo parameter?
  - Does call include state parameter?
  - Does call include iteration parameter?

IF ANY filter params present:
  → WARN: "search_workitem ignores these filters!"
  → DO NOT EXECUTE
  → SUGGEST: wit_my_work_items or CLI WIQL
```

**Rule 3: Wildcard Search Detection**
```
IF searchText == "*" OR searchText is empty/wildcard:
  AND has filter parameters:
    → This is NOT a text search
    → REDIRECT to wit_my_work_items or WIQL
```

#### Guard Execution Flow

```
┌───────────────────────────────────────────────────────────────┐
│ 1. ANALYZE: Extract intent from user request                  │
│    "show my active tasks" → intent="my items", filter="Active"│
├───────────────────────────────────────────────────────────────┤
│ 2. MATCH: Map intent to correct tool                          │
│    "my items" → wit_my_work_items ✅                          │
├───────────────────────────────────────────────────────────────┤
│ 3. VALIDATE: Check for wrong tool selection                   │
│    IF search_workitem with filters → BLOCK & REDIRECT         │
├───────────────────────────────────────────────────────────────┤
│ 4. EXECUTE: Run validated tool with correct params            │
└───────────────────────────────────────────────────────────────┘
```

#### Quick Decision Matrix

| User Says | Correct Tool | Never Use |
|-----------|--------------|-----------|
| "my tasks" | `wit_my_work_items` | `search_workitem` |
| "search for login" | `search_workitem` | - |
| "active bugs" | CLI WIQL | `search_workitem` |
| "sprint backlog" | `wit_get_work_items_for_iteration` | `search_workitem` |
| "work item #123" | `wit_get_work_item` | - |

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

### 🔔 Mention Processing with Validation (MANDATORY)

**Reference**: `processors/mention_processor.md` and `data/team_members.json`

```
┌─────────────────────────────────────────────────────────────────┐
│           ⚠️ CRITICAL: NEVER POST FAKE MENTIONS                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  BEFORE posting any comment with @mentions:                     │
│                                                                  │
│  1. EXTRACT all @mentions from text                             │
│  2. RESOLVE each to GUID via core_get_identity_ids API          │
│  3. VALIDATE all resolutions succeeded                          │
│                                                                  │
│  IF ANY mention fails to resolve:                               │
│    → DO NOT POST the comment                                    │
│    → ASK USER for clarification                                 │
│    → SUGGEST known team members                                 │
│    → WAIT for correct name                                      │
│                                                                  │
│  Plain text "@name" does NOT send notifications!                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Mention Resolution Workflow

```
User: "Add comment mentioning @mahmoud"

STEP 1: Extract mentions
  → Found: ["mahmoud"]

STEP 2: Resolve via API (MANDATORY)
  → core_get_identity_ids({ searchFilter: "mahmoud" })
  → Result: { id: "6011f8b0-...", displayName: "John Doe" }

STEP 3: Validate resolution
  → ✅ GUID found → Proceed
  → ❌ No match → ASK USER (do not post!)

STEP 4: Format as HTML
  → <a href="#" data-vss-mention="version:2.0,guid:6011f8b0-...">@John Doe</a>

STEP 5: Post comment with format: "html"
```

#### Failed Resolution - MUST Ask User

```
User: "Add comment mentioning @bob"

Claude (after failed API lookup):
┌─────────────────────────────────────────────────────────────────┐
│ ⚠️ I couldn't find a user matching "@bob" in Azure DevOps.       │
│                                                                  │
│ Did you mean one of these team members?                         │
│ • John Doe (@mahmoud)                                   │
│ • Jane Smith (@eslam)                                          │
│ • User One (@ahmed)                                    │
│ • Bob Williams (@mohamed)                                      │
│                                                                  │
│ Please provide the correct name or email.                       │
│ I won't post until I can properly resolve the mention.          │
└─────────────────────────────────────────────────────────────────┘
```

#### Code Example: Proper Mention Flow

```javascript
// Step 1: Resolve mention (REQUIRED)
const identity = await mcp__azure-devops__core_get_identity_ids({
  "searchFilter": "mahmoud"
});

// Step 2: Check if resolved
if (!identity || identity.length === 0) {
  // DO NOT POST - Ask user for clarification
  return "I couldn't find @mahmoud. Did you mean...?";
}

// Step 3: Format HTML mention
const mention = `<a href="#" data-vss-mention="version:2.0,guid:${identity.id}">@${identity.displayName}</a>`;

// Step 4: Post comment
mcp__azure-devops__wit_add_work_item_comment({
  "project": "Project Alpha",
  "workItemId": 1234,
  "comment": `Please review this. ${mention}`,
  "format": "html"  // REQUIRED for mentions
});
```

### Team Members Quick Reference (configure in data/team_members.json)

| Name | Email | Search Terms |
|------|-------|--------------|
| John Doe | user@company.com | @john, @jdoe |
| Jane Smith | user@company.com | @jane, @jsmith |
| Alice Johnson | user@company.com | @alice, @ajohnson |
| Bob Williams | user@company.com | @bob, @bwilliams |
| Carol Brown | user@company.com | @carol, @cbrown |

**Note**: Always resolve via API - never assume GUIDs!

### 🔒 Pre-Flight Validation (MANDATORY)

**Reference**: `validators/state_transition_validator.md` and `data/required_fields.json`

Claude MUST validate **BEFORE** executing any state change on work items:

#### Pre-Flight Validation Workflow

```
┌───────────────────────────────────────────────────────────────┐
│ User: "Mark task #1234 as Done"                               │
├───────────────────────────────────────────────────────────────┤
│ STEP 1: FETCH current work item                               │
│   wit_get_work_item({ id: 1234, project: "...",               │
│     fields: ["System.State", "System.WorkItemType",           │
│              "Microsoft.VSTS.Scheduling.*"] })                │
├───────────────────────────────────────────────────────────────┤
│ STEP 2: CHECK required fields for transition                  │
│   Task → Done REQUIRES: OriginalEstimate, CompletedWork       │
├───────────────────────────────────────────────────────────────┤
│ STEP 3: If MISSING → ASK user (DO NOT attempt update!)        │
│   "To mark as Done, I need: Original Estimate? Hours spent?"  │
├───────────────────────────────────────────────────────────────┤
│ STEP 4: EXECUTE single update with ALL fields + state         │
└───────────────────────────────────────────────────────────────┘
```

#### Required Fields by Transition

| Work Item Type | To State | Required Fields | Auto-Set |
|----------------|----------|-----------------|----------|
| **Task** | Done | `OriginalEstimate`, `CompletedWork` | `RemainingWork=0` |
| **Bug** | Resolved | `ResolvedReason` (default: "Fixed") | - |
| **PBI** | Done | - | **BLOCKED unless "Ready For QC"** → Must go through QC checkpoint |

#### State Machine Enforcement — TaqaTechno Real States

All work item types follow TaqaTechno's actual Azure DevOps process template states:

```
WORK ITEM STATE MACHINES (with role annotations):

Task:          To Do → In Progress (any) → Done (dev only) → Closed (PM only) → Removed (PM only)
Bug:           New → Approved (QA) → In Progress (dev) → Resolved (dev) → Done (QA) → Closed (PM) → Removed (PM)
                     └→ Return (QA) → In Progress (dev) [rejection loop]
PBI:           New → Approved (PM) → Committed (PM) → In Progress (dev) → Ready For QC (dev) → Done (QA) → Removed (PM)
                     └→ Return (QA) → In Progress (dev) [rejection loop]
User Story:    New → Committed (PM) → Done (PM/QA)
Enhancement:   New → Committed (PM) → Return (QA) → Done (PM/QA) → Closed (PM)
Feature:       New → In Progress (PM) → Done (PM) → Removed (PM)
Epic:          New → In Progress (PM) → Done (PM) → Removed (PM)
```

**Role Legend**: any = any team member, dev = developer, QA = tester/QC, PM = project manager/lead

**Key Rules**:
- PBI CANNOT go directly to Done — must pass through "Ready For QC" first
- Bug has a Return rejection loop (QA sends back to dev)
- PBI has a Return rejection loop (QA sends back to dev)
- Only PM can close Tasks, Bugs, and Enhancements
- Only PM can remove any work item type

#### Example: Task → Done Pre-Flight

**User**: "Mark task #1234 as Done"

**Claude** (BEFORE attempting update):
```
Checking task #1234...

To mark this task as Done, I need:
• Original Estimate (hours): ___
• Completed Work (hours): ___

I'll automatically set Remaining Work to 0.

Please provide these values.
```

**User**: "8 hours estimated, 6 actual"

**Claude** (NOW executes):
```javascript
mcp__azure-devops__wit_update_work_item({
  "id": 1234,
  "updates": [
    { "path": "/fields/Microsoft.VSTS.Scheduling.OriginalEstimate", "value": "8" },
    { "path": "/fields/Microsoft.VSTS.Scheduling.CompletedWork", "value": "6" },
    { "path": "/fields/Microsoft.VSTS.Scheduling.RemainingWork", "value": "0" },
    { "path": "/fields/System.State", "value": "Done" }
  ]
})
```

#### Quick Reference: State Transition Rules

```
┌─────────────────────────────────────────────────────────────────┐
│            TAQATECHNO STATE TRANSITION RULES                     │
├─────────────────────────────────────────────────────────────────┤
│  TASK → Done                                                    │
│  ├── Path: To Do → In Progress → Done → Closed → Removed       │
│  ├── REQUIRES: OriginalEstimate (hours)                         │
│  ├── REQUIRES: CompletedWork (hours)                            │
│  ├── AUTO-SET: RemainingWork = 0                                │
│  └── Done (dev only), Closed (PM only)                          │
├─────────────────────────────────────────────────────────────────┤
│  BUG → Resolved                                                 │
│  ├── Path: New → Approved → In Progress → Resolved → Done       │
│  │         → Closed → Removed                                   │
│  │         └→ Return → In Progress [rejection loop]             │
│  ├── REQUIRES: ResolvedReason (default: "Fixed")                │
│  │   Options: Fixed, As Designed, Cannot Reproduce,             │
│  │            Deferred, Duplicate, Not a Bug, Obsolete          │
│  └── Approved (QA), Resolved (dev), Done (QA), Closed (PM)     │
├─────────────────────────────────────────────────────────────────┤
│  PBI → Done                                                     │
│  ├── Path: New → Approved → Committed → In Progress             │
│  │         → Ready For QC → Done → Removed                      │
│  │         └→ Return → In Progress [rejection loop]             │
│  └── ⚠️ BLOCKED unless current state is "Ready For QC"          │
│      Approved (PM), Committed (PM), In Progress (dev),          │
│      Ready For QC (dev), Done (QA)                              │
├─────────────────────────────────────────────────────────────────┤
│  USER STORY: New → Committed (PM) → Done (PM/QA)               │
├─────────────────────────────────────────────────────────────────┤
│  ENHANCEMENT: New → Committed (PM) → Return (QA) → Done (PM)   │
│               → Closed (PM)                                     │
├─────────────────────────────────────────────────────────────────┤
│  FEATURE / EPIC: New → In Progress (PM) → Done (PM)            │
│                  → Removed (PM)                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 📁 Smart Project Context (AUTOMATIC)

**Reference**: `context/project_context.md` and `data/project_defaults.json`

Claude maintains project context automatically so users don't need to specify project in every query.

```
┌─────────────────────────────────────────────────────────────────┐
│              SMART PROJECT CONTEXT                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  First query: "Show my tasks in Project Alpha"                  │
│    → Sets context: Project Alpha                                │
│                                                                  │
│  Next query: "Show my tasks"                                    │
│    → Uses context automatically: Project Alpha                  │
│                                                                  │
│  Switch: "switch to Project Beta"                                  │
│    → Updates context: Project Beta                                 │
│                                                                  │
│  Override: "bugs in Project Gamma"                        │
│    → One-time query (context unchanged)                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Context Detection (First Use)

```
User: "show my tasks" (no project specified)

IF no context set:
  1. List all projects via core_list_projects
  2. Check user's items in each via wit_my_work_items
  3. Find most active project
  4. INFORM user: "Using Project Alpha (8 active items)"
  5. Set context and proceed
```

#### Context Commands

| Command | Effect |
|---------|--------|
| "switch to Project Beta" | Set new default |
| "use Project Alpha" | Set new default |
| "work on Project Gamma" | Set new default |
| "bugs in Project Beta" | One-time override (default unchanged) |
| "all my tasks across all projects" | Query all, aggregate |
| "what project am I in?" | Show current context |

#### Output Format

Always show current context in responses:

```
📁 Project: Project Alpha

## My Work Items (8)
| ID | Type | Title |
...

💡 Say "switch to [project]" to change
```

#### Available Projects (YOUR-ORG)

| Project | Aliases |
|---------|---------|
| Project Alpha | relief, rc |
| Project Beta | kg |
| Project Gamma | pm, property |
| Project Theta | hr |
| Project Delta | beneshty |
| Project Epsilon | souq |
| Project Zeta | arcelia |
| Project Eta | ittihad |

### 🔗 Repository ID Resolution (AUTOMATIC)

**Reference**: `resolvers/repository_resolver.md` and `data/repository_cache.json`

Azure DevOps APIs require repository **GUIDs** (not names) for PR and branch operations. Claude automatically resolves names to IDs.

```
┌─────────────────────────────────────────────────────────────────┐
│              REPOSITORY RESOLUTION                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User: "Create PR in relief-center-api"                         │
│                                                                  │
│  STEP 1: Is it a GUID?                                          │
│    Pattern: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx                │
│    "relief-center-api" → NOT a GUID, need to resolve            │
│                                                                  │
│  STEP 2: Resolve via API                                        │
│    repo_get_repo_by_name_or_id({                                │
│      project: "Project Alpha",                                  │
│      repositoryNameOrId: "relief-center-api"                    │
│    })                                                           │
│    → Returns: { id: "a1b2c3d4-...", name: "relief-center-api" } │
│                                                                  │
│  STEP 3: Use GUID in API call                                   │
│    repo_create_pull_request({                                   │
│      repositoryId: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"       │
│    })                                                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Resolution Workflow

```
Input: "relief-center-api" or "relief" or "a1b2c3d4-..."

1. Is GUID? → Use directly (bypass resolution)
2. Check session cache → Use cached GUID
3. Direct lookup → repo_get_repo_by_name_or_id
4. List and match → repo_list_repos_by_project + filter
5. Fuzzy match → Partial name matching
6. Not found → Show available repos
```

#### API Tools for Resolution

| Method | Tool | When to Use |
|--------|------|-------------|
| **Direct Lookup** | `repo_get_repo_by_name_or_id` | First attempt (best) |
| **List + Match** | `repo_list_repos_by_project` | If direct fails |

#### Operations Requiring Repository GUID

| Operation | Tool | Needs GUID |
|-----------|------|------------|
| Create PR | `repo_create_pull_request` | ✅ Yes |
| Update PR | `repo_update_pull_request` | ✅ Yes |
| List PRs | `repo_list_pull_requests_by_repo_or_project` | ✅ Yes |
| Create Branch | `repo_create_branch` | ✅ Yes |
| List Branches | `repo_list_branches_by_repo` | ✅ Yes |
| Search Commits | `repo_search_commits` | ✅ Yes |
| Link WI to PR | `wit_link_work_item_to_pull_request` | ✅ Yes |

#### Repository Aliases (YOUR-ORG)

| Project | Repository | Common Aliases |
|---------|------------|----------------|
| Project Alpha | relief-center-api | relief, relief-api, rc-api |
| Project Alpha | relief-center-web | relief-web, rc-web |
| Project Beta | project-beta | khairgate, kg, kg-backend |
| Project Beta | khairgate-frontend | kg-frontend, kg-web |
| Project Gamma | property-management | property, pm |
| Project Theta | taqat-hr | hr, taqat-hr-backend |
| Project Zeta | arcelia | arcelia-crm, crm |
| Project Eta | project-eta | ittihad, club |

#### Example: Create PR with Resolution

**User**: "Create PR from feature/login to main in relief-center-api"

**Claude**:
```
Resolving repository "relief-center-api"...
✅ Resolved: a1b2c3d4-e5f6-7890-abcd-ef1234567890

Creating pull request...
```

```javascript
// Step 1: Resolve repository
const repo = await mcp__azure-devops__repo_get_repo_by_name_or_id({
  "project": "Project Alpha",
  "repositoryNameOrId": "relief-center-api"
});

// Step 2: Create PR with GUID
mcp__azure-devops__repo_create_pull_request({
  "repositoryId": repo.id,  // ← GUID, not name!
  "sourceRefName": "refs/heads/feature/login",
  "targetRefName": "refs/heads/main",
  "title": "Feature: Login implementation"
});
```

#### Error Handling

```
If repository not found:

⚠️ Repository "myrepo" not found in Project Alpha.

Available repositories:
• relief-center-api
• relief-center-web
• relief-center-docs

Please specify the correct repository name.
```

```
If multiple fuzzy matches:

Found multiple repositories matching "relief":
1. relief-center-api
2. relief-center-web

Which repository did you mean?
```

#### Quick Reference

```
┌─────────────────────────────────────────────────────────────────┐
│              REPOSITORY RESOLUTION QUICK REFERENCE              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ALWAYS RESOLVE BEFORE:                                         │
│  • Creating PRs                                                 │
│  • Creating branches                                            │
│  • Listing branches                                             │
│  • Searching commits                                            │
│  • Linking work items to PRs                                    │
│                                                                  │
│  INPUT TYPES:                                                   │
│  • GUID: a1b2c3d4-... → Use directly                            │
│  • Name: relief-center-api → Resolve via API                    │
│  • Alias: relief → Resolve to relief-center-api                 │
│                                                                  │
│  NEVER pass repository NAME to repositoryId parameter!          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 🔗 Work Item Hierarchy Helper (AUTOMATIC)

**Reference**: `helpers/hierarchy_helper.md` and `data/hierarchy_rules.json`

Claude automatically finds or creates parent work items when creating child items, preventing orphan work items.

```
┌─────────────────────────────────────────────────────────────────┐
│              WORK ITEM HIERARCHY                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Epic (Strategic Initiative)                                    │
│    └── Feature (Functional Area)                                │
│          └── User Story / PBI (Requirement)                     │
│                ├── Task (Technical Work)                        │
│                ├── Bug (Defect)                                 │
│                └── Enhancement (Improvement)                    │
│                                                                  │
│  RULES:                                                         │
│  • Bug MUST have parent User Story/PBI                          │
│  • Enhancement MUST have parent User Story/PBI                  │
│  • Task MUST have parent User Story/PBI                         │
│  • User Story SHOULD have parent Feature                        │
│  • Feature SHOULD have parent Epic                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Parent Requirements

| Creating | Required Parent | Requirement Level |
|----------|-----------------|-------------------|
| **Bug** | User Story / PBI | MUST (enforced) |
| **Enhancement** | User Story / PBI | MUST (enforced) |
| **Task** | User Story / PBI | MUST (enforced) |
| User Story | Feature | SHOULD (prompted) |
| Feature | Epic | SHOULD (prompted) |
| Epic | None | - |

#### Parent Detection Workflow

```
User: "Create task: Implement login validation"

STEP 1: Check for explicit parent in message
  Patterns: "under #123", "for story #456", "parent #789"
  → If found, use specified parent

STEP 2: If no parent specified, search for candidates
  Method 1: Keyword search ("login", "validation")
  Method 2: Current sprint items
  Method 3: User's recent activity

STEP 3: Present options to user
  "Found potential parent stories:
   1. #100 - User Authentication Feature
   2. #105 - Login Page Implementation
   Which should this task be under?"

STEP 4: Create and link
  Create task → Link as child of selected parent
```

#### Specifying Parents in Commands

| Pattern | Example |
|---------|---------|
| `under #ID` | "Create task under #123" |
| `for story #ID` | "Create task for story #456" |
| `for story #ID` | "Create bug for story #789" |
| `parent #ID` | "Create bug parent #100" |
| `linked to #ID` | "Create task linked to #200" |

#### Example: Creating Task with Auto-Detection

**User**: "Create task: Implement login form validation"

**Claude**:
```
📁 Project: Project Alpha

No parent specified. Searching for related User Stories...

Found potential parent stories:

| # | ID | Title | State |
|---|-----|-------|-------|
| 1 | #100 | User Authentication Feature | In Progress |
| 2 | #105 | Login Page Implementation | In Progress |

Which User Story should this task be under?
```

**User**: "#100"

**Claude**:
```javascript
// Step 1: Create task
const task = await mcp__azure-devops__wit_create_work_item({
  "project": "Project Alpha",
  "workItemType": "Task",
  "fields": [
    { "name": "System.Title", "value": "Implement login form validation" }
  ]
});

// Step 2: Link to parent
await mcp__azure-devops__wit_work_items_link({
  "project": "Project Alpha",
  "updates": [{
    "id": task.id,
    "linkToId": 100,
    "type": "child"
  }]
});
```

```
✅ Task #150 created: "Implement login form validation"
   └── Parent: User Story #100 - User Authentication Feature

Hierarchy:
Feature #50: Authentication Module
  └── User Story #100: User Authentication Feature
        └── Task #150: Implement login form validation ← NEW
```

#### Error Handling

```
If no parent specified for Bug/Enhancement/Task:

⚠️ Tasks MUST be linked to a User Story.
No parent specified.

Options:
1. Select from existing stories in current sprint
2. Create a new User Story first
3. Specify parent: "under #123"

Which would you like to do?
```

```
If wrong parent type:

⚠️ Cannot create Task under Bug #200.

Tasks can only be children of User Stories or PBIs.
Bug #200 is a Bug, which cannot be a parent of a Task.

Please specify a User Story as the parent.
```

#### Hierarchy Visualization

When displaying work items, show their context:

```
📋 Task #150: Implement login form validation

Hierarchy:
Epic #10: Platform Modernization
  └── Feature #50: Authentication Module
        └── User Story #100: User Authentication Feature
              ├── Task #150: Implement login form validation ← YOU ARE HERE
              ├── Bug #200: Login fails on Safari
              └── Enhancement #210: Improve login form UX

State: In Progress | Sprint: Sprint 15
```

#### Quick Reference

```
┌─────────────────────────────────────────────────────────────────┐
│              HIERARCHY HELPER QUICK REFERENCE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PARENT REQUIREMENTS:                                           │
│  • Bug MUST have parent User Story/PBI                          │
│  • Enhancement MUST have parent User Story/PBI                  │
│  • Task MUST have parent User Story/PBI                         │
│  • User Story SHOULD have parent Feature                        │
│                                                                  │
│  SPECIFY PARENT:                                                │
│  • "Create task under #123"                                     │
│  • "Create bug for story #456"                                  │
│  • "Create enhancement under #789"                              │
│                                                                  │
│  AUTO-DETECTION:                                                │
│  • Keywords from title searched                                 │
│  • Sprint items checked                                         │
│  • Options presented to user                                    │
│                                                                  │
│  NEVER create orphan Tasks, Bugs, or Enhancements!              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 🛡️ Error Recovery System (AUTOMATIC)

**Reference**: `errors/error_recovery.md` and `data/error_patterns.json`

Claude automatically transforms cryptic API errors into actionable user messages with guided recovery workflows.

```
┌─────────────────────────────────────────────────────────────────┐
│              ERROR RECOVERY SYSTEM                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  BEFORE (Frustrating):                                          │
│  "Error: VS403507 - Field cannot be empty"                      │
│                                                                  │
│  AFTER (Actionable):                                            │
│  "To mark Task #1234 as Done, I need:                           │
│   • Original Estimate: ___ hours                                │
│   • Completed Work: ___ hours                                   │
│   Please provide these values."                                 │
│                                                                  │
│  GOAL: Users should NEVER see raw API errors!                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Two-Layer Protection

| Layer | Approach | When Used |
|-------|----------|-----------|
| **1. Proactive Prevention** | Check requirements BEFORE operation | Always (preferred) |
| **2. Reactive Recovery** | Transform errors when they occur | Fallback |

#### Layer 1: Proactive Prevention (PREFERRED)

```
User: "Mark task #1234 as Done"

STEP 1: Pre-flight check
┌────────────────────────────────────────┐
│ Get current work item:                 │
│ wit_get_work_item({ id: 1234 })        │
│                                        │
│ Check required fields:                 │
│ - OriginalEstimate: [empty] ❌         │
│ - CompletedWork: [empty] ❌            │
└────────────────────────────────────────┘

STEP 2: Ask BEFORE attempting
┌────────────────────────────────────────┐
│ "Task #1234 needs these fields to be   │
│  marked as Done:                       │
│                                        │
│ • Original Estimate (hours): ___       │
│ • Completed Work (hours): ___          │
│                                        │
│ Please provide the values."            │
└────────────────────────────────────────┘

STEP 3: Update with all fields
→ SUCCESS - No error encountered!
```

#### Layer 2: Reactive Recovery (FALLBACK)

When errors occur despite prevention, transform them:

```
Error: VS403507 - Field 'OriginalEstimate' cannot be empty

RECOVERY:
┌────────────────────────────────────────────────────────────────┐
│ ❌ Cannot mark task as Done                                     │
│                                                                │
│ **Missing Required Field**:                                    │
│ • Original Estimate (hours)                                    │
│                                                                │
│ **To fix**: Tell me how many hours you estimated for this task.│
└────────────────────────────────────────────────────────────────┘
```

#### Error Pattern Catalog

| Error Code | User Message | Recovery Action |
|------------|--------------|-----------------|
| `VS403507` | "Task needs {field} to be marked {state}" | Ask for field value |
| `TF401347` | "{Type} must go through {intermediate} before {target}" | Offer two-step transition |
| `TF401019` | "Work item #{id} not found" | Suggest searching |
| `VS403403` | "Permission denied. Token missing '{scope}' scope." | Show required scopes |
| `TF401398` | "Branch '{branch}' not found" | List available branches |
| `VS403323` | "Update conflict - someone else modified this" | Refresh and retry |
| `VS403513` | "'{value}' is not valid for {field}" | Show valid values |
| `TF401028` | "Source and target branches cannot be the same" | Ask for different branch |
| `VS403406` | "PR has merge conflicts" | Show conflict details |

#### Recovery Workflow Examples

**Required Field Missing:**
```
Error: VS403507 - CompletedWork cannot be empty

Claude Response:
┌────────────────────────────────────────────────────────────────┐
│ ❌ Cannot mark Task #1234 as Done                               │
│                                                                │
│ **Reason**: Required fields are missing                        │
│                                                                │
│ **Missing Fields**:                                            │
│ • Original Estimate (hours): [not set]                         │
│ • Completed Work (hours): [not set]                            │
│                                                                │
│ **Quick Fix Options**:                                         │
│ 1. Tell me the hours: "8 hours estimated, 6 hours actual"      │
│ 2. Same hours for both: "8 hours"                              │
│                                                                │
│ I'll update all fields and mark as Done in one step.           │
└────────────────────────────────────────────────────────────────┘
```

**Invalid State Transition:**
```
Error: TF401347 - Invalid state transition from 'In Progress' to 'Done'

Claude Response:
┌────────────────────────────────────────────────────────────────┐
│ ⚠️ Cannot move PBI #1000 directly to Done                       │
│                                                                │
│ **Reason**: PBIs must pass through Ready For QC                │
│                                                                │
│ **Required Path**:                                             │
│ In Progress → Ready For QC → Done                              │
│                                                                │
│ **Options**:                                                   │
│ 1. Move to "Ready For QC" first (recommended)                  │
│ 2. Move through both states now                                │
│                                                                │
│ Which would you like to do?                                    │
└────────────────────────────────────────────────────────────────┘
```

**Permission Denied:**
```
Error: VS403403 - Access denied

Claude Response:
┌────────────────────────────────────────────────────────────────┐
│ 🔒 Permission Denied                                            │
│                                                                │
│ **Operation**: Update work item #1234                          │
│ **Reason**: PAT missing required permissions                   │
│                                                                │
│ **Required Scopes**:                                           │
│ • vso.work_write (Work Items - Read, write, & manage)          │
│                                                                │
│ **How to Fix**:                                                │
│ 1. Go to Azure DevOps → User Settings → Personal Access Tokens │
│ 2. Edit your token and enable required scope                   │
│ 3. Update your Claude Code settings                            │
└────────────────────────────────────────────────────────────────┘
```

**Resource Not Found:**
```
Error: TF401398 - Branch 'feature/login' does not exist

Claude Response:
┌────────────────────────────────────────────────────────────────┐
│ 🔍 Branch Not Found                                             │
│                                                                │
│ **Looking for**: feature/login                                 │
│ **Repository**: relief-center-api                              │
│                                                                │
│ **Similar branches found**:                                    │
│ • feature/login-page                                           │
│ • feature/user-login                                           │
│ • feature/login-api                                            │
│                                                                │
│ **Options**:                                                   │
│ 1. Use one of the similar branches above                       │
│ 2. Create new branch "feature/login"                           │
│ 3. List all branches                                           │
└────────────────────────────────────────────────────────────────┘
```

#### Error Message Emoji Guide

| Emoji | Meaning | Use Case |
|-------|---------|----------|
| ❌ | Error/Blocked | Operation failed |
| ⚠️ | Warning | Partial success or caution |
| 🔒 | Permission | Access denied |
| 🔍 | Not Found | Resource missing |
| ⏳ | Timeout | Operation took too long |
| 🔄 | Conflict | Update conflict |
| ✅ | Success | Recovery successful |

#### Pre-Flight Validation Checklist

Before executing operations, validate to prevent errors:

| Operation | Pre-Flight Checks |
|-----------|-------------------|
| **Task → Done** | OriginalEstimate set? CompletedWork set? Role is dev? |
| **Bug → Approved** | Role is QA? |
| **Bug → Resolved** | ResolvedReason selected? Role is dev? |
| **Bug → Done** | Role is QA? |
| **Bug → Closed** | Role is PM? |
| **PBI → Done** | Current state is "Ready For QC"? Role is QA? |
| **PBI → Return** | Role is QA? Rejection reason provided? |
| **Enhancement → Done** | Role is PM/QA? |
| **Enhancement → Closed** | Role is PM? |
| **Create PR** | Source branch exists? Target branch exists? Different branches? |
| **Link to PR** | Repository GUID resolved? PR exists? |
| **Create Task** | Parent User Story/PBI specified? |
| **Create Bug** | Parent User Story/PBI specified? |
| **Create Enhancement** | Parent User Story/PBI specified? |

#### Quick Reference

```
┌─────────────────────────────────────────────────────────────────┐
│              ERROR RECOVERY QUICK REFERENCE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  COMMON ERRORS & QUICK FIXES:                                   │
│                                                                  │
│  "Field cannot be empty" (VS403507)                             │
│  → Ask user for the required field value                        │
│  → Update all fields in single call                             │
│                                                                  │
│  "Invalid state transition" (TF401347)                          │
│  → Show required intermediate states (see TaqaTechno states)    │
│  → Offer to do multi-step transition                            │
│                                                                  │
│  "Not found" (TF401019)                                         │
│  → Check for typos                                              │
│  → Search for similar items                                     │
│  → Check project scope                                          │
│                                                                  │
│  "Permission denied" (VS403403)                                 │
│  → List required PAT scopes                                     │
│  → Provide setup instructions                                   │
│                                                                  │
│  PREVENTION IS BETTER THAN RECOVERY:                            │
│  • Always pre-fetch work item before updating                   │
│  • Check required fields before state change                    │
│  • Validate branches before PR creation                         │
│  • Resolve repository names before API calls                    │
│                                                                  │
│  NEVER show raw API errors to users!                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

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
| **Enhancement** | Improvements | Title, Description (Current/Proposed/Benefit) |
| **Issue** | Blockers | Title, Description, Resolution |
| **Test Case** | Test scenarios | Title, Steps, Expected Results |

## Work Item Hierarchy Rules

### MANDATORY: Enforce This Hierarchy

```
Epic (Strategic Initiative)
  └── Feature (Functional Area)
        └── User Story / PBI (Requirement)
              ├── Task (Technical Work)
              ├── Bug (Defect)
              └── Enhancement (Improvement)
```

### Creation Rules

| Creating | Must Have Parent | Parent Type |
|----------|-----------------|-------------|
| **Bug** | **REQUIRED** | User Story/PBI |
| **Enhancement** | **REQUIRED** | User Story/PBI |
| **Task** | **REQUIRED** | User Story/PBI |
| **User Story/PBI** | REQUIRED | Feature |
| **Feature** | REQUIRED | Epic |
| **Epic** | None | Top-level |

### Bug & Enhancement Hierarchy Rule

**Bugs and Enhancements MUST be linked to a User Story/PBI** - This ensures:
- Traceability: Know which requirement the bug or enhancement relates to
- Context: Bug/Enhancement is tied to a specific user-facing requirement
- Visibility: PBI owner and team see all related work items as siblings

```
User Story #100: "Add login feature"
  ├── Task #101: "Implement login form"
  ├── Bug #102: "Login button not responding" ← Bug under User Story
  └── Enhancement #103: "Improve login form UX" ← Enhancement under User Story
```

### Validation Before Creation

Before creating a work item, ALWAYS:

1. **For Bug**:
   - Ask: "Which User Story or PBI is this bug related to?"
   - If no parent User Story/PBI specified, prompt user to:
     a) Select existing User Story/PBI
     b) Create new User Story/PBI first
   - NEVER create orphan bugs - they must be under a User Story/PBI

2. **For Enhancement**:
   - Ask: "Which User Story or PBI should this enhancement be under?"
   - If no parent specified, prompt user to:
     a) Select existing User Story/PBI
     b) Create new User Story/PBI first
   - NEVER create orphan enhancements - they must be under a User Story/PBI

3. **For Task**:
   - Ask: "Which User Story or PBI should this task be under?"
   - If no parent specified, prompt user to:
     a) Select existing PBI
     b) Create new PBI first
   - NEVER create orphan tasks

4. **For User Story/PBI**:
   - Ask: "Which Feature should this story be under?"
   - If no Feature exists, prompt to create one
   - If no Feature specified, list available Features

5. **For Feature**:
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
1. Ask: "Which User Story or PBI should this task be under?"
2. User provides parent ID or creates new PBI
3. Create task
4. Link task to parent
5. Confirm: "Task #1234 created under PBI #1000"
```

### Example Workflow: Creating a Bug

```
User: "Create bug: Login button not responding"

Claude:
1. Ask: "Which User Story or PBI is this bug related to?"
2. User provides User Story/PBI ID (e.g., #1000)
3. Create bug with details
4. Link bug to parent User Story/PBI
5. Confirm: "Bug #1235 created under User Story #1000"

If user doesn't know the User Story/PBI:
1. Ask: "What feature/area is this bug related to?"
2. Search for related User Stories/PBIs
3. Present options: "Found these stories in that area:
   - User Story #1000: Add login feature
   - User Story #1001: User authentication flow
   Which one is related to this bug?"
```

### Example Workflow: Creating an Enhancement

```
User: "Create enhancement: Improve login form validation UX"

Claude:
1. Ask: "Which User Story or PBI should this enhancement be under?"
2. User provides User Story/PBI ID (e.g., #1000)
3. Create enhancement with details
4. Link enhancement to parent User Story/PBI
5. Confirm: "Enhancement #1236 created under User Story #1000"
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

## ⚠️ REQUIRED FIELDS VALIDATION (CRITICAL)

### MANDATORY: Validate Before Create/Update

**NEVER create or update a work item without checking required fields!**

Before ANY `wit_create_work_item` or `wit_update_work_item` call:
1. Check what fields are REQUIRED for the operation
2. If required fields are missing, **ASK THE USER** - don't skip or guess!
3. Only proceed when all required fields have values

### Required Fields by Work Item Type

#### Task Creation
| Field | Required | Description |
|-------|----------|-------------|
| `System.Title` | **REQUIRED** | Task title |
| `System.Description` | Recommended | Task description |
| `Microsoft.VSTS.Scheduling.OriginalEstimate` | **REQUIRED for Done** | Estimated hours |
| `Microsoft.VSTS.Scheduling.CompletedWork` | **REQUIRED for Done** | Actual hours spent |
| `Microsoft.VSTS.Scheduling.RemainingWork` | Recommended | Hours remaining |
| Parent Link | **REQUIRED** | Must link to User Story/PBI |

#### Bug Creation
| Field | Required | Description |
|-------|----------|-------------|
| `System.Title` | **REQUIRED** | Bug title |
| `System.Description` | Recommended | Bug description |
| `Microsoft.VSTS.TCM.ReproSteps` | Recommended | Steps to reproduce |
| `Microsoft.VSTS.Common.Severity` | Recommended | 1-Critical, 2-High, 3-Medium, 4-Low |
| `Microsoft.VSTS.Common.Priority` | Recommended | 1-4 (1=highest) |
| Parent Link | **REQUIRED** | Must link to a Task |

#### User Story / PBI Creation
| Field | Required | Description |
|-------|----------|-------------|
| `System.Title` | **REQUIRED** | Story title |
| `System.Description` | **REQUIRED** | Story description (What/How/Why) |
| `Microsoft.VSTS.Common.AcceptanceCriteria` | **REQUIRED** | Done criteria |
| `Microsoft.VSTS.Scheduling.StoryPoints` | Recommended | Effort estimate |
| Parent Link | **REQUIRED** | Must link to Feature |

### State Transition Rules

#### Task State Transitions

```
┌────────┐     ┌─────────────┐     ┌──────┐     ┌────────┐     ┌─────────┐
│ To Do  │ ──► │ In Progress │ ──► │ Done │ ──► │ Closed │ ──► │ Removed │
└────────┘     └─────────────┘     └──────┘     └────────┘     └─────────┘
                                     ▲
                                     │ REQUIRES:
                                     │ - Original Estimate
                                     │ - Completed Work
```

| From State | To State | Required Fields | Ask User If Missing | Role |
|------------|----------|-----------------|---------------------|------|
| To Do | In Progress | None | - | any |
| In Progress | Done | `OriginalEstimate`, `CompletedWork` | **YES - ALWAYS ASK!** | dev |
| To Do | Done | `OriginalEstimate`, `CompletedWork` | **YES - ALWAYS ASK!** | dev |
| Done | Closed | None | - | PM only |
| Any | Removed | None | - | PM only |

**Example Validation for Task → Done:**
```
User: "Set task #1234 to Done"

Claude MUST:
1. Check statePermissions from profile:
   - If user role is PM → BLOCKED (only devs can move Task to Done)
   - Show: "Your role (PM) cannot move Tasks to Done. Only developers can."

2. Get current work item details:
   mcp__azure-devops__wit_get_work_item({
     "project": "ProjectName",
     "id": 1234,
     "fields": ["System.State", "Microsoft.VSTS.Scheduling.OriginalEstimate",
                "Microsoft.VSTS.Scheduling.CompletedWork"]
   })

3. Check current state is "In Progress" (not "To Do" — must be In Progress first)

4. Check if OriginalEstimate and CompletedWork have values

5. IF MISSING - ASK USER:
   "To mark task #1234 as Done, I need:
   - Original Estimate (hours): [currently not set]
   - Completed Work (hours): [currently not set]

   Please provide these values."

6. ONLY after user provides values, make the update:
   mcp__azure-devops__wit_update_work_item({
     "id": 1234,
     "updates": [
       {"path": "/fields/Microsoft.VSTS.Scheduling.OriginalEstimate", "value": "8"},
       {"path": "/fields/Microsoft.VSTS.Scheduling.CompletedWork", "value": "6"},
       {"path": "/fields/System.State", "value": "Done"}
     ]
   })
```

#### Bug State Transitions

```
┌──────┐     ┌──────────┐     ┌─────────────┐     ┌──────────┐     ┌──────┐     ┌───────────┐     ┌──────┐     ┌────────┐     ┌─────────┐
│ New  │ ──► │ Approved │ ──► │ In Progress │ ──► │ Resolved │ ──► │ Done │ ──► │ Committed │ ──► │ Done │ ──► │ Closed │ ──► │ Removed │
└──────┘     └──────────┘     └─────────────┘     └──────────┘     └──────┘     └───────────┘     └──────┘     └────────┘     └─────────┘
                                     ▲                                │
                                     │          ┌────────┐            │
                                     └──────────│ Return │◄───────────┘
                                                └────────┘
                                              [rejection loop]
```

Full Bug path: New → Approved → In Progress → Resolved → Return → Committed → Done → Closed → Removed

| From State | To State | Required Fields | Ask User If Missing | Role |
|------------|----------|-----------------|---------------------|------|
| New | Approved | None | - | QA |
| Approved | In Progress | None | - | dev |
| In Progress | Resolved | `Microsoft.VSTS.Common.ResolvedReason` | **YES** | dev |
| Resolved | Return | Rejection reason | **YES** | QA |
| Return | In Progress | None | - | dev |
| Resolved | Done | None | - | QA |
| Done | Closed | None | - | PM |
| Any | Removed | None | - | PM |

#### User Story State Transitions

```
┌──────┐     ┌───────────┐     ┌──────┐
│ New  │ ──► │ Committed │ ──► │ Done │
└──────┘     └───────────┘     └──────┘
```

| From State | To State | Required/Recommended | Ask User If Missing | Role |
|------------|----------|---------------------|---------------------|------|
| New | Committed | None | - | PM |
| Committed | Done | All child PBIs must be Done | **WARN if PBIs incomplete** | PM/QA |

#### PBI (Product Backlog Item) State Transitions

```
┌──────┐     ┌──────────┐     ┌───────────┐     ┌─────────────┐     ┌───────────────┐     ┌──────┐     ┌─────────┐
│ New  │ ──► │ Approved │ ──► │ Committed │ ──► │ In Progress │ ──► │ Ready For QC  │ ──► │ Done │ ──► │ Removed │
└──────┘     └──────────┘     └───────────┘     └─────────────┘     └───────────────┘     └──────┘     └─────────┘
                                                        ▲                   │
                                                        │     ┌────────┐    │
                                                        └─────│ Return │◄───┘
                                                              └────────┘
                                                            [rejection loop]
```

| From State | To State | Required/Recommended | Ask User If Missing | Role |
|------------|----------|---------------------|---------------------|------|
| New | Approved | None | - | PM |
| Approved | Committed | None | - | PM |
| Committed | In Progress | None | - | dev |
| In Progress | Ready For QC | All child Tasks must be Done | **WARN if tasks incomplete** | dev |
| Ready For QC | Done | Acceptance Criteria verified | **ASK for confirmation** | QA |
| Ready For QC | Return | Rejection reason | **YES** | QA |
| Return | In Progress | None | - | dev |
| **In Progress** | **Done** | **NOT ALLOWED DIRECTLY** | **ENFORCE Ready For QC first** | - |
| **New/Approved/Committed** | **Done** | **NOT ALLOWED DIRECTLY** | **ENFORCE Ready For QC first** | - |
| Any | Removed | None | - | PM |

#### Enhancement State Transitions

```
┌──────┐     ┌───────────┐     ┌────────┐     ┌──────┐     ┌────────┐
│ New  │ ──► │ Committed │ ──► │ Return │ ──► │ Done │ ──► │ Closed │
└──────┘     └───────────┘     └────────┘     └──────┘     └────────┘
```

| From State | To State | Required/Recommended | Ask User If Missing | Role |
|------------|----------|---------------------|---------------------|------|
| New | Committed | None | - | PM |
| Committed | Return | Rejection reason | **YES** | QA |
| Committed | Done | None | - | PM/QA |
| Return | Done | None | - | PM/QA |
| Done | Closed | None | - | PM |

#### Feature / Epic State Transitions

```
┌──────┐     ┌─────────────┐     ┌──────┐     ┌─────────┐
│ New  │ ──► │ In Progress │ ──► │ Done │ ──► │ Removed │
└──────┘     └─────────────┘     └──────┘     └─────────┘
```

| From State | To State | Required/Recommended | Ask User If Missing | Role |
|------------|----------|---------------------|---------------------|------|
| New | In Progress | None | - | PM |
| In Progress | Done | All child items should be Done | **WARN if children incomplete** | PM |
| Any | Removed | None | - | PM |

### CRITICAL RULE: PBI → Done Requires Ready For QC

**MANDATORY**: PBIs CANNOT transition directly to "Done" from any state other than "Ready For QC"!

```
PBI State Machine (ENFORCED):

┌──────────────────────────────────────────────────────────────────────────────────┐
│                         PBI STATE TRANSITIONS                                     │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  New → Approved → Committed → In Progress → Ready For QC → Done → Removed        │
│                                      ▲            │                               │
│                                      └── Return ◄─┘  [rejection loop]            │
│                                                                                   │
│  ⚠️ MANDATORY QC CHECKPOINT: Cannot skip Ready For QC to reach Done!             │
│                                                                                   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

**Why This Rule Exists:**
- Ensures QA review before completion
- Forces explicit quality checkpoint
- Prevents accidental completion without testing
- Maintains proper workflow discipline

**Example Validation for PBI → Done:**
```
User: "Set PBI #1000 to Done"

Claude MUST:
1. Check statePermissions from profile:
   - If user role is dev → BLOCKED (only QA can move PBI to Done)
   - Show: "Your role (developer) cannot move PBIs to Done. Only QA can."

2. Get current work item details:
   mcp__azure-devops__wit_get_work_item({
     "project": "ProjectName",
     "id": 1000,
     "fields": ["System.State", "System.WorkItemType"]
   })

3. Check current state:
   - If state is "Ready For QC" → Proceed to Done (QA role required)
   - If state is NOT "Ready For QC" → MUST transition through intermediate states first

4. IF NOT "Ready For QC" - ENFORCE INTERMEDIATE STATES:
   "⚠️ PBI #1000 is currently in '{currentState}' state.

   Before marking as Done, it must pass through 'Ready For QC' for quality review.

   Required path: {currentState} → ... → Ready For QC → Done

   Shall I:
   1. Move it to 'Ready For QC' now (you can then mark it Done after QA review)
   2. Move it through all intermediate states now?

   Please confirm the approach."

5. If user confirms option 2 (all transitions):
   // Walk through each required intermediate state
   // e.g., if currently "In Progress":
   await mcp__azure-devops__wit_update_work_item({
     "id": 1000,
     "updates": [
       {"path": "/fields/System.State", "value": "Ready For QC"}
     ]
   });

   await mcp__azure-devops__wit_update_work_item({
     "id": 1000,
     "updates": [
       {"path": "/fields/System.State", "value": "Done"}
     ]
   });

6. Confirm to user:
   "PBI #1000 has been moved:
    - From: {originalState}
    - Through: Ready For QC (QA checkpoint)
    - To: Done

    The PBI passed through the required QA checkpoint."
```

**Quick Reference - PBI State Rule:**

| Current State | User Wants "Done" | Action Required |
|---------------|------------------|-----------------|
| New | Block | Transition: New → Approved → Committed → In Progress → Ready For QC → Done |
| Approved | Block | Transition: Approved → Committed → In Progress → Ready For QC → Done |
| Committed | Block | Transition: Committed → In Progress → Ready For QC → Done |
| In Progress | Block | Transition: In Progress → Ready For QC → Done |
| Ready For QC | Allow | Direct transition to Done (QA role only) |
| Done | N/A | Already Done |
| Return | Block | Transition: Return → In Progress → Ready For QC → Done |

### Pre-Update Validation Workflow

**ALWAYS follow this workflow before updating work items:**

```
┌─────────────────────────────────────────────────────────────┐
│                    USER REQUEST                             │
│         "Update task #1234 to Done"                         │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 1: Fetch Current Work Item                            │
│  - Get current state                                         │
│  - Get all relevant fields                                   │
│  - Check work item type                                      │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 2: Determine Required Fields                           │
│  - Based on work item type                                   │
│  - Based on state transition (from → to)                     │
│  - Check organization-specific rules                         │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  STEP 3: Check If Required Fields Have Values                │
│  - OriginalEstimate set? CompletedWork set?                  │
│  - Parent linked? Description filled?                        │
└─────────────────────────────────────────────────────────────┘
                          │
              ┌───────────┴───────────┐
              │                       │
              ▼                       ▼
    ┌─────────────────┐     ┌─────────────────────────┐
    │ ALL FIELDS SET  │     │ MISSING REQUIRED FIELDS │
    │                 │     │                         │
    │ Proceed with    │     │ ASK USER for values     │
    │ update          │     │ before proceeding       │
    └─────────────────┘     └─────────────────────────┘
                                      │
                                      ▼
                          ┌─────────────────────────┐
                          │ User provides values    │
                          │ OR cancels operation    │
                          └─────────────────────────┘
                                      │
                                      ▼
                          ┌─────────────────────────┐
                          │ Make update with ALL    │
                          │ fields in single call   │
                          └─────────────────────────┘
```

### Common Field Paths Reference

| Field Name | API Path | Type |
|------------|----------|------|
| Title | `/fields/System.Title` | string |
| Description | `/fields/System.Description` | html |
| State | `/fields/System.State` | string |
| Assigned To | `/fields/System.AssignedTo` | identity |
| Original Estimate | `/fields/Microsoft.VSTS.Scheduling.OriginalEstimate` | double (hours) |
| Completed Work | `/fields/Microsoft.VSTS.Scheduling.CompletedWork` | double (hours) |
| Remaining Work | `/fields/Microsoft.VSTS.Scheduling.RemainingWork` | double (hours) |
| Story Points | `/fields/Microsoft.VSTS.Scheduling.StoryPoints` | double |
| Priority | `/fields/Microsoft.VSTS.Common.Priority` | integer (1-4) |
| Severity | `/fields/Microsoft.VSTS.Common.Severity` | string |
| Acceptance Criteria | `/fields/Microsoft.VSTS.Common.AcceptanceCriteria` | html |
| Repro Steps | `/fields/Microsoft.VSTS.TCM.ReproSteps` | html |
| Iteration Path | `/fields/System.IterationPath` | string |
| Area Path | `/fields/System.AreaPath` | string |

### Example: Complete Task Update with Validation

```javascript
// User: "Mark task #1234 as done, I spent 6 hours on it"

// Step 1: Get current state
const item = await mcp__azure-devops__wit_get_work_item({
  "project": "Project Alpha",
  "id": 1234,
  "fields": [
    "System.State",
    "System.Title",
    "Microsoft.VSTS.Scheduling.OriginalEstimate",
    "Microsoft.VSTS.Scheduling.CompletedWork"
  ]
});

// Step 2: Check required fields
// Current: OriginalEstimate = null, CompletedWork = null, State = "In Progress"

// Step 3: User provided CompletedWork (6), but OriginalEstimate missing
// ASK: "What was the original estimate for this task?"
// User: "8 hours"

// Step 4: Update with ALL required fields
await mcp__azure-devops__wit_update_work_item({
  "id": 1234,
  "updates": [
    {"path": "/fields/Microsoft.VSTS.Scheduling.OriginalEstimate", "value": "8"},
    {"path": "/fields/Microsoft.VSTS.Scheduling.CompletedWork", "value": "6"},
    {"path": "/fields/Microsoft.VSTS.Scheduling.RemainingWork", "value": "0"},
    {"path": "/fields/System.State", "value": "Done"}
  ]
});

// Step 5: Confirm to user
// "Task #1234 marked as Done. Original estimate: 8h, Completed: 6h"
```

### Validation Error Messages

When required fields are missing, provide CLEAR guidance:

**Good Response:**
```
❌ Cannot mark task #1234 as Done - missing required fields:

| Field | Current Value | Required |
|-------|--------------|----------|
| Original Estimate | (not set) | ✗ Required |
| Completed Work | (not set) | ✗ Required |

Please provide:
1. Original Estimate (hours): How many hours did you estimate for this task?
2. Completed Work (hours): How many hours did you actually spend?
```

**Bad Response:**
```
// DON'T DO THIS - Don't silently skip required fields!
"Task updated to Done"  // ← Will fail or corrupt data!
```

## Response Formatting

When presenting Azure DevOps data, use consistent formatting:

### Work Items
```
[Bug] #1234: Fix login button not responding
   State: In Progress | Priority: 2 | Severity: 2
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

### Common API Errors

| Error Code | Cause | Solution |
|------------|-------|----------|
| 401 | Unauthorized | PAT expired - regenerate token |
| 403 | Forbidden | Insufficient permissions - check PAT scopes |
| 404 | Not Found | Invalid ID - verify project/item exists |
| VS403507 | Field validation | **Check required fields - see below** |
| TF401019 | Item not found | Work item may be deleted |
| TF401320 | Invalid field value | Check field type and format |
| TF401347 | State transition invalid | Check allowed state transitions |

### Field Validation Errors (VS403507)

**This error means required fields are missing!** Don't ignore it - ask the user for values.

**Common Causes:**
1. **Task → Done without hours**: Missing `OriginalEstimate` or `CompletedWork`
2. **PBI without criteria**: Missing `AcceptanceCriteria`
3. **Work item without parent**: Required by organization policy

**How to Handle:**
```
ERROR: VS403507 - Field 'Microsoft.VSTS.Scheduling.CompletedWork'
       cannot be empty when state is 'Done'

CORRECT RESPONSE:
"I cannot mark this task as Done because the Completed Work field is required.
How many hours did you spend on this task?"

WRONG RESPONSE:
"Failed to update task" // ← Don't just report error, help user fix it!
```

### Validation Quick Reference

| When User Says | Check Before Proceeding |
|----------------|------------------------|
| "Mark task as done" | OriginalEstimate, CompletedWork, role is dev |
| "Approve this bug" | Role is QA |
| "Resolve this bug" | ResolvedReason, role is dev |
| "Close this bug" | Role is PM, bug must be in Done state |
| "Create a bug" | **Parent User Story/PBI specified** |
| "Create a task" | Parent User Story/PBI specified |
| "Create user story" | AcceptanceCriteria, Description, Parent Feature |
| **"Mark PBI as done"** | **Current state MUST be "Ready For QC" - enforce intermediate state! Role must be QA** |
| **"Set PBI to done"** | **If not "Ready For QC", transition through intermediate states first** |
| "Return this PBI" | Role is QA, rejection reason provided |
| "Close enhancement" | Role is PM |

### Proactive Validation Example

```javascript
// ALWAYS do this BEFORE attempting state change:
async function validateTaskDone(project, taskId) {
  const item = await wit_get_work_item({
    project,
    id: taskId,
    fields: [
      "System.State",
      "System.WorkItemType",
      "Microsoft.VSTS.Scheduling.OriginalEstimate",
      "Microsoft.VSTS.Scheduling.CompletedWork"
    ]
  });

  const missing = [];
  if (!item.OriginalEstimate) missing.push("Original Estimate (hours)");
  if (!item.CompletedWork) missing.push("Completed Work (hours)");

  if (missing.length > 0) {
    // ASK USER - don't proceed!
    return {
      valid: false,
      message: `To mark this task as Done, please provide:\n${missing.map(f => `- ${f}`).join('\n')}`
    };
  }

  return { valid: true };
}
```

## Best Practices

1. **ALWAYS validate required fields before updates** ⚠️
   - Fetch current work item state before updating
   - Check if required fields have values
   - ASK USER for missing values - never skip or guess!
   - See "Required Fields Validation" section above

2. **Always start with context**
   - List projects first if unsure
   - Verify project name before operations

3. **Use appropriate work item types**
   - Bug for defects
   - Task for technical work
   - User Story for requirements

4. **Link related items**
   - Link bugs to user stories
   - Link tasks to parent stories
   - Link PRs to work items

5. **Include all required fields on creation**
   - Title (always required)
   - Description (highly recommended)
   - Priority/Severity (for bugs)
   - Acceptance Criteria (for stories)
   - **OriginalEstimate** (for tasks you expect to close)

6. **Validate state transitions (TaqaTechno states)**
   - Task: To Do → In Progress → Done (dev) → Closed (PM)
   - Bug: New → Approved (QA) → In Progress (dev) → Resolved (dev) → Done (QA) → Closed (PM)
   - PBI: New → Approved (PM) → Committed → In Progress → Ready For QC → Done (QA)
   - Check user role permissions from statePermissions before any transition
   - Task → Done: Needs OriginalEstimate + CompletedWork
   - Bug → Resolved: Needs ResolvedReason
   - PBI → Done: Must be in Ready For QC first, check all child tasks are Done

7. **Use WIQL for complex queries**
   - More powerful than simple filters
   - Supports date math (@Today - 7)
   - Supports hierarchy (UNDER)

8. **Monitor builds proactively**
   - Check build status after PR merge
   - Get logs for failed builds
   - Link build failures to bugs

## Integration Notes

This skill works with **BOTH** Azure DevOps CLI and MCP server in hybrid mode.

### Configuration Files

| Resource | Path | Purpose |
|----------|------|---------|
| MCP Settings | `C:\Users\ahmed\.claude\settings.json` | MCP server config |
| Claude Guide | `C:\TQ-WorkSpace\odoo\AZURE_DEVOPS_MCP_CLAUDE_GUIDE.md` | Developer reference |
| User Guide | `C:\TQ-WorkSpace\odoo\AZURE_DEVOPS_USER_GUIDE.md` | End-user documentation |
| Hybrid Routing | `hybrid_routing.md` | CLI vs MCP decision guide |
| Plugin Config | `plugin.json` | Plugin metadata (v2.0.0) |

### Predefined References

Claude loads these references for intelligent routing and best practices:

| Reference File | Purpose |
|-------------|---------|
| `references/cli_best_practices.md` | CLI command patterns and tips |
| `references/mcp_best_practices.md` | MCP tool usage patterns |
| `references/automation_templates.md` | Reusable PowerShell/Bash/Python scripts |
| `references/wiql_queries.md` | 40+ WIQL query templates |
| `references/team_workflows.md` | organization-specific workflows |

### Available Commands (v4.0)

| Command | Type | Description |
|---------|------|-------------|
| `/init` | Hybrid | Install CLI, configure MCP, check status |
| `/workday` | Hybrid | Daily dashboard with auto-sync, time log, compliance |
| `/create` | MCP | Create work item (task, bug, story) with auto-detection |
| `/log-time` | Local | Log hours against work items or categories |
| `/timesheet` | Local | View time tracking, manage time-off |
| `/standup` | MCP | Generate daily standup notes |
| `/sprint` | Hybrid | Sprint summary (use --full for comprehensive report) |
| `/task-monitor` | MCP | Periodic new assignment alerts (use with /loop) |
| `/cli-run` | CLI | Execute any CLI command (includes vars & extensions recipes) |

### Authentication

**CLI Authentication**:
```bash
# Set PAT environment variable
export AZURE_DEVOPS_EXT_PAT="your-pat-token"

# Configure defaults
az devops configure --defaults organization=https://dev.azure.com/YOUR-ORG
```

**MCP Authentication**:
- PAT stored in `ADO_PAT_TOKEN` environment variable
- Server configured in Claude Code settings

---

## Skill-Handled Workflows

The following workflows are handled directly by this skill through natural language detection. They do not require slash commands — the skill detects intent and executes the appropriate workflow.

For full instructions, see `devops/workflows.md`.

| Workflow | Trigger Patterns | Guards |
|----------|-----------------|--------|
| **Update Work Item** | "mark #ID as done", "resolve bug #ID", "close #ID" | write_operation_guard, state_transition_validator |
| **Add Comment** | "comment on #ID", "tell @name about #ID" | write_operation_guard, mention_processor |
| **Switch Project** | "switch to PROJECT", "use PROJECT", "work on PROJECT" | (none — read-only) |
| **Build Status** | "any failing builds?", "check CI", "pipeline health" | (none — read-only) |
| **Create PR** | "create PR from BRANCH to BRANCH", "open pull request" | write_operation_guard, repository_resolver |
| **CI/CD Setup** | "set up CI/CD", "generate GitHub Actions" | write_operation_guard |

**Previously**: These were standalone commands (`/update-workitem`, `/add-comment`, `/switch-project`, `/build-status`, `/create-pr`, `/ci-setup`). They are now triggered contextually through natural language.

---

### Version Information

- **Skill Version**: 3.0.0 (Hybrid Mode + Skill-Handled Workflows)
- **CLI Version Required**: Azure CLI 2.30.0+ with azure-devops extension
- **MCP Server**: @anthropic-ai/azure-devops-mcp (Official Anthropic)

The hybrid architecture provides optimal performance by routing tasks to CLI or MCP based on task characteristics, combining CLI's scripting power with MCP's natural language convenience.
