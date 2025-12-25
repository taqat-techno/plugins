# Tool Selection Guard

## Purpose

This guard **PREVENTS** wrong tool selection before execution. It transforms confusing tool choices into correct ones, eliminating the #1 cause of user frustration.

**Problem Solved**: Users say "show my tasks" and get 0 results because `search_workitem` was used instead of `wit_my_work_items`.

---

## MANDATORY: Before Using Any MCP Work Item Tool

### Decision Tree: Query Operations

```
User wants to see work items?
    │
    ├─► "My tasks" / "assigned to me" / "my work items"?
    │       │
    │       └─► USE: wit_my_work_items ✅
    │           NEVER: search_workitem ❌
    │           WHY: search_workitem is TEXT SEARCH only
    │
    ├─► "Search for [text] in work items" / "find items containing [keyword]"?
    │       │
    │       └─► USE: search_workitem ✅
    │           (Searches title, description, comments for text)
    │
    ├─► "Work items by filter" (state=Active, type=Bug, iteration=Sprint1)?
    │       │
    │       ├─► Simple filter (my items + state)?
    │       │       └─► USE: wit_my_work_items + client filter ✅
    │       │
    │       └─► Complex filter (any combination)?
    │               └─► USE: CLI az boards query --wiql ✅
    │               └─► OR: wit_get_query_results_by_id (saved query) ✅
    │
    ├─► "Specific work item #123"?
    │       │
    │       └─► USE: wit_get_work_item ✅
    │
    ├─► "Multiple items #1, #2, #3"?
    │       │
    │       └─► USE: wit_get_work_items_batch_by_ids ✅
    │
    └─► "Items in current sprint" / "sprint backlog"?
            │
            └─► USE: wit_get_work_items_for_iteration ✅
```

---

## CRITICAL WARNING TABLE

### Tool Selection Matrix

| User Request | WRONG Tool | CORRECT Tool | Why Wrong Tool Fails |
|--------------|------------|--------------|---------------------|
| "my tasks" | `search_workitem` | `wit_my_work_items` | search is TEXT SEARCH, ignores AssignedTo |
| "assigned to me" | `search_workitem` | `wit_my_work_items` | search ignores filter params |
| "active bugs" | `search_workitem` | CLI WIQL or `wit_my_work_items` | search ignores State filter |
| "sprint items" | `search_workitem` | `wit_get_work_items_for_iteration` | search ignores Iteration filter |
| "work items for @mahmoud" | `search_workitem` | WIQL query | search cannot filter by AssignedTo |
| "bugs in Ready for QC" | `search_workitem` | WIQL query | search cannot filter by State |

---

## Tool Behavior Reference

### `search_workitem` - TEXT SEARCH ONLY

**What it does**: Searches for TEXT inside work item titles, descriptions, and comments.

**What it DOES NOT do**:
- ❌ Filter by AssignedTo
- ❌ Filter by State
- ❌ Filter by Iteration
- ❌ Filter by WorkItemType (as primary filter)
- ❌ Return "my" work items

**Correct usage**:
```javascript
// Find items containing "login" in text
mcp__azure-devops__search_workitem({
  "searchText": "login authentication",  // ← Searches this TEXT
  "project": ["Relief Center"]           // ← Limits to project
})
```

**WRONG usage** (returns 0 results):
```javascript
// WRONG - These filters are IGNORED!
mcp__azure-devops__search_workitem({
  "searchText": "*",
  "assignedTo": ["@Me"],      // ❌ IGNORED - not a search filter
  "state": ["Active"],        // ❌ IGNORED - not a search filter
  "workItemType": ["Task"]    // ❌ IGNORED as filter
})
```

### `wit_my_work_items` - ASSIGNED TO ME QUERY

**What it does**: Returns work items assigned to the current user.

**Parameters**:
```javascript
mcp__azure-devops__wit_my_work_items({
  "project": "Relief Center",     // REQUIRED - project scope
  "type": "assignedtome",         // "assignedtome" or "myactivity"
  "includeCompleted": false,      // Include Done/Closed items?
  "top": 50                       // Max items to return
})
```

**Returns**: Work item IDs. Use `wit_get_work_items_batch_by_ids` for full details.

### `wit_get_work_items_for_iteration` - SPRINT ITEMS

**What it does**: Returns all work items in a specific sprint/iteration.

**Parameters**:
```javascript
mcp__azure-devops__wit_get_work_items_for_iteration({
  "project": "Relief Center",
  "iterationId": "Sprint 15",    // Iteration name or GUID
  "team": "Relief Center Team"   // Optional team scope
})
```

### CLI WIQL Query - COMPLEX FILTERS

**When to use**: Any filter combination not supported by MCP tools.

```bash
az boards query --wiql "
  SELECT [System.Id], [System.Title], [System.State]
  FROM WorkItems
  WHERE [System.TeamProject] = 'Relief Center'
    AND [System.AssignedTo] = 'mahmoud@email.com'
    AND [System.State] = 'Active'
    AND [System.WorkItemType] = 'Bug'
  ORDER BY [System.ChangedDate] DESC
" --output json
```

---

## Auto-Correction Rules

### Rule 1: Detect Intent Mismatch

Before executing `search_workitem`, check if intent is actually "find my items":

```
TRIGGER PHRASES for wit_my_work_items:
- "my tasks"
- "my work items"
- "assigned to me"
- "my bugs"
- "my stories"
- "show what I'm working on"
- "what's on my plate"
- "my current work"

If detected AND tool is search_workitem:
  → BLOCK and REDIRECT to wit_my_work_items
```

