# Migration Guide: v1.3 to v2.0

This guide helps you upgrade from DevOps Plugin v1.3.x to v2.0.0 (Hybrid Mode).

## Overview of Changes

### What's New in v2.0

| Category | v1.3 | v2.0 |
|----------|------|------|
| **Architecture** | MCP-only | Hybrid CLI + MCP |
| **Authentication** | MCP PAT only | CLI PAT + MCP PAT |
| **Commands** | 8 slash commands | 12 slash commands (+4 new) |
| **Scripts** | 4 Python scripts | 10 scripts (PowerShell + Python) |
| **Memories** | None | 6 predefined memory files |
| **Routing** | Manual | Intelligent auto-routing |

### Breaking Changes

**None.** Version 2.0 is fully backward compatible with v1.3. All existing commands and workflows continue to work.

### New Capabilities

1. **CLI Integration** - Direct Azure CLI access for CLI-only features
2. **Batch Operations** - Parallel work item updates
3. **Pipeline Variables** - Variable group management
4. **Extension Management** - Install marketplace extensions
5. **Predefined Memories** - Best practices loaded automatically
6. **Automation Scripts** - Ready-to-use PowerShell and Python scripts

---

## Prerequisites

### Existing Requirements (v1.3)
- Node.js 18+
- MCP Server configured
- Azure DevOps PAT token

### New Requirements (v2.0)
- Azure CLI 2.30+ (optional but recommended)
- Azure DevOps CLI extension (optional but recommended)
- Python 3.8+ (for hybrid scripts, optional)

---

## Migration Steps

### Step 1: Update Plugin Files

Copy the new plugin files to your plugins directory:

```bash
# If using git
cd ~/.claude/plugins/devops-plugin
git pull origin main

# If manual installation
# Download and replace the plugin directory
```

### Step 2: Verify Existing MCP Configuration

Your existing MCP configuration should continue to work. Verify in `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "azure-devops": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@anthropic-ai/azure-devops-mcp", "YOUR_ORGANIZATION"],
      "env": {
        "ADO_MCP_AUTH_TOKEN": "${ADO_PAT_TOKEN}"
      }
    }
  }
}
```

### Step 3: Install Azure CLI (Recommended)

For hybrid mode benefits, install Azure CLI:

**Windows (PowerShell):**
```powershell
winget install -e --id Microsoft.AzureCLI
```

**macOS:**
```bash
brew install azure-cli
```

**Linux:**
```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
```

### Step 4: Install DevOps Extension

```bash
az extension add --name azure-devops
```

### Step 5: Configure CLI Authentication

Set the PAT token for CLI:

**Windows (PowerShell):**
```powershell
[System.Environment]::SetEnvironmentVariable('AZURE_DEVOPS_EXT_PAT', 'your-pat-token', 'User')
```

**macOS/Linux:**
```bash
export AZURE_DEVOPS_EXT_PAT="your-pat-token"
# Add to ~/.bashrc or ~/.zshrc for persistence
```

### Step 6: Configure CLI Defaults

```bash
az devops configure --defaults organization=https://dev.azure.com/YOUR_ORG
az devops configure --defaults project="Your Project"
```

### Step 7: Verify Installation

Run the status command to verify both CLI and MCP are working:

```
/devops status
```

Expected output:
```
Azure DevOps Integration Status
================================
CLI Status:     ✅ Installed (v2.65.0)
MCP Status:     ✅ Connected
Hybrid Mode:    ✅ Enabled
Organization:   TaqaTechno
```

---

## Command Changes

### Existing Commands (Unchanged)

All v1.3 commands work exactly as before:

| Command | Status |
|---------|--------|
| `/devops` | ✅ Works (enhanced with CLI setup) |
| `/my-tasks` | ✅ Works |
| `/create-task` | ✅ Works |
| `/create-bug` | ✅ Works |
| `/create-user-story` | ✅ Works |
| `/standup` | ✅ Works |
| `/sprint` | ✅ Works |
| `/build-status` | ✅ Works |
| `/sync-my-tasks` | ✅ Works |

### New Commands (v2.0)

| Command | Description |
|---------|-------------|
| `/cli-run` | Execute any Azure CLI command |
| `/setup-pipeline-vars` | Manage pipeline variables (CLI-only) |
| `/install-extension` | Install marketplace extensions (CLI-only) |
| `/full-sprint-report` | Comprehensive hybrid sprint report |

---

## Feature Mapping

### v1.3 Features → v2.0 Equivalents

| v1.3 Feature | v2.0 Equivalent | Notes |
|--------------|-----------------|-------|
| MCP work item queries | Same | No change |
| @mention processing | Same | No change |
| State transition rules | Same | No change |
| Work item hierarchy | Same | No change |
| TODO sync | Same | No change |
| PR management | Same + CLI options | Enhanced with CLI |
| Sprint reports | Same + `/full-sprint-report` | New hybrid option |

### New v2.0 Features (No v1.3 Equivalent)

| Feature | How to Use |
|---------|------------|
| Pipeline variables | `/setup-pipeline-vars` command |
| Service connections | Direct CLI via `/cli-run` |
| Extension management | `/install-extension` command |
| Batch updates | `batch_update.ps1` script |
| Parallel operations | Scripts with `-Parallel` flag |
| Predefined memories | Auto-loaded by Claude |

---

## Environment Variables

### v1.3 Variables (Still Required)

