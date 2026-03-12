# Write Operation Guard

## CRITICAL RULE — NEVER EXECUTE WITHOUT CONFIRMATION

This guard enforces a mandatory **present → confirm → execute** gate for ALL operations that create, update, or delete resources in Azure DevOps. No write operation may proceed without explicit user approval.

---

## The Rule

Before calling ANY write MCP tool or CLI command listed below, you **MUST**:

1. **Gather** all required information (title, parent, sprint, fields, etc.)
2. **Investigate** — use READ operations freely to validate parents, sprints, fields
3. **Present** a confirmation summary showing exactly what will be created/modified
4. **Wait** for explicit user approval ("yes", "go ahead", "create it", "do it", "proceed")
5. **Only then** execute the write operation

**If the user has NOT explicitly approved**: DO NOT call the write tool. Present the summary again or ask for clarification.

**In Plan Mode**: NEVER execute write operations under any circumstances. Only describe what would be created. You may use READ tools to investigate and validate, but calling any write tool during Plan Mode is strictly forbidden.

---

## Classified Operations

### CREATE — Require Confirmation (HIGH risk)

| MCP Tool / CLI Command | What It Does |
|------------------------|-------------|
| `mcp__azure-devops__wit_create_work_item` | Creates Bug, Task, User Story, PBI, Feature, Epic |
| `mcp__azure-devops__wit_work_items_link` | Links work items in hierarchy (child/parent/related) |
| `mcp__azure-devops__wit_add_work_item_comment` | Posts a comment visible to the entire team |
| `mcp__azure-devops__repo_create_pull_request` | Creates a pull request in a repository |
| `az pipelines variable-group create` | Creates a pipeline variable group |
| `az devops extension install` | Installs a marketplace extension org-wide |

### UPDATE — Require Confirmation (MEDIUM-HIGH risk)

| MCP Tool / CLI Command | What It Does |
|------------------------|-------------|
| `mcp__azure-devops__wit_update_work_item` | Changes state, fields, assignments on a work item |
| `az pipelines variable-group update` | Modifies pipeline variables |
| `az devops extension uninstall` | Removes a marketplace extension |

### DELETE — Require Confirmation (HIGHEST risk)

| MCP Tool / CLI Command | What It Does |
|------------------------|-------------|
| `az pipelines variable-group delete` | Deletes a variable group permanently |
| Any destructive CLI command | Permanent data loss |

### READ — No Confirmation Needed (safe)

All query/read operations can be executed freely without confirmation:
- `wit_get_work_item`, `wit_get_work_items_batch_by_ids`
- `wit_my_work_items`, `search_workitem`
- `wit_get_work_items_for_iteration`, `wit_get_query_results_by_id`
- `work_list_team_iterations`, `core_get_identity_ids`
- `repo_list_repositories`, `repo_get_pull_request`
- `az boards query --wiql "..."` (read-only queries)
- Any `list`, `show`, `get`, `search` operation

---

## Confirmation Summary Templates

Always present a boxed summary before executing. Use the appropriate template:

### Work Item Creation

```
┌─────────────────────────────────────────────┐
│  READY TO CREATE: {WorkItemType}            │
├─────────────────────────────────────────────┤
│  Title:     {title}                         │
│  Type:      {Bug/Task/User Story/PBI/etc}   │
│  Project:   {project}                       │
│  Parent:    #{parentId} - {parentTitle}      │
│  Sprint:    {iterationPath}                 │
│  Assigned:  {assignedTo or "Unassigned"}    │
│  Estimate:  {hours}h                        │
│  Priority:  {priority}                      │
│  Severity:  {severity} (bugs only)          │
├─────────────────────────────────────────────┤
│  Proceed? (yes/no)                          │
└─────────────────────────────────────────────┘
```

Only show fields that have values. Omit empty/unset fields.

### Work Item State Change

```
┌─────────────────────────────────────────────┐
│  READY TO UPDATE: #{id} {title}             │
├─────────────────────────────────────────────┤
│  State:     {currentState} → {newState}     │
│  Fields:    {list of fields being set}      │
│  Hours:     Est: {orig}h / Done: {comp}h    │
├─────────────────────────────────────────────┤
│  Proceed? (yes/no)                          │
└─────────────────────────────────────────────┘
```