### Rule 2: Validate Filter Parameters

Before executing `search_workitem` with filter-like parameters:

```
CHECK: Does search_workitem call include:
  - assignedTo?
  - state?
  - iteration?

If ANY present:
  → WARN: "search_workitem ignores these filters"
  → SUGGEST: Use wit_my_work_items or CLI WIQL
  → DO NOT EXECUTE search_workitem with filters
```

### Rule 3: Empty searchText Detection

```
CHECK: Is searchText = "*" or empty/wildcard?

If YES AND has filter params:
  → This is NOT a text search, it's a filtered query
  → REDIRECT to wit_my_work_items or WIQL
```

---

## Execution Guard Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    TOOL SELECTION GUARD                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  STEP 1: Analyze User Request                                   │
│  ┌───────────────────────────────────────────────────────┐      │
│  │ Extract: intent, filters, text search terms           │      │
│  │ Example: "show my active tasks"                       │      │
│  │   → intent: "my work items"                           │      │
│  │   → filters: [state=Active, type=Task]                │      │
│  │   → text: none                                        │      │
│  └───────────────────────────────────────────────────────┘      │
│                                                                  │
│  STEP 2: Match Intent to Correct Tool                           │
│  ┌───────────────────────────────────────────────────────┐      │
│  │ "my work items" → wit_my_work_items ✅                │      │
│  │ "search [text]" → search_workitem ✅                  │      │
│  │ "sprint items"  → wit_get_work_items_for_iteration ✅ │      │
│  │ "item #123"     → wit_get_work_item ✅                │      │
│  └───────────────────────────────────────────────────────┘      │
│                                                                  │
│  STEP 3: Validate Before Execution                              │
│  ┌───────────────────────────────────────────────────────┐      │
│  │ IF intended_tool == search_workitem:                  │      │
│  │   IF has_filter_params OR intent == "my items":       │      │
│  │     → BLOCK EXECUTION                                 │      │
│  │     → WARN: "Wrong tool for this query"               │      │
│  │     → SUGGEST: Correct tool                           │      │
│  │   ELSE:                                               │      │
│  │     → ALLOW EXECUTION                                 │      │
│  └───────────────────────────────────────────────────────┘      │
│                                                                  │
│  STEP 4: Execute Correct Tool                                   │
│  ┌───────────────────────────────────────────────────────┐      │
│  │ Call the validated tool with correct parameters       │      │
│  │ Return results to user                                │      │
│  └───────────────────────────────────────────────────────┘      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────┐
│                 TOOL SELECTION QUICK REFERENCE                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  "My tasks" / "Assigned to me"                                  │
│  ✅ wit_my_work_items                                            │
│  ❌ search_workitem (TEXT SEARCH ONLY!)                          │
│                                                                  │
│  "Search for [text] in work items"                              │
│  ✅ search_workitem                                              │
│                                                                  │
│  "Active bugs" / "Items in state X" / "By assignee"             │
│  ✅ CLI: az boards query --wiql "..."                            │
│  ❌ search_workitem (IGNORES FILTERS!)                           │
│                                                                  │
│  "Work item #123"                                               │
│  ✅ wit_get_work_item                                            │
│                                                                  │
│  "Multiple items by ID"                                         │
│  ✅ wit_get_work_items_batch_by_ids                              │
│                                                                  │
│  "Sprint backlog" / "Iteration items"                           │
│  ✅ wit_get_work_items_for_iteration                             │
│                                                                  │
│  "All items in project" (no personal filter)                    │
│  ✅ CLI WIQL or saved query                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Examples: Before and After Guard

### Example 1: "Show my tasks"

**Before Guard (WRONG)**:
```javascript
mcp__azure-devops__search_workitem({
  "searchText": "*",
  "assignedTo": ["@Me"],
  "workItemType": ["Task"]
})
// Result: 0 items (filters ignored!)
```

**After Guard (CORRECT)**:
```javascript
mcp__azure-devops__wit_my_work_items({
  "project": "Relief Center",
  "type": "assignedtome",
  "includeCompleted": false,
  "top": 50
})
// Result: All my assigned work items
```

### Example 2: "Find bugs about login"

**Before Guard**: Might use wrong parameters

**After Guard (CORRECT)**:
```javascript
// This IS a text search, so search_workitem is correct
mcp__azure-devops__search_workitem({
  "searchText": "login bug",
  "project": ["Relief Center"]
})
// Result: Items containing "login bug" text
```

### Example 3: "Active bugs assigned to Mahmoud"

**Before Guard (WRONG)**:
```javascript
mcp__azure-devops__search_workitem({
  "searchText": "*",
  "assignedTo": ["mahmoud"],
  "state": ["Active"],
  "workItemType": ["Bug"]
})
// Result: 0 items
```

**After Guard (CORRECT)**:
```bash
az boards query --wiql "
  SELECT [System.Id], [System.Title]
  FROM WorkItems
  WHERE [System.TeamProject] = 'Relief Center'
    AND [System.AssignedTo] CONTAINS 'mahmoud'
    AND [System.State] = 'Active'
    AND [System.WorkItemType] = 'Bug'
" --output json
```

---

## Integration Points

This guard integrates with:

1. **SKILL.md** - Main skill file references this guard
2. **commands/my-tasks.md** - Uses guard for task queries
3. **commands/sync-my-tasks.md** - Uses guard for TODO sync
4. **memories/mcp_best_practices.md** - Documents correct patterns

---

*Tool Selection Guard v1.0*
*Part of DevOps Plugin v3.0 Enhancement*
*TaqaTechno - December 2025*
