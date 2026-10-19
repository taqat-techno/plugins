---
title: 'Init'
read_only: false
type: 'command'
description: 'Complete Azure DevOps integration setup - installs CLI, configures MCP, detects the project process (Basic/Agile/Scrum/CMMI or a custom preset), generates user profile with team GUIDs, role, and project defaults. Use /init for full setup or /init profile to regenerate profile.'
primary_agent: skill
---

# /init - Azure DevOps Integration Setup

## Sub-Commands

| Usage | Action |
|-------|--------|
| `/init` or `/init setup` | Full setup (CLI + MCP + profile) |
| `/init status` | Check current configuration status |
| `/init profile` | Generate/regenerate user profile |
| `/init profile --refresh` | Refresh profile preserving user customizations |

---

## CRITICAL: Pre-Flight Detection (ALWAYS RUN FIRST)

Before doing ANYTHING, detect the current configuration state. This prevents redundant work, avoids overwriting existing configs, and identifies exactly what needs to be fixed.

### Pre-Flight Checks

Run these checks silently and build a status table:

| Component | How to Check | Expected |
|-----------|-------------|----------|
| **ADO_MCP_AUTH_TOKEN** | Read `$ADO_MCP_AUTH_TOKEN` env var. If empty on Windows, also check registry: `powershell.exe -Command "[Environment]::GetEnvironmentVariable('ADO_MCP_AUTH_TOKEN','User')"` | Non-empty string |
| **ADO_ORGANIZATION** | Read `$ADO_ORGANIZATION` env var. If empty on Windows, also check registry: `powershell.exe -Command "[Environment]::GetEnvironmentVariable('ADO_ORGANIZATION','User')"` | Org name only (no URL) |
| **Profile** | Check if `~/.claude/devops.md` exists. If yes, read `lastRefresh` date. | Exists, <30 days old |
| **MCP Server** | Try `mcp__plugin_devops_azure-devops__core_list_projects({})`. If it works, MCP is live. | Returns project list |
| **Azure CLI** | Run `az --version 2>/dev/null` | Installed |
| **CLI Extension** | Run `az extension show --name azure-devops 2>/dev/null` | Installed |
| **Pending Init** | Check if `~/.claude/devops-init-pending.json` exists | Usually absent |

### Show Status Table

Present the results clearly:

```
Azure DevOps Configuration Status
----------------------------------
ADO_MCP_AUTH_TOKEN  : [Set / Not Set / Set in registry but not in current shell]
ADO_ORGANIZATION    : [Set / Not Set / Set but contains URL (needs fix)]
Profile             : [Exists (X days old) / Not found]
MCP Server          : [Connected / Not responding / Not configured]
Azure CLI           : [Installed / Not installed]
Pending Init        : [Resuming from previous setup / None]
```

### Decision Logic

Based on the pre-flight results:

| State | Action |
|-------|--------|
| Everything configured and working | "All good. Use `/init profile --refresh` to update profile data." |
| Env vars in registry but not in shell | "Env vars are set but your shell hasn't picked them up. Restart your terminal/IDE/computer." |
| Env vars missing entirely | Jump to "Environment Variable Setup" below |
| MCP not responding but env vars set | "MCP server not responding. Try restarting Claude Code. If still failing, check your PAT token." |
| Profile missing but MCP works | Jump to "Profile Generation" below |
| Profile exists but stale (>30 days) | "Profile is X days old. Run `/init profile --refresh` to update." |
| Fresh install (nothing configured) | Run full setup flow below |
| Pending init exists | Resume from where previous setup stopped |

---

## `/init status` — Configuration Health Check

When the user runs `/init status`, run ONLY the pre-flight checks above and show the status table. Do not start any setup steps. This is a read-only diagnostic.

**Windows registry fallback**: If env vars appear empty in the bash shell, always also check the Windows registry:

```bash
powershell.exe -Command "[Environment]::GetEnvironmentVariable('ADO_MCP_AUTH_TOKEN','User')"
powershell.exe -Command "[Environment]::GetEnvironmentVariable('ADO_ORGANIZATION','User')"
```

