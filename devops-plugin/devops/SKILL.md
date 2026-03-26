---
name: devops
description: |
  Azure DevOps HYBRID integration skill for your Azure DevOps organization. Combines CLI power with MCP convenience for optimal performance. Uses CLI for automation, batch operations, variables, and extensions. Uses MCP for interactive queries, code reviews, test plans, search, and security alerts. Intelligent routing automatically selects the best tool for each task.

  <example>
  Context: User wants to create a work item in Azure DevOps
  user: "Create a user story for the login feature"
  assistant: "I will use the devops skill to create a User Story with title, description, and acceptance criteria under the correct epic."
  <commentary>Core trigger - work item creation.</commentary>
  </example>

  <example>
  Context: User wants to view their sprint tasks
  user: "Show me my active sprint tasks"
  assistant: "I will use the devops skill to query the current sprint, filter by assigned user, and display a task board with status."
  <commentary>Sprint query trigger.</commentary>
  </example>

  <example>
  Context: User wants to update a work item state
  user: "Mark task #1234 as done, I spent 6 hours on it"
  assistant: "I will validate the state transition, check required fields, and update the work item with pre-flight validation."
  <commentary>State change trigger - with validation.</commentary>
  </example>

  <example>
  Context: User wants to add a comment with mentions
  user: "Comment on #1234 telling @mahmoud to review this"
  assistant: "I will resolve the @mention to a GUID, format as HTML, and post the comment."
  <commentary>Comment trigger - mention resolution.</commentary>
  </example>

  <example>
  Context: User wants to create a pull request
  user: "Create a PR from feature/login to main"
  assistant: "I will resolve the repository to a GUID, validate branches, and create the pull request."
  <commentary>PR creation trigger.</commentary>
  </example>
license: "MIT"
metadata:
  version: "6.3.0"
  author: "TAQAT Techno"
  allowed-tools: "Read, Write, Bash, WebFetch, Glob, Grep"
  organization: "YOUR-ORG"
  mode: "hybrid"
  mcp-server: "@anthropic-ai/azure-devops-mcp"
  cli-extension: "azure-devops"
  tools-count: "100+ MCP tools + full CLI"
---

# Azure DevOps Integration Skill (v6.0 - Hybrid Mode)

## Configuration

- **Organization**: YOUR-ORG
- **Mode**: HYBRID (CLI + MCP)
- **MCP Server**: `@anthropic-ai/azure-devops-mcp`
- **CLI Extension**: `azure-devops` (via Azure CLI 2.30.0+)
- **Auth CLI**: `AZURE_DEVOPS_EXT_PAT` env var
- **Auth MCP**: `ADO_PAT_TOKEN` env var
- **Tools**: 100+ MCP tools + full CLI
- **MCP Failures**: If MCP server is unavailable, see `devops/MCP_FAILURE_MODES.md` for recovery and CLI fallback matrix.

---

## STEP 0: LOAD USER PROFILE

Before any DevOps operation, load `~/.claude/devops.md`. See `rules/profile-loader.md` for the full loading workflow, lookup tables, and cache-first resolution pattern.

---

## Rules & Guards (Single Source of Truth)

All behavioral enforcement lives in `rules/`. Do NOT re-implement — follow the references:

| Concern | Owner | Reference |
|---------|-------|-----------|
| Write confirmation gate | `rules/write-gate.md` | Gather → present → confirm → execute. Plan Mode = read only. |
| Tool selection (`wit_my_work_items` vs `search_workitem`) | `rules/guards.md` Guard 1 | Decision table + auto-correction. |
| Mention resolution (@name → GUID → HTML) | `rules/guards.md` Guard 2 | Checklist before posting comments. |
| Repository name → GUID resolution | `rules/guards.md` Guard 3 | Required before all PR/branch operations. |
| State transitions & role permissions | `data/state_machine.json` | Pre-flight: check role → fetch item → check required fields → ask if missing → confirm → execute. |
| Work item hierarchy enforcement | `data/hierarchy_rules.json` | Epic > Feature > Story > Task/Bug/Enhancement. Tasks/Bugs MUST have parent. |
| Business rules (naming, bug authority, sprint) | `data/state_machine.json` `businessRules` | Task prefixes, QA-only bugs, user story format, auto-sprint. |
| Error recovery patterns | `data/state_machine.json` (`errorPatterns`) | Single source of truth for all error codes → recovery actions. |
| Profile loading & project context | `rules/profile-loader.md` | Cache-first resolution, context persistence. |

---

## Hybrid Mode: CLI + MCP Routing

### Decision Matrix

