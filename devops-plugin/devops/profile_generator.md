# User Profile Generator

Reference document for building and maintaining the user's `DevOps.md` profile file at `~/.claude/devops.md`.

---

## Profile File Location

```
~/.claude/devops.md
```

- **Windows**: `C:\Users\{USERNAME}\.claude\devops.md`
- **macOS**: `/Users/{USERNAME}/.claude/devops.md`
- **Linux**: `/home/{USERNAME}/.claude/devops.md`

---

## Generation Workflow

### Step 1: Resolve Current User Identity

Use the authenticated PAT to discover who the current user is.

**Method A: MCP (preferred)**
```javascript
// Get current user's connection info
mcp__azure-devops__core_get_connection_data({})
// Returns: { authenticatedUser: { id, displayName, uniqueName } }
```

**Method B: CLI fallback**
```bash
az devops user show --user "me" --output json
# Returns: displayName, mailAddress, principalName
```

**Method C: Identity search**
```javascript
// If methods A/B don't return full info, search by the PAT owner
mcp__azure-devops__core_get_identity_ids({
  "searchFilter": authenticatedUser.uniqueName
})
```

Extract and store:
- `displayName` — Full name
- `email` / `uniqueName` — Email address
- `guid` / `id` — Azure DevOps GUID

### Step 2: Fetch User's Projects

```javascript
const projects = await mcp__azure-devops__core_list_projects({})

// For each project, get user's team membership
for (const project of projects) {
  const teams = await mcp__azure-devops__work_list_teams({
    "project": project.name
  })

  for (const team of teams) {
    const members = await mcp__azure-devops__work_get_team_members({
      "project": project.name,
      "team": team.name
    })

    // Check if current user is in this team
    if (members.some(m => m.uniqueName === currentUser.email)) {
      userProjects.push({
        name: project.name,
        team: team.name,
        role: "member"  // Will be refined by user input
      })
    }
  }
}
```

### Step 3: Fetch Team Members with GUIDs

For each project the user belongs to, collect all team members:

```javascript
const allMembers = new Map()  // deduplicate across projects

for (const project of userProjects) {
  const members = await mcp__azure-devops__work_get_team_members({
    "project": project.name,
    "team": project.team
  })

  for (const member of members) {
    if (!allMembers.has(member.uniqueName)) {
      // Resolve GUID
      const identity = await mcp__azure-devops__core_get_identity_ids({
        "searchFilter": member.uniqueName
      })

      allMembers.set(member.uniqueName, {
        name: member.displayName,
        email: member.uniqueName,
        guid: identity.id,
        aliases: generateAliases(member.displayName),
        role: "member"  // Default, can be refined
      })
    }
  }
}
```

**Alias Generation Logic**:
```javascript
function generateAliases(displayName) {
  const parts = displayName.toLowerCase().split(' ')
  const aliases = [
    parts[0],                           // "ahmed"
    parts[parts.length - 1],            // "mohamed"
    parts.map(p => p[0]).join(''),      // "am"
  ]
  return [...new Set(aliases)]  // deduplicate
}
```

### Step 4: Fetch Task Templates from Project Settings

Fetch the actual task templates defined in the project's Board settings. These are the naming prefixes the organization uses.

**Location in Azure DevOps**: Project Settings → Boards → Templates → Task

```javascript
// Method A: Via MCP (if available)
mcp__azure-devops__wit_get_work_item_type_fields({
  "project": currentProject,
  "type": "Task"
})

// Method B: Via CLI
az boards work-item template list --project "Project Alpha" --type Task --output json
// Returns: [{ "name": "[Dev]", ... }, { "name": "[Front]", ... }, ...]

// Method C: Via REST API through CLI
az devops invoke --area wit --resource templates \
  --route-parameters project="Project Alpha" team="Project Alpha Team" \
  --query-parameters workItemTypeName=Task --output json
```

Store the templates in the profile:

```yaml
taskTemplates:
  - name: "[Dev]"
    description: "Backend/Full-Stack development"
    keywords: ["api", "endpoint", "database", "model", "backend", "server", "implement"]
  - name: "[Front]"
    description: "Frontend development"
    keywords: ["ui", "component", "form", "page", "style", "css", "frontend"]
  - name: "[QC Bug Fixing]"
    description: "QA - Bug fixing and verification"
    keywords: ["fix", "bug", "patch", "hotfix", "debug", "resolve", "reproduce"]
  - name: "[QC Test Execution]"
    description: "QA - Test case execution"
    keywords: ["test", "execute", "test case", "regression", "scenario", "validate"]
  - name: "[IMP]"
    description: "Implementation, deployment, configuration"
    keywords: ["deploy", "config", "setup", "install", "migration", "infrastructure"]
```

**If API returns templates**: Use them directly (org-specific).
**If API fails or returns empty**: Use the defaults above.

### Step 5: Ask User for Role

Present role selection based on the ACTUAL templates found in Step 4:

```
What is your primary role? (based on your project's task templates)

| # | Template | Description |
|---|----------|-------------|
| 1 | [Dev] | Backend/Full-Stack development |
| 2 | [Front] | Frontend development |
| 3 | [QC Bug Fixing] | QA - Bug fixing and verification |
| 4 | [QC Test Execution] | QA - Test case execution |
| 5 | [IMP] | Implementation, deployment, configuration |
```

The user's selection sets `preferences.taskPrefix` in the profile.

### Step 6: Generate State Permissions from Role

Based on the user's selected role, auto-populate statePermissions in the profile:

