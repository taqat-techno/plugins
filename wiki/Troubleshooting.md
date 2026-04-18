# Troubleshooting

Common issues across the marketplace, ordered by frequency. For plugin-specific diagnostics, see each plugin's own page — `rag-plugin` in particular has a rich failure catalog (F-001..F-012) and walkable playbooks in [`rag-plugin/skills/ragtools-ops/references/repair-playbooks.md`](../../rag-plugin/skills/ragtools-ops/references/repair-playbooks.md).

## Marketplace-level issues

### Plugins don't appear after installation

**Symptoms:** `/plugins` doesn't list the marketplace or lists it but shows zero plugins.

**Causes and fixes:**

1. **Claude Code hasn't restarted** since install. Restart Claude Code; re-run `/plugins`.
2. **Marketplace directory missing.** Verify:
   ```bash
   # macOS / Linux
   ls ~/.claude/plugins/marketplaces/taqat-techno-plugins/
   # Windows
   dir %USERPROFILE%\.claude\plugins\marketplaces\taqat-techno-plugins\
   ```
   If missing, re-run installation ([[Installation and Usage|Installation-and-Usage]]).
3. **Marketplace manifest broken.**
   ```bash
   cat ~/.claude/plugins/marketplaces/taqat-techno-plugins/.claude-plugin/marketplace.json | python -m json.tool
   ```
   If JSON parse fails, `git pull` inside the marketplace dir to recover; if still broken, open an issue.
4. **Plugin directory exists but no manifest entry.** Plugins not registered in `marketplace.json` are invisible. The validator does not catch this — check the marketplace README or compare `ls plugins/` against `marketplace.json` plugin entries.

### Cache-vs-source drift (after updating)

**Symptoms:** you updated the plugin source but Claude Code is running the old behavior.

**Reason:** Claude Code runs plugins from the **cache** at `~/.claude/plugins/cache/<marketplace>/`, not from your source checkout. Source changes are invisible until the cache is refreshed.

**Fix:**

```bash
cd ~/.claude/plugins/marketplaces/taqat-techno-plugins
git pull
```

Then restart Claude Code. This is the #1 "my fix isn't working" cause during development — documented in [`HOOK_STABILIZATION_REPORT.md`](../../HOOK_STABILIZATION_REPORT.md).

### Marketplace README shows plugins that don't exist

**Symptoms:** the table in `plugins/README.md` lists plugin X but clicking through returns 404.

**Reason:** stale marketplace README. Fixed by the Apr 2026 rewrite; if you see it again, the catalog needs re-sync with the filesystem.

**Fix:** edit `plugins/README.md` to reflect what's actually in `plugins/` + `marketplace.json`. See [[Contribution Guide|Contribution-Guide]] for the dual-location update rule.

## MCP server issues

### `/mcp` shows server as "disconnected"

**Symptoms:** the plugin is installed, but its MCP server (`ragtools`, `azure-devops`, etc.) isn't connected in the Claude Code session.

**Common causes:**

1. **Target binary not on PATH.**
   - For `rag-plugin`: `where rag` (Windows) / `which rag` (POSIX) must resolve. The RAGTools installer adds `rag.exe` to PATH by default; verify the installer's "Add to PATH" option was checked.
   - For `devops-plugin`: `where npx` must resolve; Node.js + npx is required for the Azure DevOps MCP.
2. **Wrong schema shape in `.mcp.json`.** Plugin-level `.mcp.json` must use the **flat shape** (no `mcpServers` wrapper). If someone edited it to the wrapped shape, no tools load. See [[Architecture]] §MCP.
3. **Python launcher wrapping on Windows.** If a plugin's `.mcp.json` runs `python <script>` instead of the binary directly, Python's `os.execvp` on Windows breaks the stdio pipe. Spawn the binary directly. See `rag-plugin` D-020.
4. **First-run cold start.** MCP servers launched via `npx` (like Azure DevOps) can take 5–10 seconds on their first invocation while npx downloads the package. Wait and re-run `/mcp`.

**Diagnosis:** for the `rag-plugin` MCP specifically, run `/rag-config mcp-dedupe status` — it reports schema validity, command-on-PATH, launcher presence, and duplicate registrations.

### Tools registered but can't be called

**Symptoms:** `/mcp` shows the server as "connected" but `mcp__plugin_<name>__<tool>` isn't callable.

**Reason:** the tool is disabled in the server's config. Debug tools in `rag-plugin`'s MCP default OFF and require user grant in the admin panel.

**Fix:** open the relevant admin UI (for ragtools: `http://127.0.0.1:21420/config`), toggle the tool under "MCP Tool Access", save, **restart Claude Code** (MCP servers read settings once at startup).

## Hook issues

### Session-start hook error or slow startup

**Symptoms:** Claude Code reports "hook error" on session start, or startup takes > 5 seconds.

**Common causes from [`HOOK_STABILIZATION_REPORT.md`](../../HOOK_STABILIZATION_REPORT.md):**

