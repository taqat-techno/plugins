# MCP Server Failure Modes & Recovery

When the Azure DevOps MCP server (`@azure-devops/mcp`, pinned at 2.8.0) is unavailable or errors occur, use this guide for recovery and CLI fallback.

---

## 1. MCP Server Startup Failures

**Symptoms**: "MCP server unavailable", "Cannot connect to azure-devops", tools not appearing

**Common Causes**:
- `npx` installation failed (network issue, npm registry down)
- Node.js missing or old (use a current LTS, 20 or later)
- No organization or token: neither the plugin options (`ado_organization`, `ado_token` in `/config`) nor the `ADO_ORGANIZATION` / `ADO_MCP_AUTH_TOKEN` env vars are set. The launcher then exits with a message that `/mcp` shows

**Recovery**:
1. Check Node.js: `node --version`
2. Check npx: `npx --version`
3. Check the token is set without printing it: `[ -n "$ADO_MCP_AUTH_TOKEN" ] && echo set`, or look at the plugin options in `/config`
4. Reconfigure: run `/init`
5. Manual test (same pinned version the plugin uses): `npx -y @azure-devops/mcp@2.8.0 <org> --authentication envvar`

**Never** switch to `@latest`: 2.9.0 renamed every tool and breaks this plugin's hooks, agents and rules.

---

## 2. Authentication Failures

**Symptoms**: 401 Unauthorized, "token expired", "authentication failed"

**Recovery**:
1. Regenerate PAT at `https://dev.azure.com/{org}/_usersSettings/tokens`
2. Scopes: grant the narrowest set you need, typically **Work Items** (Read & Write), **Code** (Read & Write) and **Build** (Read). Add **Build (Read & Execute)** only to run pipelines
3. Put the new PAT in the `ado_token` plugin option (`/config`), or update the `ADO_MCP_AUTH_TOKEN` env var in your shell profile (not on the command line, where it lands in history)
4. Verify: `az devops login` (for CLI fallback)

**CLI Fallback**: `az login` uses device code authentication (no PAT needed).

**Prevention**: PAT expires after 1 year max. Set a calendar reminder to regenerate before expiry.

---

## 3. Tool Timeouts & Rate Limits

**Symptoms**: Tool calls hang >30s, 429 errors, "rate limit exceeded"

**Affected Tools**: `search_workitem`, `search_code`, `repo_search_commits` (large result sets)

**Recovery**:
1. Narrow query scope — filter by project, date range, or iteration
2. For rate limits: wait 60s before retrying
3. Batch operations: use CLI for bulk updates (`/cli-run`)
4. For persistent timeouts: check Azure DevOps service status

**Limits**: 200 requests/minute per user, max 200 items per batch, max 20,000 query results.

---

## 4. Graceful Degradation — CLI Fallback Matrix

When MCP is unavailable, the CLI (`az devops`) can handle many operations:

| Capability | MCP | CLI Fallback | CLI Command |
|-----------|:---:|:---:|-------------|
| Work item queries | Y | Y | `az boards query --wiql "..."` |
| Work item CRUD | Y | Y | `az boards work-item create/update` |
| PR creation | Y | Y | `az repos pr create` |
| PR review/threads | Y | Partial | `az repos pr list` (no threads) |
| Pipeline runs | Y | Y | `az pipelines run` |
| Build logs | Y | Y | `az pipelines runs show` |
| Test plans/cases | Y | N | MCP only |
| Code/wiki search | Y | N | MCP only |
| Security alerts | Y | N | MCP only |
| Team capacity | Y | N | MCP only |

**To use CLI fallback**: Use `/cli-run` command for direct Azure DevOps CLI access.

**Note**: CLI operations bypass the plugin's write-gate, state validation, and mention resolution guards. Use MCP workflows when possible for safety.

---

## 5. Version Incompatibilities

**Symptoms**: "Unknown tool" errors, changed parameter names, missing tools

**Cause**: a different server version than the one this plugin is built for, usually from a second `azure-devops` entry in `~/.claude/.mcp.json` that uses `@latest`.

**Recovery**:
1. Run `/init`; Step 2 finds a duplicate global server entry
2. The plugin's own launcher always runs `@azure-devops/mcp@2.8.0`. Do not change it: 2.9.0 collapses the 90 tools into 37 renamed ones
3. Clear a corrupt npx cache if the pinned version fails to install: delete the `_npx` folder in the npm cache (`npm config get cache`)