If registry has values but shell doesn't, tell the user: "Environment variables are set in the Windows registry but not available in your current shell. You need to restart your computer (or close and reopen all terminals and VS Code) for the changes to take effect."

---

## Full Setup Workflow (`/init` or `/init setup`)

### Step 1: Environment Variable Setup

**CRITICAL LESSON: On Windows, `setx` sets registry values but the current process does NOT inherit them. You MUST NOT try to verify MCP connectivity immediately after setting env vars.**

#### Check existing env vars first

If both `ADO_MCP_AUTH_TOKEN` and `ADO_ORGANIZATION` are already set and non-empty, skip to Step 2.

#### If env vars are missing: the user sets them

**NEVER ask the user to paste their Personal Access Token (PAT) into the chat, and never
set it on their behalf.** Anything typed in the conversation is stored in the session
transcript under `~/.claude/projects/`. Show the commands below and let the user run them
in their own terminal, then STOP. The user restarts and runs `/init` again.

If the user volunteers a PAT in chat anyway, do not use or echo it: tell them it is now in
the transcript and that they should revoke it in Azure DevOps (User settings ->
Personal access tokens) and create a new one.

**Organization name:** the value must be just the org name (e.g. `MyOrgName`), NOT a URL.
If the user mentions `https://dev.azure.com/MyOrgName/...`, tell them to use only the first
path segment after `dev.azure.com/`.

**PAT scopes:** create the PAT with the narrowest scopes covering what the user will do
(typically Work Items Read & Write, Code Read & Write, Build Read; add Build Read & Execute
only if they will run pipelines) and a short expiry.

Show platform-specific commands:

**Windows (PowerShell)** - prompts for the PAT so it never lands in shell history:
```
[Environment]::SetEnvironmentVariable('ADO_MCP_AUTH_TOKEN', (Read-Host 'Azure DevOps PAT'), 'User')
setx ADO_ORGANIZATION "YourOrgName"
```

**Linux/Mac:**
```
# Add to ~/.bashrc or ~/.zshrc (edit the file in your editor, not via a command
# that would leave the token in shell history):
export ADO_MCP_AUTH_TOKEN="your-personal-access-token-here"
export ADO_ORGANIZATION="YourOrgName"
```

Then show the restart notice (see below).

#### RESTART NOTICE (MANDATORY after setting env vars)

After showing the commands, ALWAYS show this notice and STOP the setup:

```
Once you have set the environment variables:

IMPORTANT: You MUST restart for changes to take effect.

On Windows: Restart your computer. (Closing VS Code alone is NOT enough
            because the VS Code process inherits from Explorer.exe which
            may not have received the registry update broadcast.)

On Linux/Mac: Close and reopen your terminal, or run: source ~/.bashrc

After restarting:
  1. Run /init status   -- verify env vars are now available
  2. Run /init          -- to continue setup from where you left off
```

**DO NOT attempt MCP verification at this point.** The env vars are not available in the current process.

#### Save pending state

Write a marker file so the next `/init` knows to resume:

```json
// ~/.claude/devops-init-pending.json
{
  "envVarsSet": true,
  "timestamp": "2026-04-04T10:30:00Z",
  "nextStep": "verify-mcp",
  "org": "MyOrgName"
}
```

### Step 1.5: Resume After Restart

If `~/.claude/devops-init-pending.json` exists when `/init` runs:

1. Read the pending state
2. Verify env vars are now available (check both shell env AND registry)
3. If available: proceed to Step 2 (MCP verification)
4. If still missing: "Environment variables are still not available. Did you restart your computer?"
5. After successful MCP verification, delete the pending file

### Step 2: MCP Dedup — Migrate Global Config to Plugin

The plugin provides its own `azure-devops` MCP server via `.mcp.json`. If the user also has one in their global config (`~/.claude/.mcp.json`), the plugin's version overrides it. This step detects and migrates the global config.

**Procedure:**

