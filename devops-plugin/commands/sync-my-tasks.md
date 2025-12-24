---
title: 'Sync My Tasks'
read_only: false
type: 'command'
description: 'Sync Azure DevOps tasks to Claude Code TODO list'
---

# Sync My Tasks

Synchronize Azure DevOps work items assigned to you with Claude Code's TODO list.

## What This Command Does

1. **Fetches** work items from Azure DevOps assigned to current user
2. **Detects** project(s) from working directory or user input
3. **Adds/Updates** items in Claude Code TODO list using TodoWrite tool
4. **Reports** sync summary with added/updated items

## Usage

```
/sync-my-tasks                           # Auto-detect project from git remote
/sync-my-tasks Relief Center             # Sync from specific project
/sync-my-tasks Relief Center, Property   # Sync from multiple projects
/sync-my-tasks --all                     # Sync from all accessible projects
```

## Workflow

### Step 1: Detect/Select Projects

**Method 1: Git Remote Detection**
```bash
# Check git remote for Azure DevOps project
git remote -v
# Look for: dev.azure.com/TaqaTechno/PROJECT_NAME
```

**Method 2: User Input**
- If no git remote found, ask: "Which project(s) should I sync tasks from?"
- List available projects if needed

**Method 3: All Projects**
```
mcp__azure-devops__core_list_projects()
```

### Step 2: Query Work Items

For each project:
```
mcp__azure-devops__wit_my_work_items({
  "project": "ProjectName",
  "type": "assignedtome",
  "includeCompleted": false,
  "top": 50
})
```

### Step 3: Transform to TODO Format

**Azure DevOps State → TODO Status Mapping:**

| Azure DevOps State | TODO Status |
|-------------------|-------------|
| New, To Do | pending |
| Active, In Progress | in_progress |
| Done, Closed, Resolved | completed |
| Removed | (skip - don't add) |

**TODO Format:**
```json
{
  "content": "#1234 [Task] Fix login bug - https://dev.azure.com/TaqaTechno/Project/_workitems/edit/1234",
  "status": "in_progress",
  "activeForm": "Fixing login bug (#1234)"
}
```

### Step 4: Smart Update Logic

1. **Read existing TODOs** (if any)
2. **Match by work item ID** - Look for `#1234` pattern in content
3. **For existing items**: Update status if changed
4. **For new items**: Add to TODO list
5. **Preserve non-DevOps TODOs** - Don't remove manually added items

### Step 5: Use TodoWrite Tool

```
TodoWrite({
  "todos": [
    // Existing non-DevOps todos (preserved)
    {"content": "Manual todo item", "status": "pending", "activeForm": "Working on manual item"},

    // Synced Azure DevOps items
    {"content": "#1234 [Task] Fix login bug - Relief Center", "status": "in_progress", "activeForm": "Fixing login bug (#1234)"},
    {"content": "#1235 [Bug] UI alignment issue - Relief Center", "status": "pending", "activeForm": "Fixing UI alignment (#1235)"},
    {"content": "#1236 [PBI] Add dark mode - Property Management", "status": "pending", "activeForm": "Implementing dark mode (#1236)"}
  ]
})
```

### Step 6: Report Results

```markdown
## Tasks Synced

### Added (3)
- #1234 [Task] Fix login bug - Relief Center
- #1235 [Bug] UI alignment issue - Relief Center
- #1236 [PBI] Add dark mode - Property Management

### Updated (2)
- #1230 [Task] New → In Progress
- #1231 [Bug] In Progress → Done (moved to completed)

### Removed (1)
- #1229 [Task] Removed from Azure DevOps

### Summary
| Project | Items |
|---------|-------|
| Relief Center | 5 |
| Property Management | 3 |
| **Total** | **8** |
```

## Detection Patterns

### Git Remote URL Patterns
```
https://dev.azure.com/TaqaTechno/PROJECT_NAME/_git/REPO
git@ssh.dev.azure.com:v3/TaqaTechno/PROJECT_NAME/REPO
https://TaqaTechno@dev.azure.com/TaqaTechno/PROJECT_NAME/_git/REPO
```

### Odoo Project Detection
For Odoo projects, check config file:
```
# Check for .conf file with project name
# e.g., conf/relief_center17.conf → Relief Center project
```

## Multi-Project Support

When syncing from multiple projects:
- Include project name in TODO content
- Group report by project
- Handle project-specific work item types

## Example Session

**User**: `/sync-my-tasks`

**Claude**:
```
Detecting project from git remote...
Found: Relief Center

Fetching work items assigned to you...
Found 5 items:
- 3 Tasks (2 Active, 1 New)
- 2 Bugs (1 Active, 1 New)

Updating TODO list...

## Tasks Synced

### Added (5)
| ID | Type | Title | State |
|----|------|-------|-------|
| #1636 | Bug | Broken Checksum Validation | Active |
| #1629 | Bug | SQL Injection in Email | New |
| #1828 | Task | Investigate map duration | Active |
| #1829 | Task | Convert subscription form | New |
| #1830 | Task | Add rate limiting | New |

Your TODO list has been updated with 5 Azure DevOps items.
```

## Configuration (Optional)

Create `~/.claude/devops-sync-config.json`:
```json
{
  "defaultProjects": ["Relief Center", "Property Management"],
  "excludeTypes": ["Test Case"],
  "excludeStates": ["Removed", "Closed"],
  "maxItems": 50,
  "includeUrl": true
}
```

## Best Practices

1. **Run at session start** - Keep TODO list in sync with DevOps
2. **Use project filters** - Don't sync from all projects if unnecessary
3. **Check for updates** - Re-run periodically to catch state changes
4. **Manual items preserved** - Your non-DevOps TODOs won't be affected

## Related Commands

- `/my-tasks` - View Azure DevOps tasks (read-only, no TODO sync)
- `/standup` - Generate standup notes from recent activity
- `/sprint` - View sprint progress
