---
title: 'Switch Project'
read_only: false
type: 'command'
description: 'Switch the current project context for all subsequent queries'
---

# Switch Project Context

Change the default project context used for all subsequent Azure DevOps queries.

## Usage

```
switch to Relief Center
use KhairGate
work on Property Management
set project TAQAT HR
```

## Supported Trigger Phrases

| Phrase | Example |
|--------|---------|
| `switch to [project]` | "switch to Relief Center" |
| `use [project]` | "use KhairGate" |
| `work on [project]` | "work on Property Management" |
| `change project to [project]` | "change project to Beneshty" |
| `set project [project]` | "set project TAQAT HR" |
| `default project [project]` | "default project OkSouq" |

## Project Aliases

Users can use short names or aliases:

| Full Name | Aliases |
|-----------|---------|
| Relief Center | `relief`, `rc`, `disaster` |
| KhairGate | `kg`, `beneficiary` |
| Property Management | `property`, `pm`, `real-estate` |
| TAQAT HR | `hr`, `payroll` |
| Beneshty | `children`, `charity` |
| OkSouq | `souq`, `marketplace` |
| Arcelia | `crm`, `real-estate-crm` |
| Ittihad Club | `ittihad`, `club`, `sports` |

## Workflow

### Step 1: Resolve Project Name

```javascript
// User input: "switch to relief"
const input = "relief";

// Check against aliases in project_defaults.json
const projects = [
  { name: "Relief Center", aliases: ["relief", "relief-center", "rc", "disaster"] },
  { name: "KhairGate", aliases: ["khairgate", "kg", "beneficiary"] },
  // ...
];

// Find matching project (case-insensitive)
const match = projects.find(p =>
  p.name.toLowerCase() === input.toLowerCase() ||
  p.aliases.some(a => a.toLowerCase() === input.toLowerCase())
);

// Result: { name: "Relief Center", ... }
```

### Step 2: Validate Project Exists

```javascript
// Optionally verify project exists in Azure DevOps
mcp__azure-devops__core_list_projects({
  "projectNameFilter": "Relief Center"
})

// Expected: Returns project with matching name
```

### Step 3: Update Context

```javascript
// Store new context
const previousProject = getContext();  // e.g., "KhairGate"
setContext("Relief Center");
```

### Step 4: Confirm to User

```
✓ Switched project context

Previous: KhairGate
Current: Relief Center

All subsequent commands will use Relief Center.
Say "switch to [project]" to change again.
```

## Example Flows

### Example 1: Switch Using Full Name

**User**: "switch to KhairGate"

**Claude**:
```
✓ Switched project context

Previous: Relief Center
Current: KhairGate

All subsequent commands will use KhairGate.
```

### Example 2: Switch Using Alias

**User**: "use hr"

**Claude**:
```
Resolving "hr"...
Found: TAQAT HR

✓ Switched project context

Previous: KhairGate
Current: TAQAT HR

All subsequent commands will use TAQAT HR.
```

### Example 3: Ambiguous Input

**User**: "switch to property"

**Claude**:
```
Found project: Property Management

✓ Switched project context

Previous: TAQAT HR
Current: Property Management
```

### Example 4: Unknown Project

**User**: "switch to xyz"

**Claude**:
```
⚠️ I couldn't find a project matching "xyz".

Available projects:
• Relief Center (aliases: relief, rc, disaster)
• KhairGate (aliases: kg, beneficiary)
• Property Management (aliases: property, pm)
• TAQAT HR (aliases: hr, payroll)
• Beneshty (aliases: children, charity)
• OkSouq (aliases: souq, marketplace)
• Arcelia (aliases: crm)
• Ittihad Club (aliases: ittihad, club, sports)

Please specify the correct project name or alias.
```

### Example 5: No Current Context

**User**: "switch to Relief Center" (first time)

**Claude**:
```
✓ Project context set

Current: Relief Center

All subsequent commands will use Relief Center.
```

## Query Current Context

Users can check their current context:

| Phrase | Example |
|--------|---------|
| `what project am I in?` | Shows current context |
| `current project` | Shows current context |
| `which project?` | Shows current context |
| `show context` | Shows current context |

**Response**:
```
📁 Current Project: Relief Center

You're working in Relief Center.
All queries use this project by default.

Say "switch to [project]" to change.
```

## One-Time Override vs Permanent Switch

### One-Time Override (Doesn't Change Context)

```
User: "tasks in KhairGate"   ← Uses KhairGate once
User: "my bugs"              ← Still uses Relief Center (context unchanged)
```

### Permanent Switch (Changes Context)

```
User: "switch to KhairGate"  ← Changes context
User: "my bugs"              ← Uses KhairGate
User: "create task"          ← Uses KhairGate
```

## Multi-Project Queries

These queries work across ALL projects without changing context:

```
User: "all my tasks across all projects"
```

**Response**:
```
📁 Querying all projects...

## My Work Items Across All Projects

### Relief Center (8 items)
| ID | Type | Title | State |
...

### KhairGate (3 items)
| ID | Type | Title | State |
...

📊 Total: 11 items across 2 projects
📌 Default project: Relief Center (unchanged)
```

## Context Persistence Rules

1. **Session-Based**: Context persists throughout conversation
2. **Explicit Switch**: Use switch phrases to change permanently
3. **One-Time Override**: Use "in [project]" for single query
4. **Reset on New Session**: Context resets when conversation ends
5. **Auto-Detection**: If no context, detects from user's activity

## Error Handling

### API Error

```
If project lookup fails:

"I couldn't verify the project due to a connection issue.
Do you want me to:
1. Retry the lookup
2. Use 'Relief Center' without verification
3. Show available projects from cache"
```

### Permission Error

```
If user doesn't have access to project:

"⚠️ You don't appear to have access to 'XYZ Project'.

Projects you have access to:
• Relief Center
• KhairGate
• Property Management

Please check your permissions or choose another project."
```

## Output Format

### Successful Switch

```
✓ Switched project context

Previous: {oldProject}
Current: {newProject}

All subsequent commands will use {newProject}.
```

### With Alias Resolution

```
Resolving "{alias}"...
Found: {fullProjectName}

✓ Switched project context

Previous: {oldProject}
Current: {newProject}
```

### Context Query Response

```
📁 Current Project: {projectName}

You're working in {projectName}.
All queries use this project by default.

Say "switch to [project]" to change.
```

---

*Part of DevOps Plugin v3.0*
*Smart Project Context: Enabled*
