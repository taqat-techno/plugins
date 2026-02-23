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
switch to Project Alpha
use Project Beta
work on Project Gamma
set project Project Theta
```

## Supported Trigger Phrases

| Phrase | Example |
|--------|---------|
| `switch to [project]` | "switch to Project Alpha" |
| `use [project]` | "use Project Beta" |
| `work on [project]` | "work on Project Gamma" |
| `change project to [project]` | "change project to Project Delta" |
| `set project [project]` | "set project Project Theta" |
| `default project [project]` | "default project Project Epsilon" |

## Project Aliases

Users can use short names or aliases:

| Full Name | Aliases |
|-----------|---------|
| Project Alpha | `relief`, `rc`, `disaster` |
| Project Beta | `kg`, `beneficiary` |
| Project Gamma | `property`, `pm`, `real-estate` |
| Project Theta | `hr`, `payroll` |
| Project Delta | `children`, `charity` |
| Project Epsilon | `souq`, `marketplace` |
| Project Zeta | `crm`, `real-estate-crm` |
| Project Eta | `ittihad`, `club`, `sports` |

## Workflow

### Step 1: Resolve Project Name

```javascript
// User input: "switch to relief"
const input = "relief";

// Check against aliases in project_defaults.json
const projects = [
  { name: "Project Alpha", aliases: ["relief", "relief-center", "rc", "disaster"] },
  { name: "Project Beta", aliases: ["khairgate", "kg", "beneficiary"] },
  // ...
];

// Find matching project (case-insensitive)
const match = projects.find(p =>
  p.name.toLowerCase() === input.toLowerCase() ||
  p.aliases.some(a => a.toLowerCase() === input.toLowerCase())
);

// Result: { name: "Project Alpha", ... }
```

### Step 2: Validate Project Exists

```javascript
// Optionally verify project exists in Azure DevOps
mcp__azure-devops__core_list_projects({
  "projectNameFilter": "Project Alpha"
})

// Expected: Returns project with matching name
```

### Step 3: Update Context

```javascript
// Store new context
const previousProject = getContext();  // e.g., "Project Beta"
setContext("Project Alpha");
```

### Step 4: Confirm to User

```
✓ Switched project context

Previous: Project Beta
Current: Project Alpha

All subsequent commands will use Project Alpha.
Say "switch to [project]" to change again.
```

## Example Flows

### Example 1: Switch Using Full Name

**User**: "switch to Project Beta"

**Claude**:
```
✓ Switched project context

Previous: Project Alpha
Current: Project Beta

All subsequent commands will use Project Beta.
```

### Example 2: Switch Using Alias

**User**: "use hr"

**Claude**:
```
Resolving "hr"...
Found: Project Theta

✓ Switched project context

Previous: Project Beta
Current: Project Theta

All subsequent commands will use Project Theta.
```

### Example 3: Ambiguous Input

**User**: "switch to property"

**Claude**:
```
Found project: Project Gamma

✓ Switched project context

Previous: Project Theta
Current: Project Gamma
```

### Example 4: Unknown Project

**User**: "switch to xyz"

**Claude**:
```
⚠️ I couldn't find a project matching "xyz".

Available projects:
• Project Alpha (aliases: relief, rc, disaster)
• Project Beta (aliases: kg, beneficiary)
• Project Gamma (aliases: property, pm)
• Project Theta (aliases: hr, payroll)
• Project Delta (aliases: children, charity)
• Project Epsilon (aliases: souq, marketplace)
• Project Zeta (aliases: crm)
• Project Eta (aliases: ittihad, club, sports)

Please specify the correct project name or alias.
```

### Example 5: No Current Context

**User**: "switch to Project Alpha" (first time)

**Claude**:
```
✓ Project context set

Current: Project Alpha

All subsequent commands will use Project Alpha.
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
📁 Current Project: Project Alpha

You're working in Project Alpha.
All queries use this project by default.

Say "switch to [project]" to change.
```

## One-Time Override vs Permanent Switch

### One-Time Override (Doesn't Change Context)

```
User: "tasks in Project Beta"   ← Uses Project Beta once
User: "my bugs"              ← Still uses Project Alpha (context unchanged)
```

### Permanent Switch (Changes Context)

```
User: "switch to Project Beta"  ← Changes context
User: "my bugs"              ← Uses Project Beta
User: "create task"          ← Uses Project Beta
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

### Project Alpha (8 items)
| ID | Type | Title | State |
...

### Project Beta (3 items)
| ID | Type | Title | State |
...

📊 Total: 11 items across 2 projects
📌 Default project: Project Alpha (unchanged)
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
2. Use 'Project Alpha' without verification
3. Show available projects from cache"
```

### Permission Error

```
If user doesn't have access to project:

"⚠️ You don't appear to have access to 'XYZ Project'.

Projects you have access to:
• Project Alpha
• Project Beta
• Project Gamma

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