| Task Type | CLI | MCP | Reason |
|-----------|:---:|:---:|--------|
| Batch work item updates | Y | | CLI scripting faster |
| Single work item query | | Y | MCP more convenient |
| Create multiple items | Y | | CLI parallel execution |
| PR code review threads | | Y | MCP dedicated tools |
| Create service connections | Y | | CLI only |
| Install extensions | Y | | CLI only |
| Manage pipeline variables | Y | | CLI only |
| Run pipelines | Y | Y | CLI better for CI/CD |
| Test plan management | | Y | MCP only |
| Security alerts | | Y | MCP only |
| Search code/wiki | | Y | MCP only |
| Create projects | Y | | CLI only |
| Daily standup / sprint | | Y | MCP queries sufficient |
| Automated scripts | Y | | CLI scriptable |
| Team capacity | | Y | MCP only |

### CLI-Only Features

| Feature | Command |
|---------|---------|
| Create project | `az devops project create` |
| Create repository | `az repos create` |
| Variable groups | `az pipelines variable-group` |
| Pipeline variables | `az pipelines variable` |
| Service connections | `az devops service-endpoint` |
| Extensions | `az devops extension install` |
| Create pipeline | `az pipelines create` |

### MCP-Only Features

| Feature | Tool |
|---------|------|
| Test plans/cases/results | `testplan_*` |
| Code/wiki/work item search | `search_*` |
| Security alerts | `advsec_*` |
| PR threads & comments | `repo_*_thread*`, `repo_reply_*`, `repo_resolve_*` |
| Team capacity | `work_get/update_team_capacity` |
| Batch work item update | `wit_update_work_items_batch` |

---

## Skill-Handled Workflows

These workflows trigger via natural language. They replace former standalone commands.

### Workflow 1: Update Work Item
**Triggers**: "mark #ID as done", "resolve bug #ID", "close #ID", "move #ID to [state]"
**Steps**: Follow `data/state_machine.json` pre-flight (role → fetch → required fields → ask → confirm → execute) → offer time logging
**Dev-Internal-fix check**: If completing a `[Dev-Internal-fix]` Task, verify QC was notified; ask if fix changes user-facing behavior

### Workflow 2: Add Comment
**Triggers**: "comment on #ID", "tell @name about #ID", "add note to #ID"
**Steps**: Follow `rules/guards.md` Guard 2 (extract → resolve → validate → HTML → confirm → post)

### Workflow 3: Switch Project
**Triggers**: "switch to PROJECT", "use PROJECT", "work on PROJECT"
**Steps**: Resolve alias from `data/project_defaults.json` → validate → update session context per `rules/profile-loader.md`

### Workflow 4: Build Status
**Triggers**: "build status", "any failing builds?", "check CI", "pipeline health"
**Steps**: List recent builds (last 10) -> show status/duration -> highlight failures -> provide quick actions

### Workflow 5: Create PR
**Triggers**: "create PR from BRANCH to BRANCH", "open pull request"
**Steps**: Parse request → resolve repo per `rules/guards.md` Guard 3 → validate branches → confirm per `rules/write-gate.md` → create → offer reviewers/linking

### Workflow 6: CI/CD Setup
**Triggers**: "set up CI/CD", "generate GitHub Actions", "create pipeline"
**Steps**: Determine target (Odoo.sh vs self-hosted) -> gather info -> generate workflow files -> confirm -> save
  - Odoo.sh: 2 files (quality-gate.yml, odoo_tests.cfg)
  - Self-hosted: 4 files (lint, test, deploy-staging, deploy-production)
  - Optional ntfy.sh notification step
  - Confirm per `rules/write-gate.md` before saving

### Workflow 7: Log Time
**Triggers**: "spent 3h on #1401", "logged 2 hours on #ID", "mark 1h", "time: 4h #ID"
**Steps**: Parse hours + ID → fetch via `wit_get_work_item` → calculate new CompletedWork (existing + hours) → update RemainingWork → confirm per `rules/write-gate.md` → execute via `wit_update_work_item`
**Without #ID**: Log to local timesheet by category (meeting, research, learning, review, admin)
**Shortcut**: `/log-time` command

### Workflow 8: Daily Standup
**Triggers**: "prepare my standup", "standup notes", "what did I do yesterday?", "generate standup"
**Steps**: Load profile → query yesterday's completed items → query today's active items → detect blockers → format as Yesterday/Today/Blockers
**Shortcut**: `/standup` command

### Workflow 9: Monitor Assignments
**Triggers**: "check for new assignments", "any new tasks for me?", "assignment changes"
**Steps**: Load snapshot from session → query `wit_my_work_items` → diff new/changed/removed → report → save snapshot
**For periodic monitoring**: Use `/loop 15m /task-monitor`
**Shortcut**: `/task-monitor` command

---

## Available Commands

