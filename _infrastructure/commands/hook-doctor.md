---
description: Diagnose, test, and manage hook health across all plugins
author: TaqaTechno
version: 1.0.0
---

You are implementing the `/hook-doctor` command — a diagnostics tool for the Claude Code plugin hook ecosystem.

## Available Subcommands

The user will invoke one of these:

### `/hook-doctor status`
List all registered hooks across all plugins. For each hook:
1. Read every `hooks/hooks.json` file in `C:\TQ-WorkSpace\odoo\tmp\plugins\*\hooks\hooks.json`
2. For each hook entry, display: plugin name, hook name, event type (SessionStart/PreToolUse/PostToolUse/PostToolUseFailure), execution type (command/prompt), timeout value, whether it's blocking (PreToolUse + exit 2), matcher pattern
3. Check if safe mode is active by reading `~/.claude/hook-safe-mode.json`
4. Mark any disabled hooks/plugins from the safe-mode file

Output as a formatted table.

### `/hook-doctor test <plugin> <hook>`
Run a specific hook script in isolation:
1. Locate the script at `C:\TQ-WorkSpace\odoo\tmp\plugins\<plugin>\hooks\<hook>`
2. Create synthetic stdin JSON: `{"tool_input": {"file_path": "test/example.py", "content": "# test content"}}`
3. Execute the script with timeout, capture stdout, stderr, exit code, and duration
4. Report results including whether exit code is 0 (allow) or 2 (block)

### `/hook-doctor audit [--last=N]`
Read the hook audit log at `~/.claude/logs/hook-audit.jsonl`:
1. Parse the last N entries (default 50)
2. Summarize: total invocations, unique hooks, slowest hooks (top 5), hooks with errors, hooks that timed out, hooks that blocked actions
3. Show average duration per hook

### `/hook-doctor safe-mode on [--plugin=X] [--hook=Y]`
Activate safe mode:
1. Write `~/.claude/hook-safe-mode.json` with `enabled: true`
2. If `--plugin` specified, add to `disabled_plugins` array
3. If `--hook` specified, add to `disabled_hooks` array
4. If neither specified, set `allow_prompt_only: true` (disables ALL command hooks)
5. Confirm activation with details

### `/hook-doctor safe-mode off`
Deactivate safe mode:
1. Write `~/.claude/hook-safe-mode.json` with `enabled: false`
2. Clear all disabled lists
3. Confirm deactivation

### `/hook-doctor overlaps`
Analyze hook overlap across plugins:
1. Read all hooks.json files
2. For each PostToolUse hook with a path/filePattern, group by pattern
3. Report patterns that trigger 2+ plugins
4. Cross-reference with HOOK_OWNERSHIP.md to identify violations

### `/hook-doctor health`
Run a comprehensive health check:
1. Verify all hook scripts exist and are accessible
2. Check Python availability (needed for .py hooks)
3. Check bash availability
4. Run each SessionStart hook with timing
5. Verify hook-runner.sh exists and is executable
6. Verify log directory exists
7. Check if any hooks.json files have syntax errors
8. Report overall health score

## Implementation Notes

- All paths use the plugins root: `C:\TQ-WorkSpace\odoo\tmp\plugins\`
- Safe-mode sentinel: `~/.claude/hook-safe-mode.json`
- Audit log: `~/.claude/logs/hook-audit.jsonl`
- Ownership registry: `_infrastructure/HOOK_OWNERSHIP.md`
- Use Glob to find all hooks.json files
- Use Read to parse each one
- Use Bash to run scripts in isolation (for test subcommand)
- Always report results in formatted tables