1. Read `data/state_permissions.json`
2. Find `rolePermissions` entry matching the user's role:
   - `"developer"` / `"backend"` / `"fullstack"` → `rolePermissions.developer`
   - `"frontend"` → `rolePermissions.frontend` (`$ref:developer` — same permissions)
   - `"tester"` / `"qa"` / `"qc-bugfix"` / `"qc-test"` → `rolePermissions.qa`
   - `"pm"` / `"lead"` → `rolePermissions.pm`
3. Copy the permissions block into the profile YAML under `statePermissions`:

```yaml
statePermissions:
  Task:
    allowed: ["To Do → In Progress", "In Progress → Done"]
    blocked: ["Done → Closed", "Any → Removed"]
    blockedMessage: "Only PM can close or remove Tasks"
  Bug:
    allowed: ["Approved → In Progress", "In Progress → Resolved"]
    blocked: ["New → Approved", "Resolved → Done", "Done → Closed"]
    blockedMessage: "Approve/Done is QA only, Close is PM only"
  PBI:
    allowed: ["Committed → In Progress", "In Progress → Ready For QC"]
    blocked: ["New → Approved", "Approved → Committed", "Ready For QC → Done"]
    blockedMessage: "Approve/Commit is PM only, Done is QA only"
  Enhancement:
    allowed: []
    blocked: ["New → Committed", "Done → Closed"]
    blockedMessage: "Commit and Close are PM only"
```

4. Show confirmation to user:

```
State permissions configured for your role ({role}):
 - Task: {list allowed transitions}
 - Bug: {list allowed transitions}
 - PBI: {list allowed transitions}
 - Enhancement: {list allowed transitions}

These prevent accidental state changes outside your role.
You can always re-run /init profile to update.
```

### Step 7: Fetch Repository List (Optional)

For each project, get available repositories:

```javascript
for (const project of userProjects) {
  const repos = await mcp__azure-devops__repo_list_repos({
    "project": project.name
  })
  project.repos = repos.map(r => r.name)
}
```

### Step 8: Generate DevOps.md

Use the template from `data/profile_template.md` and fill in the collected data.

### Step 9: Write to Disk

```javascript
Write({
  file_path: "~/.claude/devops.md",
  content: generatedContent
})
```

---

## Role-to-Prefix Mapping

### Default Mapping (when no project templates are fetched)

| Role Value | Default Prefix | Display Name |
|------------|---------------|-------------|
| `developer` / `backend` | `[Dev]` | Backend Developer |
| `frontend` | `[Front]` | Frontend Developer |
| `fullstack` | `[Dev]` | Full-Stack Developer |
| `tester` / `qa` / `qc-bugfix` | `[QC Bug Fixing]` | QA - Bug Fixing |
| `qa-test` / `qc-test` | `[QC Test Execution]` | QA - Test Execution |
| `devops` / `pm` / `lead` | `[IMP]` | Implementation / Management |

### Dynamic Mapping (when templates ARE fetched from project)

The role selection in Step 5 presents the actual templates from the project.
The user picks their default, and it's stored as-is in `preferences.taskPrefix`.
No mapping table is needed — the template name IS the prefix.

---

## Profile Refresh Workflow

When user runs `/init profile --refresh`:

1. Read existing `~/.claude/devops.md` to preserve:
   - User's role selection (don't re-ask)
   - Custom aliases they may have added
   - Preferences
2. Re-fetch from API:
   - Identity (in case display name changed)
   - Projects (new projects may have been added)
   - Team members (people join/leave)
   - Repositories (new repos created)
3. Merge: Keep user customizations, update API-sourced data
4. Write updated file
5. Report what changed:
   ```
   Profile refreshed at ~/.claude/devops.md

   Changes:
   - 1 new project added: Project Gamma
   - 2 new team members: Bob Smith, Carol Brown
   - 1 team member removed: Dave Wilson
   - Repositories updated for Project Alpha (+1 new repo)
   ```

---

## Profile Loading (Session Start)

When any devops command or skill triggers:

```
Step 0: Load User Profile

1. Try to Read ~/.claude/devops.md
2. If found:
   a. Parse YAML frontmatter
   b. Build lookup tables:
      - currentUser = identity object
      - teamByAlias = Map(alias → {name, email, guid, role})
         Include "me", "myself" → current user
      - teamByEmail = Map(email → {name, guid, role})
      - projectsByName = Map(name → {role, team, repos})
      - statePerms = Map(workItemType → {allowed, blocked, blockedMessage})
   c. Set defaultProject from profile
   d. Set taskPrefix from preferences
   e. Profile loaded → proceed with command
3. If NOT found:
   a. Show: "No user profile found. Run /init profile to set up."
   b. Fall back to API-based resolution (current behavior)
   c. Continue with command (graceful degradation)
```

---

## Cache-First Resolution Pattern

For any operation that needs a user identity (assign, mention, comment):

```
1. Extract name/alias from user input
2. Check special aliases:
   - "me", "myself", "I" → return currentUser from profile
3. Check teamByAlias lookup:
   - If found → return cached {name, email, guid}
4. Check teamByEmail lookup:
   - If found → return cached {name, email, guid}
5. If NOT in cache → fall back to API:
   - Call core_get_identity_ids({ searchFilter: name })
   - If found → suggest adding to profile:
     "Found user '{name}'. Add to your DevOps.md profile? (y/n)"
6. If API also fails → ask user for clarification
```

---

*Part of DevOps Plugin v4.2 — User Profile System with State Permissions*
