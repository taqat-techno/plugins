#!/usr/bin/env bash
# PostToolUse/Bash hook: Contextual suggestions after git operations
# Reads JSON on stdin. Extracts tool_input.command.
# Exit 0 always. Stdout becomes conversation context.

INPUT=$(cat)

# Extract the command that was run
COMMAND=$(echo "$INPUT" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"command"[[:space:]]*:[[:space:]]*"//' | sed 's/"$//')

# Git commit completed
if echo "$COMMAND" | grep -qiE 'git\s+commit'; then
  echo "[DevOps] Code committed. Consider checking build status or running pipeline to verify changes."
  exit 0
fi

# Git push completed
if echo "$COMMAND" | grep -qiE 'git\s+push'; then
  echo "[DevOps] Code pushed. Consider creating a PR if on a feature branch, or check pipeline status."
  exit 0
fi

# Switched to feature/bugfix branch
if echo "$COMMAND" | grep -qiE 'git\s+(checkout|switch).*(feature|bugfix)'; then
  echo "[DevOps] Working on feature branch. When ready, create a PR with: 'Create PR from [branch] to main'"
  exit 0
fi

# No match -- output nothing
exit 0
