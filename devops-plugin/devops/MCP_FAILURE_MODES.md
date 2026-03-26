# MCP Server Failure Modes & Recovery

When the Azure DevOps MCP server (`@anthropic-ai/azure-devops-mcp`) is unavailable or errors occur, use this guide for recovery and CLI fallback.

---

## 1. MCP Server Startup Failures

**Symptoms**: "MCP server unavailable", "Cannot connect to azure-devops", tools not appearing

**Common Causes**:
- `npx` installation failed (network issue, npm registry down)
- Node.js not installed or wrong version (requires 16+)
- Environment variables not set (`ADO_PAT_TOKEN`, `ADO_ORGANIZATION`)

**Recovery**:
1. Check Node.js: `node --version` (expect 16+)
2. Check npx: `npx --version`
3. Verify env vars: `echo $ADO_PAT_TOKEN` (should not be empty)
4. Reinstall: Run `/init` to reconfigure MCP server
5. Manual test: `npx -y @anthropic-ai/azure-devops-mcp@latest`

**Prevention**: Pin MCP version in `.mcp.json` instead of using `@latest` for production stability.

---

## 2. Authentication Failures

**Symptoms**: 401 Unauthorized, "token expired", "authentication failed"

**Recovery**:
1. Regenerate PAT at `https://dev.azure.com/{org}/_usersSettings/tokens`
2. Required scopes: **Code** (Read/Write), **Work Items** (Read/Write), **Build** (Read/Execute)
3. Set env var: `export ADO_PAT_TOKEN="your-new-pat"`
4. Verify: `az devops login` (for CLI fallback)

**CLI Fallback**: `az login` uses device code authentication (no PAT needed).

**Prevention**: PAT expires after 1 year max. Set a calendar reminder to regenerate before expiry.

---

## 3. Tool Timeouts & Rate Limits

**Symptoms**: Tool calls hang >30s, 429 errors, "rate limit exceeded"

**Affected Tools**: `search_workitem`, `search_code`, `repo_get_commits` (large result sets)

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

**Cause**: `@latest` in `.mcp.json` pulled a breaking MCP server update.

**Recovery**:
1. Check current version: `npx @anthropic-ai/azure-devops-mcp --version`
2. Pin to known-good version in `.mcp.json`: change `@latest` to `@6.2.0`
3. Clear npx cache: `npx clear-npx-cache`

**Prevention**: Pin the MCP server version in `.mcp.json` for production use.