| Command | Type | Description |
|---------|------|-------------|
| `/init` | Hybrid | Install CLI, configure MCP, generate profile |
| `/workday` | Hybrid | Daily dashboard with auto-sync, time log |
| `/create` | MCP | Create work item with auto-detection |
| `/log-time` | Local | Log hours against work items (also Workflow 7) |
| `/timesheet` | Local | View time tracking, manage time-off |
| `/standup` | MCP | Generate daily standup notes (also Workflow 8) |
| `/sprint` | Hybrid | Sprint summary (--full for comprehensive) |
| `/task-monitor` | MCP | Periodic new assignment alerts (also Workflow 9) |
| `/cli-run` | CLI | Execute any CLI command |

---

## Quick Reference

### Response Formatting

```
[Bug] #1234: Fix login button not responding
   State: In Progress | Priority: 2 | Severity: 2
   Assigned: Ahmed | Sprint: Sprint 15
```
```
PR #45: Add user authentication
   Author: Ahmed | Status: Active
   Reviewers: 2/3 approved | Comments: 5
```
```
Build #789: CI-Main
   Status: Succeeded | Duration: 5m 23s
   Trigger: PR merge | Branch: main
```

### Work Item Fields

| Field | Description |
|-------|-------------|
| `System.Id` | Work item ID |
| `System.Title` | Title |
| `System.State` | Current state |
| `System.WorkItemType` | Type (Bug, Task, etc.) |
| `System.AssignedTo` | Assigned user |
| `System.CreatedDate` | Creation date |
| `System.ChangedDate` | Last modified date |
| `System.AreaPath` | Area path |
| `System.IterationPath` | Iteration/Sprint |
| `System.Tags` | Tags |
| `Microsoft.VSTS.Common.Priority` | Priority (1-4) |
| `Microsoft.VSTS.Common.Severity` | Severity (1-4) |
| `Microsoft.VSTS.Scheduling.StoryPoints` | Story points |
| `Microsoft.VSTS.Scheduling.OriginalEstimate` | Original estimate (hours) |
| `Microsoft.VSTS.Scheduling.RemainingWork` | Remaining work (hours) |
| `Microsoft.VSTS.Scheduling.CompletedWork` | Completed work (hours) |

### WIQL Quick Reference

**Syntax:**
```sql
SELECT [Field1], [Field2]
FROM WorkItems
WHERE [Condition]
ORDER BY [Field]
```

**Macros:** `@Me` (current user), `@Today` (today), `@CurrentIteration` (current sprint), `@Project` (current project)

**Common Queries:**

My active items:
```sql
SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType]
FROM WorkItems
WHERE [System.AssignedTo] = @Me
  AND [System.State] <> 'Closed' AND [System.State] <> 'Removed'
ORDER BY [System.ChangedDate] DESC
```

Current sprint items:
```sql
SELECT [System.Id], [System.Title], [System.State], [System.AssignedTo]
FROM WorkItems
WHERE [System.IterationPath] = @CurrentIteration
  AND [System.State] NOT IN ('Done', 'Closed', 'Removed')
ORDER BY [Microsoft.VSTS.Common.Priority] ASC
```

Completed yesterday (standup):
```sql
SELECT [System.Id], [System.Title], [System.WorkItemType]
FROM WorkItems
WHERE [System.AssignedTo] = @Me AND [System.State] = 'Done'
  AND [System.ChangedDate] >= @Today-1 AND [System.ChangedDate] < @Today
```

Active bugs:
```sql
SELECT [System.Id], [System.Title], [System.State], [Microsoft.VSTS.Common.Priority]
FROM WorkItems
WHERE [System.WorkItemType] = 'Bug'
  AND [System.State] IN ('New', 'Active', 'In Progress')
ORDER BY [Microsoft.VSTS.Common.Priority] ASC
```

### API Limits

- **Rate Limit**: 200 requests per minute per user
- **Batch Size**: Max 200 work items per request
- **Query Results**: Max 20,000 results
- **Attachment Size**: Max 130 MB
- **Comment Length**: Max 1 MB

For real-world workflow examples, see `devops/EXAMPLES.md`.

---

## Per-Project Configuration

The plugin ships with `.local.md.template` at the plugin root. To override organization or project defaults per-machine:

1. Copy to `~/.claude/devops-plugin.local.md`
2. Fill in your organization name, default project, and team
3. Run `/init profile` to auto-populate `~/.claude/devops.md` with team members, GUIDs, and state permissions

The `.local.md` file is gitignored and never committed. It provides machine-local overrides that supplement the shared plugin configuration.

**What it configures:**
- Organization name and URL (overrides `data/project_defaults.json`)
- Default project and team (overrides profile `defaultProject`)
- PAT environment variable name

**Example profile:** See `data/example_profile.md` for a realistic example of what `/init profile` generates.

For full setup including CLI installation and MCP configuration, run `/init`.