1. Read `~/.claude/.mcp.json` (the global MCP config)
2. Check if `azure-devops` exists at root level OR inside `mcpServers`
3. **If found:**
   a. Extract the token -- look in `env.ADO_MCP_AUTH_TOKEN` (may be a hardcoded string or `${ENV_VAR}`)
   b. Extract the org -- look in `args` array for the element after `@azure-devops/mcp`
   c. Show the user what was found: `"Found azure-devops in global config. Org: {org}, Token: {masked first 8 chars}..."`
   d. Ask the user: `"Migrate to plugin and remove from global? (This sets ADO_MCP_AUTH_TOKEN and ADO_ORGANIZATION as environment variables)"`
   e. If yes: set env vars (same flow as Step 1), remove entry from global config
   f. Show restart notice if env vars were newly set
4. **If NOT found:**
   a. Check if `ADO_MCP_AUTH_TOKEN` and `ADO_ORGANIZATION` env vars are already set
   b. If both set: report `"MCP config OK -- env vars found."`
   c. If missing: go back to Step 1 (env var setup)

**Important:** The plugin `.mcp.json` uses `@azure-devops/mcp` (the correct official package), NOT `@anthropic-ai/azure-devops-mcp`. If the global config uses the wrong package, still extract the token -- they use the same PAT format.

### Step 3: Verify MCP Server

Verify the plugin's `@azure-devops/mcp` MCP server connects successfully:

```javascript
// Test MCP connectivity
mcp__plugin_devops_azure-devops__core_list_projects({})
// Should return a list of projects the user has access to
```

If this fails:
- Check that `ADO_MCP_AUTH_TOKEN` and `ADO_ORGANIZATION` environment variables are set
- Check that Claude Code was restarted after setting them
- Try the registry check: `powershell.exe -Command "[Environment]::GetEnvironmentVariable('ADO_MCP_AUTH_TOKEN','User')"`

### Step 4: Generate User Profile

Run the profile generation workflow below. But first, check if a profile already exists.

### Step 5: Verify Hybrid Mode

Test both CLI and MCP connectivity. Report status.

---

## Profile Generation Workflow

### PROTECT EXISTING PROFILE

Before generating a profile, ALWAYS check if `~/.claude/devops.md` already exists:

**If profile exists:**
```
Existing profile found:
  Role: developer
  Default Project: My Project
  Last Refreshed: 2026-03-20 (15 days ago)

What would you like to do?
  1. Refresh (keep your customizations, update team/project data from API)  [RECOMMENDED]
  2. Regenerate from scratch (will replace ALL customizations)
  3. Cancel
```

Default to option 1 (refresh) -- it's the safest choice.

If the user picks option 1, run the "Profile Refresh" workflow instead.

**If profile does NOT exist:** proceed with fresh generation below.

### Profile Location

```
~/.claude/devops.md
  Windows: C:\Users\{USERNAME}\.claude\devops.md
```

### Step 1: Resolve Current User Identity

**Method A (MCP — only if available in your server version)**:
```javascript
// NOTE: @azure-devops/mcp 2.7.0 does NOT expose a connection-data/whoami tool.
// If this tool is unavailable, use Method B (CLI) or Method C below.
mcp__plugin_devops_azure-devops__core_get_connection_data({})
// Returns: { authenticatedUser: { id, displayName, uniqueName } }
```

**Method B (CLI fallback — reliable)**:
```bash
az devops user show --user "me" --output json
```

**Method C (Identity search)**:
```javascript
mcp__plugin_devops_azure-devops__core_get_identity_ids({ "searchFilter": authenticatedUser.uniqueName })
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
   "Jane Smith" -> aliases: ["jane", "smith", "js"]
   ```
4. Deduplicate across projects

### Step 3.5: Detect the Project's Process (sets `process`)

The plugin's state/role/naming behavior depends on which process the project uses.
The process models are presets in `data/state_machine.json` `processPresets`
(`basic`, `agile`, `scrum`, `cmmi` = Microsoft stock templates; `custom-scrum-qc` =
an opt-in customized Scrum). Detect it for the default project (read-only calls only):

1. **List the work item types in use** — `wit_list_backlogs({ project, team })`. Each
   backlog level lists its `workItemTypes`; collect the type names.
2. **Confirm the signature types and read their states** —
   `wit_get_work_item_type({ project, workItemType })` for the requirement-level type
   found in step 1 (`Product Backlog Item`, `User Story`, `Requirement` or `Issue`), and
   for `Enhancement` if present. The result includes the type's `states`. A "not found"
   error simply means the type does not exist in this project.
