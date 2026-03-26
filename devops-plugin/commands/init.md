---
title: 'Init'
read_only: false
type: 'command'
description: 'Complete Azure DevOps integration setup - installs CLI, configures MCP, generates user profile with team GUIDs, role permissions, and project defaults. Use /init for full setup or /init profile to regenerate profile.'
primary_agent: skill
---

# /init - Azure DevOps Integration Setup

## Sub-Commands

| Usage | Action |
|-------|--------|
| `/init` or `/init setup` | Full setup (CLI + MCP + profile) |
| `/init status` | Check current configuration |
| `/init profile` | Generate/regenerate user profile |
| `/init profile --refresh` | Refresh profile preserving user customizations |

---

## Full Setup Workflow

### Step 1: Install CLI

```bash
az extension add --name azure-devops
az devops configure --defaults organization=https://dev.azure.com/ORG project=PROJECT
az devops login --organization https://dev.azure.com/ORG
```

### Step 1.5: MCP Dedup — Migrate Global Config to Plugin

The plugin provides its own `azure-devops` MCP server via `.mcp.json`. If the user also has one in their global config (`~/.claude/.mcp.json`), the plugin's version overrides it. This step detects and migrates the global config.

**Procedure:**

1. Read `~/.claude/.mcp.json` (the global MCP config)
2. Check if `azure-devops` exists at root level OR inside `mcpServers`
3. **If found:**
   a. Extract the token — look in `env.ADO_MCP_AUTH_TOKEN` (may be a hardcoded string or `${ENV_VAR}`)
   b. Extract the org — look in `args` array for the element after `@azure-devops/mcp`
   c. Show the user what was found: `"Found azure-devops in global config. Org: {org}, Token: {masked first 8 chars}..."`
   d. Ask the user: `"Migrate to plugin and remove from global? (This sets ADO_MCP_AUTH_TOKEN and ADO_ORGANIZATION as environment variables)"`
   e. If yes:
      - If on Windows: run `setx ADO_MCP_AUTH_TOKEN "{token}"` and `setx ADO_ORGANIZATION "{org}"`
      - If on Linux/Mac: append `export ADO_MCP_AUTH_TOKEN="{token}"` and `export ADO_ORGANIZATION="{org}"` to `~/.bashrc` or `~/.zshrc`
      - Remove the `azure-devops` entry from `~/.claude/.mcp.json` (keep other servers intact)
      - If the global file becomes `{"mcpServers":{}}` or `{}`, leave it (don't delete the file)
      - Report: `"Migrated azure-devops config from global to plugin. Token and org set as environment variables. Global entry removed. Restart Claude Code to take effect."`
4. **If NOT found:**
   a. Check if `ADO_MCP_AUTH_TOKEN` and `ADO_ORGANIZATION` env vars are already set
   b. If both set: report `"MCP config OK — env vars found."`
   c. If missing: ask user for their Azure DevOps organization name and PAT token, then set as env vars (same `setx`/`export` approach)
5. Verify the plugin `.mcp.json` can resolve `${ADO_ORGANIZATION}` and `${ADO_MCP_AUTH_TOKEN}`

**Important:** The plugin `.mcp.json` uses `@azure-devops/mcp` (the correct official package), NOT `@anthropic-ai/azure-devops-mcp`. If the global config uses the wrong package, still extract the token — they use the same PAT format.

### Step 2: Verify MCP Server

Verify the plugin's `@azure-devops/mcp` MCP server connects successfully:

```javascript
// Test MCP connectivity
mcp__azure-devops__core_get_connection_data({})
// Should return: { authenticatedUser: { displayName, uniqueName } }
```

If this fails, check that `ADO_MCP_AUTH_TOKEN` and `ADO_ORGANIZATION` environment variables are set and Claude Code was restarted after setting them.

### Step 3: Generate User Profile

Run the profile generation workflow below.

### Step 4: Verify Hybrid Mode

Test both CLI and MCP connectivity. Report status.

---

## Profile Generation Workflow

### Profile Location

```
~/.claude/devops.md
  Windows: C:\Users\{USERNAME}\.claude\devops.md
```

### Step 1: Resolve Current User Identity

**Method A (MCP preferred)**:
```javascript
mcp__azure-devops__core_get_connection_data({})
// Returns: { authenticatedUser: { id, displayName, uniqueName } }
```

**Method B (CLI fallback)**:
```bash
az devops user show --user "me" --output json
```

**Method C (Identity search)**:
```javascript
mcp__azure-devops__core_get_identity_ids({ "searchFilter": authenticatedUser.uniqueName })
```

Extract: `displayName`, `email`/`uniqueName`, `guid`/`id`

### Step 2: Fetch User's Projects

```javascript
const projects = await core_list_projects({})
// For each project, check team membership via work_get_team_members
// Record projects where current user is a member
```

### Step 3: Fetch Team Members with GUIDs

For each project the user belongs to:
1. Get all team members via `work_get_team_members`
2. Resolve each member's GUID via `core_get_identity_ids`
3. Generate aliases from display names:
   ```
   "Ahmed Mohamed" -> aliases: ["ahmed", "mohamed", "am"]
   ```
4. Deduplicate across projects

### Step 4: Fetch Task Templates from Project Settings

```bash
az devops invoke --area wit --resource templates \
  --route-parameters project="PROJECT" team="TEAM" \
  --query-parameters workItemTypeName=Task --output json
```

If API returns templates, use them. If empty, use defaults from `data/state_machine.json` `businessRules.taskNaming.defaultPrefixes`.

### Step 5: Ask User for Role

Present role selection based on templates found:

```
What is your primary role?

| # | Template | Description |
|---|----------|-------------|
| 1 | [Dev] | Backend/Full-Stack development |
| 2 | [Front] | Frontend development |
| 3 | [QC Bug Fixing] | QA - Bug fixing |
| 4 | [QC Test Execution] | QA - Test execution |
| 5 | [IMP] | Implementation / deployment |
```

### Step 6: Generate State Permissions from Role

1. Read `data/state_machine.json` -> `rolePermissions`
2. Match user's role to permission set:
   - developer/backend/fullstack -> `rolePermissions.developer`
   - frontend -> `rolePermissions.frontend` ($ref:developer)
   - tester/qa/qc-* -> `rolePermissions.qa`
   - pm/lead -> `rolePermissions.pm`
3. Copy permissions block into profile YAML under `statePermissions`
4. Show confirmation of configured permissions

### Step 7: Fetch Repository List (Optional)

```javascript
for (const project of userProjects) {
  const repos = await repo_list_repos({ "project": project.name })
  project.repos = repos.map(r => r.name)
}
```

### Step 8: Generate DevOps.md

Use template from `data/profile_template.md`, fill with collected data. **Always set `lastRefresh` to today's ISO date** so the session-start hook can detect staleness (>30 days triggers refresh reminder).

Profile structure:

```yaml
---
lastRefresh: "2026-03-26"

identity:
  displayName: "Full Name"
  email: "user@company.com"
  guid: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
role: "developer"
defaultProject: "Project Alpha"
preferences:
  taskPrefix: "[Dev]"
taskTemplates: [...]
statePermissions:
  Task: { allowed: [...], blocked: [...], blockedMessage: "..." }
  Bug: { ... }
  ProductBacklogItem: { ... }
teamMembers:
  - name: "Ahmed Mohamed"
    email: "ahmed@company.com"
    guid: "..."
    aliases: ["ahmed", "mohamed", "am"]
    role: "developer"
projects:
  - name: "Project Alpha"
    team: "Alpha Team"
    repos: ["repo-1", "repo-2"]
---
```

### Step 9: Write to Disk

Write generated content to `~/.claude/devops.md`.

---

## Profile Refresh (`/init profile --refresh`)

1. Read existing `~/.claude/devops.md` — preserve role, custom aliases, preferences
2. Re-fetch from API: identity, projects, team members, repositories
3. Merge: keep user customizations, update API-sourced data
4. Write updated file
5. Report changes:
   ```
   Profile refreshed. Changes:
   - 1 new project added: Project Gamma
   - 2 new team members: Bob, Carol
   - Repositories updated for Project Alpha (+1)
   ```