1. **Source/cache desync** — hooks in source use `${CLAUDE_PLUGIN_ROOT}/../_infrastructure/hook-runner.sh` (relative path traversal). That path cannot resolve inside the cache. Fix: hooks should use `${CLAUDE_PLUGIN_ROOT}/hooks/<script>` directly.
2. **Non-standard JSON output.** Official SessionStart hooks output `{hookSpecificOutput: {additionalContext: "..."}}`. Plain text stdout causes "hook error".
3. **Python interpreter startup overhead.** A hook that runs `python <script>` spawns an interpreter each time. For hooks that fire on every `Bash` / `Write` / `Edit`, this adds significant latency. Use bash or pre-compiled Python.

### PreToolUse hook blocks everything

**Symptoms:** every tool call is blocked with a hook denial.

**Diagnosis:** run `ls ~/.claude/plugins/cache/taqat-techno-plugins/<plugin>/hooks/hooks.json`. Look for entries with `permissionDecision: "deny"`.

**Fix:** per the house convention — hooks should use `"ask"`, never silent `"deny"`. Find the blocking hook, change to ask, re-cache.

## Plugin-specific issues

### `/rag-doctor` says service is down but `rag service status` says up

**Reason:** F-010 in the `rag-plugin` failure catalog — when the MCP tool runs `rag doctor` while the service holds the Qdrant lock, `rag doctor` cannot open the collection. This is **expected**, not a bug. The plugin's `--full` mode tags this as `[INFO]` and does not route to a repair playbook.

**Fix:** no action needed. Use `/rag-doctor` default mode (via MCP `index_status`) or `curl /api/status` via HTTP — both see the live service correctly.

### Odoo upgrade leaves `attrs={}` residues

**Reason:** `attrs` removal is a known gap in the `odoo-plugin` upgrade pattern library (documented in [`PLUGIN_ENHANCEMENT_REPORT_FEB_2026.md`](../../PLUGIN_ENHANCEMENT_REPORT_FEB_2026.md) §3). The pattern library knows about it but the auto-fix coverage is partial.

**Fix:** run `/odoo-quickfix` and manually review the reported residues. Full fix coming in a future version of the upgrade pattern library.

### ntfy notifications not arriving

**Causes and fixes:**

1. **Topic mismatch.** The phone app subscribed to one topic; `/ntfy config` has a different one. Re-run `/ntfy setup`.
2. **Server unreachable.** `ping ntfy.sh` must work. For self-hosted, verify the server URL in `~/.claude/ntfy-plugin/config.json`.
3. **Rate-limited on ntfy.sh public instance.** Soft limit; wait a few minutes or self-host.
4. **App permissions.** iOS silently drops notifications for apps without granted notification permissions. Check Settings → Notifications → ntfy.

### `/pandoc convert` fails with "pandoc: command not found"

**Fix:** run `/pandoc setup` — it auto-installs Pandoc + LaTeX. If the auto-install path fails (no package manager access), install manually from [pandoc.org](https://pandoc.org/installing.html).

### `/remotion` render is very slow

**Reason:** Remotion rendering is CPU-bound by design. No GPU acceleration out of the box.

**Mitigations:**

- Shorter videos, fewer effects.
- Render on a workstation rather than a laptop.
- Use lower output resolution during iteration; re-render at full resolution once the composition is finalized.

## Diagnostic commands per plugin

| Plugin | Diagnostic command |
|---|---|
| odoo | `/odoo-service` (lifecycle status) |
| devops | `/init` (re-run to validate auth + connectivity) |
| rag | `/rag-doctor --full --fix` (structured diagnosis + inline repair) |
| paper | `/paper` (status + Figma MCP check) |
| pandoc | `/pandoc status` |
| remotion | `/remotion` (status only, no args) |
| ntfy | `/ntfy status` then `/ntfy test` |

## When you're stuck

1. **Check the plugin's CHANGELOG.** Recent commits often document known issues and workarounds.
2. **Check the plugin's `ARCHITECTURE.md` or `docs/decisions.md`** if present. The binding decisions frequently document why something is the way it is.
3. **Check the workspace-level reports**:
   - [`HOOK_STABILIZATION_REPORT.md`](../../HOOK_STABILIZATION_REPORT.md) — hook ecosystem issues.
   - [`HOOK_AUDIT_REPORT.md`](../../HOOK_AUDIT_REPORT.md) — audit findings.
   - [`PLUGIN_ENHANCEMENT_REPORT_FEB_2026.md`](../../PLUGIN_ENHANCEMENT_REPORT_FEB_2026.md) — plugin-by-plugin gap analysis.
4. **Open an issue** at [github.com/taqat-techno/plugins/issues](https://github.com/taqat-techno/plugins/issues) with:
   - Claude Code version
   - OS and shell
   - Plugin name and version (`cat plugins/<name>-plugin/.claude-plugin/plugin.json`)
   - Exact error message
   - Steps to reproduce

## See also

- [[Plugin Catalog|Plugin-Catalog]] — all plugins with component details
- Individual plugin pages — plugin-specific failure modes and playbooks
- [[Architecture]] — the design patterns these issues often trace back to
