#!/usr/bin/env bash
# PreToolUse/Bash hook: Check git commit messages for work item references
# Reads JSON on stdin. Extracts tool_input.command.
# Exit 0 always (never blocks). Stdout becomes additionalContext.

INPUT=$(cat)

# Extract the command being run
COMMAND=$(echo "$INPUT" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"command"[[:space:]]*:[[:space:]]*"//' | sed 's/"$//')

# Check if this is a git commit command
if echo "$COMMAND" | grep -qiE 'git\s+commit'; then
  # Check if commit message contains a work item reference (#NNN)
  if ! echo "$COMMAND" | grep -qE '#[0-9]+'; then
    echo "[DevOps] Tip: Include a work item ID in your commit message (e.g., 'Fix #1234: description') for automatic Azure DevOps linking."
  fi
fi

exit 0
