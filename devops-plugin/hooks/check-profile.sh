#!/usr/bin/env bash
# SessionStart hook: Check if DevOps profile exists
# Reads JSON on stdin (Claude Code standard), checks ~/.claude/devops.md
# Exit 0 always. Stdout text becomes conversation context.

# Consume stdin (required even if unused)
INPUT=$(cat)

# Determine profile path
PROFILE_PATH="$HOME/.claude/devops.md"

if [ -f "$PROFILE_PATH" ]; then
  # Profile exists -- stay silent, don't add noise
  exit 0
else
  # Profile missing -- output setup reminder
  echo "[DevOps] Profile not configured. Run /init profile to set up your identity, role, team members, and state permissions for faster Azure DevOps operations."
  exit 0
fi