### Work Item Field Update (no state change)

```
┌─────────────────────────────────────────────┐
│  READY TO UPDATE: #{id} {title}             │
├─────────────────────────────────────────────┤
│  Changes:                                   │
│    {field1}: {oldValue} → {newValue}        │
│    {field2}: {oldValue} → {newValue}        │
├─────────────────────────────────────────────┤
│  Proceed? (yes/no)                          │
└─────────────────────────────────────────────┘
```

### Pull Request Creation

```
┌─────────────────────────────────────────────┐
│  READY TO CREATE: Pull Request              │
├─────────────────────────────────────────────┤
│  Title:     {prTitle}                       │
│  Source:    {sourceBranch}                   │
│  Target:    {targetBranch}                   │
│  Repo:      {repository}                    │
│  Reviewers: {reviewers or "None"}           │
│  Work Items: {linked work item IDs}         │
├─────────────────────────────────────────────┤
│  Proceed? (yes/no)                          │
└─────────────────────────────────────────────┘
```

### Comment Addition

```
┌─────────────────────────────────────────────┐
│  READY TO ADD COMMENT: #{workItemId}        │
├─────────────────────────────────────────────┤
│  Target:    #{id} - {workItemTitle}         │
│  Content:   {first 150 chars of comment}... │
│  Mentions:  {resolved @mentions or "None"}  │
├─────────────────────────────────────────────┤
│  Proceed? (yes/no)                          │
└─────────────────────────────────────────────┘
```

### Work Item Linking

```
┌─────────────────────────────────────────────┐
│  READY TO LINK: Work Items                  │
├─────────────────────────────────────────────┤
│  Child:     #{childId} - {childTitle}       │
│  Parent:    #{parentId} - {parentTitle}     │
│  Link Type: {child/parent/related}          │
├─────────────────────────────────────────────┤
│  Proceed? (yes/no)                          │
└─────────────────────────────────────────────┘
```

### Infrastructure Change (Pipeline Vars / Extensions)

```
┌─────────────────────────────────────────────┐
│  READY TO {CREATE/UPDATE/DELETE}: {resource} │
├─────────────────────────────────────────────┤
│  Resource:  {variable group / extension}    │
│  Name:      {name}                          │
│  Action:    {create/update/delete}          │
│  Details:   {key details}                   │
├─────────────────────────────────────────────┤
│  ⚠️  This affects shared infrastructure     │
│  Proceed? (yes/no)                          │
└─────────────────────────────────────────────┘
```

---

## Batch Operations

When the user asks to create multiple items at once (e.g., "create 3 tasks for story #100"):

1. Gather info for ALL items first
2. Present a SINGLE combined summary listing all items
3. Wait for ONE confirmation covering all items
4. Execute all writes only after approval

```
┌─────────────────────────────────────────────┐
│  READY TO CREATE: 3 Tasks                   │
├─────────────────────────────────────────────┤
│  1. [DEV] Implement login API               │
│  2. [FRONT] Create login form               │
│  3. [QA] Test login flow                    │
│                                             │
│  Parent:  #100 - User Authentication        │
│  Sprint:  Sprint 16                         │
│  Project: Project Alpha                     │
├─────────────────────────────────────────────┤
│  Create all 3? (yes/no)                     │
└─────────────────────────────────────────────┘
```

---

## What Counts as User Approval

**Explicit approval** (proceed):
- "yes", "y", "go", "go ahead", "create it", "do it", "proceed", "ok", "confirm", "approved"

**Explicit rejection** (stop):
- "no", "n", "stop", "cancel", "wait", "hold on", "not yet", "change..."

**Ambiguous** (ask again):
- If the user's response is unclear, ask: "Should I proceed with creating this? (yes/no)"

---

## Integration Points

This guard is referenced by:
1. **`devops/SKILL.md`** — Top-level mandatory section
2. **All write commands** — Each command references this guard before its execution step
3. **`guards/tool_selection_guard.md`** — Complements the read-side guard

---

*Write Operation Guard v1.0*
*Part of DevOps Plugin v3.1*
