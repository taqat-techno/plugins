# Plugin Infrastructure

Shared infrastructure for the Claude Code plugin hook ecosystem.

## Components

| File | Purpose |
|------|---------|
| `hook-runner.sh` | Centralized wrapper for all command-type hooks (timeout, logging, safe-mode) |
| `safe-mode.json.template` | Template for `~/.claude/hook-safe-mode.json` sentinel file |
| `HOOK_OWNERSHIP.md` | Registry of which plugin owns each file-pattern hook |
| `commands/hook-doctor.md` | Diagnostics command for hook health, testing, and safe-mode control |

## Safe Mode

Copy `safe-mode.json.template` to `~/.claude/hook-safe-mode.json` and set `"enabled": true` to activate.

When active, the hook-runner wrapper skips command-type hooks for disabled plugins/hooks. Prompt-type hooks are unaffected (zero crash risk).

**Quick activation:**
```bash
cp _infrastructure/safe-mode.json.template ~/.claude/hook-safe-mode.json
# Then edit the file to set enabled=true and specify which plugins/hooks to disable
```

**Or use:** `/hook-doctor safe-mode on [--plugin=X] [--hook=Y]`

## Log Location

Hook audit logs: `~/.claude/logs/hook-audit.jsonl` (one JSON line per hook invocation).

## Timeout Convention

All timeouts in hooks.json are in **seconds** (matching devops-plugin convention: `"timeout": 10` = 10 seconds).