3. **Map to a preset** using `data/state_machine.json` `presetDetection.order` — first
   match wins (the custom signature is checked before plain Scrum).
4. **Confirm with the user**, showing the evidence:
   ```
   Detected process: Scrum (Microsoft default)
     Evidence: Product Backlog Item, Bug, Task, Feature, Epic; PBI states New/Approved/Committed/Done
   Use this preset? [Y / choose another: basic | agile | scrum | cmmi | custom-scrum-qc]
   ```
   If the live states differ from the preset (a customized inherited process), say so;
   the hook will then ask before any state the preset does not define.
5. **Fallback** — if the calls fail or nothing matches, ask: "Which process does
   `{project}` use? (Project Settings > Overview shows it)". If the user does not know,
   use the preset matching the detected types, else `defaultPreset` (`agile`).

Write the choice to the profile as `process: "<preset>"`. Never pick `custom-scrum-qc`
without the user's confirmation: it carries role rules and Task-title prefixes.

### Step 4: Fetch Task Templates from Project Settings

```bash
az devops invoke --area wit --resource templates \
  --route-parameters project="PROJECT" team="TEAM" \
  --query-parameters workItemTypeName=Task --output json
```

If the API returns templates, store them as `taskTemplates` (suggestions for `/create`).
Prefixes are only **required** when the active preset defines `taskNaming`
(`custom-scrum-qc` does; stock presets do not) or the user adds a `taskNaming`
override. Do not invent prefixes for a stock-process project.

### Step 5: Ask User for Role

Ask for the user's primary role: `developer`, `frontend`, `qa`, `pm`, `lead`, `devops`
(free text is fine; the hook normalizes "Tech Lead" -> `lead`, "Project Manager" -> `pm`).
If templates were found in Step 4, show them alongside so the user can pick a default
`preferences.taskPrefix`.

### Step 6: Role Rules and Enforcement (only if the preset defines them)

1. If the preset has `rolePermissions` (only `custom-scrum-qc`), copy the matching
   block into the profile under `statePermissions`:
   - developer/backend/fullstack -> `rolePermissions.developer`
   - frontend -> `rolePermissions.frontend` ($ref:developer)
   - tester/qa/qc-* -> `rolePermissions.qa`
   - pm/lead -> `rolePermissions.pm`
2. For a stock preset, omit `statePermissions`: role does not restrict transitions.
3. Tell the user how rule violations behave (`enforcement`, default `ask` - the hook
   asks before the write) and that `enforcement: "block"` restores hard blocking.
   Write `enforcement` only if the user chooses a non-default value.

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
process: "scrum"            # preset from Step 3.5 (data/state_machine.json processPresets)
# enforcement: "ask"        # ask (default) | block | advise
# roleRules: off            # optional override; inline JSON or off (see README "Process presets")
# taskNaming: off           # optional override; inline JSON or off
defaultProject: "Project Alpha"
preferences:
  taskPrefix: ""            # e.g. "[Dev]" when the project uses Task templates
taskTemplates: [...]
statePermissions:           # only when the preset defines rolePermissions (custom-scrum-qc)
  Task: { allowed: [...], blocked: [...], blockedMessage: "..." }
teamMembers:
  - name: "Jane Smith"
    email: "user@example.com"
    guid: "..."
    aliases: ["jane", "smith", "js"]
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

1. Read existing `~/.claude/devops.md` -- preserve role, `process`, `enforcement`,
   `roleRules`/`taskNaming` overrides, custom aliases, preferences
2. Re-fetch from API: identity, projects, team members, repositories. If the profile has
   no `process` field (profiles from before process presets), run Step 3.5 and add it --
   without it the hook applies generic rules only (no role or naming rules)
3. Merge: keep user customizations, update API-sourced data
4. Write updated file
5. Report changes:
   ```
   Profile refreshed. Changes:
   - 1 new project added: Project Gamma
   - 2 new team members: Bob, Carol
   - Repositories updated for Project Alpha (+1)
   ```
