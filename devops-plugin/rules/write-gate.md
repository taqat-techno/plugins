# Write Operation Gate

## CRITICAL RULE: NEVER EXECUTE WITHOUT CONFIRMATION

Before calling ANY write MCP tool or CLI command, you **MUST**:

1. **Gather** all required information (title, parent, sprint, fields, etc.)
2. **Investigate** freely using READ operations (queries, fetches, searches)
3. **Present** a confirmation summary showing exactly what will be created/modified
4. **Wait** for explicit user approval ("yes", "go ahead", "create it", "do it", "proceed")
5. **Only then** execute the write operation

**In Plan Mode**: NEVER execute write operations. Only describe what would be created.

**NO EXCEPTIONS.** Even if the user says "create task X" in one sentence — present the summary first.

---

## Classified Operations

### CREATE (HIGH risk) — Require Confirmation

| Tool / Command | What It Does |
|----------------|-------------|
| `wit_create_work_item` | Creates Bug, Task, User Story, PBI, Feature, Epic |
| `wit_work_items_link` | Links work items in hierarchy |
| `wit_add_work_item_comment` | Posts a comment visible to the entire team |
| `repo_create_pull_request` | Creates a pull request |
| `az pipelines variable-group create` | Creates a pipeline variable group |
| `az devops extension install` | Installs a marketplace extension org-wide |

### UPDATE (MEDIUM-HIGH risk) — Require Confirmation

| Tool / Command | What It Does |
|----------------|-------------|
| `wit_update_work_item` | Changes state, fields, assignments |
| `az pipelines variable-group update` | Modifies pipeline variables |
| `az devops extension uninstall` | Removes a marketplace extension |

### DELETE (HIGHEST risk) — Require Confirmation

| Tool / Command | What It Does |
|----------------|-------------|
| `az pipelines variable-group delete` | Deletes a variable group permanently |

### READ (safe) — No Confirmation Needed

All `list`, `show`, `get`, `search`, `query` operations execute freely.

---

## Confirmation Summary Templates

### Work Item Creation

```
READY TO CREATE: {WorkItemType}
----------------------------------
Title:     {title}
Type:      {type}
Project:   {project}
Parent:    #{parentId} - {parentTitle}
Sprint:    {iterationPath}
Assigned:  {assignedTo or "Unassigned"}
Estimate:  {hours}h
Priority:  {priority}

Proceed? (yes/no)
```

### Work Item State Change

```
READY TO UPDATE: #{id} {title}
----------------------------------
State:     {currentState} -> {newState}
Fields:    {list of fields being set}
Hours:     Est: {orig}h / Done: {comp}h

Proceed? (yes/no)
```

### Pull Request Creation

```
READY TO CREATE: Pull Request
------------------------------
Title:     {prTitle}
Source:    {sourceBranch}
Target:    {targetBranch}
Repo:      {repository}
Reviewers: {reviewers or "None"}
Work Items: {linked IDs}

Proceed? (yes/no)
```

### Comment Addition

```
READY TO ADD COMMENT: #{workItemId}
------------------------------------
Target:    #{id} - {workItemTitle}
Content:   {first 150 chars}...
Mentions:  {resolved @mentions or "None"}

Proceed? (yes/no)
```

### Batch Operations

Present a SINGLE combined summary listing all items, wait for ONE confirmation.

---

## What Counts as User Approval

**Approve**: "yes", "y", "go", "go ahead", "create it", "do it", "proceed", "ok", "confirm"
**Reject**: "no", "n", "stop", "cancel", "wait", "hold on", "not yet"
**Ambiguous**: Ask again — "Should I proceed? (yes/no)"