| Variable | Purpose |
|----------|---------|
| `ADO_PAT_TOKEN` | MCP server authentication |

### v2.0 Variables (New)

| Variable | Purpose | Required |
|----------|---------|----------|
| `AZURE_DEVOPS_EXT_PAT` | CLI authentication | For CLI features |
| `DEVOPS_HYBRID_MODE` | Enable hybrid mode | Optional |

**Note:** You can use the same PAT token value for both `ADO_PAT_TOKEN` and `AZURE_DEVOPS_EXT_PAT`.

---

## Script Migration

### v1.3 Scripts (Still Available)

Located in `devops/scripts/`:
- `mention_helper.py` - @mention processing
- `pr_analyzer.py` - PR analysis
- `sprint_report.py` - MCP sprint reports
- `standup_helper.py` - Standup generation

### v2.0 Scripts (New)

**CLI Scripts** (`devops/scripts/cli/`):
- `install_cli.ps1` / `install_cli.sh` - CLI installers
- `configure_defaults.ps1` - CLI configuration
- `batch_update.ps1` - Bulk work item updates
- `sprint_report.ps1` - CLI sprint reports
- `pr_automation.ps1` - PR workflow automation

**Hybrid Scripts** (`devops/scripts/hybrid/`):
- `standup_generator.py` - Hybrid standup notes
- `sprint_planner.py` - Sprint planning with capacity
- `release_notes.py` - Release notes generator

---

## Memory Files

v2.0 introduces predefined memories in the `memories/` directory. These are automatically loaded by Claude for reference:

| Memory File | Purpose |
|-------------|---------|
| `cli_best_practices.md` | CLI command patterns |
| `mcp_best_practices.md` | MCP tool patterns |
| `automation_templates.md` | Reusable scripts |
| `wiql_queries.md` | 40+ WIQL query templates |
| `team_workflows.md` | TaqaTechno conventions |
| `hybrid_routing.md` | CLI vs MCP decisions |

No action required - these are loaded automatically.

---

## Hybrid Routing

v2.0 introduces intelligent routing. Claude automatically selects CLI or MCP based on the task:

### CLI is Selected For:
- Batch/parallel operations (performance)
- Pipeline variables (CLI-only)
- Service connections (CLI-only)
- Extensions (CLI-only)
- Project/repo creation (CLI-only)

### MCP is Selected For:
- Interactive queries (convenience)
- Code review threads (dedicated tools)
- Test plans (MCP-only)
- Security alerts (MCP-only)
- Search operations (MCP-only)
- Natural language requests (better UX)

You don't need to specify which to use - Claude decides automatically.

---

## Troubleshooting Migration

### Issue: CLI Not Detected

**Symptom:** `/devops status` shows CLI not installed

**Solution:**
1. Install Azure CLI for your platform
2. Install DevOps extension: `az extension add --name azure-devops`
3. Restart terminal/Claude Code

### Issue: CLI Authentication Failed

**Symptom:** CLI commands return "Not logged in"

**Solution:**
1. Set PAT environment variable:
   ```powershell
   [System.Environment]::SetEnvironmentVariable('AZURE_DEVOPS_EXT_PAT', 'your-pat', 'User')
   ```
2. Restart terminal
3. Test with: `az devops project list`

### Issue: MCP Still Works, CLI Doesn't

**Symptom:** MCP commands work, CLI commands fail

**Solution:**
This is expected if CLI is not installed. Hybrid mode is optional. You can:
1. Continue with MCP-only (v1.3 behavior)
2. Install CLI for full hybrid mode

### Issue: Scripts Not Found

**Symptom:** PowerShell scripts not executing

**Solution:**
1. Navigate to scripts directory: `cd devops/scripts/cli`
2. Check execution policy: `Get-ExecutionPolicy`
3. Allow scripts: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### Issue: Python Scripts Fail

**Symptom:** Hybrid Python scripts error

**Solution:**
1. Verify Python 3.8+: `python --version`
2. Verify Azure CLI installed: `az --version`
3. Check encoding: Scripts use UTF-8

---

## Rollback Instructions

If you need to revert to v1.3:

1. **Keep Configuration**: MCP settings remain unchanged
2. **Remove CLI**: Optional, doesn't affect MCP
3. **Restore Files**: Replace with v1.3 plugin files

```bash
# Git rollback
cd ~/.claude/plugins/devops-plugin
git checkout v1.3.0
```

---

## Frequently Asked Questions

### Q: Do I have to install CLI?
**A:** No. CLI is optional. MCP-only mode (v1.3 behavior) continues to work. CLI is only needed for CLI-only features like pipeline variables.

### Q: Can I use different PAT tokens?
**A:** Yes. You can use different tokens for CLI (`AZURE_DEVOPS_EXT_PAT`) and MCP (`ADO_PAT_TOKEN`) if needed for security.

### Q: Will my existing workflows break?
**A:** No. All v1.3 commands and workflows are fully backward compatible.

### Q: How do I know if hybrid mode is working?
**A:** Run `/devops status`. If both CLI and MCP show green checkmarks, hybrid mode is enabled.

### Q: Can I disable hybrid mode?
**A:** Yes. Simply don't install CLI. Claude will use MCP-only mode automatically.

---

## Support

- **Documentation**: See README.md for full documentation
- **Organization**: TaqaTechno
- **Email**: info@taqatechno.com

---

*Migration Guide - DevOps Plugin v2.0.0*
