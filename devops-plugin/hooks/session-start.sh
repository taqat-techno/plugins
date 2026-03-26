#!/usr/bin/env bash
# SessionStart hook: Profile check + staleness detection
# Reads JSON on stdin (required). Checks ~/.claude/devops.md.
# Exit 0 always. Stdout becomes conversation context.

INPUT=$(cat)

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROFILE_PATH="$HOME/.claude/devops.md"
DEFAULTS_FILE="$PLUGIN_ROOT/data/project_defaults.json"

if [ ! -f "$PROFILE_PATH" ]; then
  echo "[DevOps] Profile not configured. Run /init profile to set up your identity, role, team members, and state permissions."
  exit 0
fi

# Read configurable staleness threshold (default 14 days)
STALENESS_DAYS=14
if [ -f "$DEFAULTS_FILE" ] && command -v python3 &>/dev/null; then
  CONFIGURED=$(python3 -c "
import json, sys
try:
    with open('$DEFAULTS_FILE') as f:
        print(json.load(f).get('workTracking', {}).get('profileStalenessThresholdDays', 14))
except:
    print(14)
" 2>/dev/null)
  [ -n "$CONFIGURED" ] && STALENESS_DAYS="$CONFIGURED"
fi

# Profile exists -- check staleness
LAST_REFRESH=$(grep -E '^lastRefresh:|^lastUpdated:' "$PROFILE_PATH" | head -1 | sed 's/^[^:]*:[[:space:]]*//' | tr -d '"' | tr -d "'")

if [ -n "$LAST_REFRESH" ] && command -v python3 &>/dev/null; then
  DAYS_OLD=$(python3 -c "
from datetime import datetime, date
try:
    d = datetime.strptime('$LAST_REFRESH'.strip()[:10], '%Y-%m-%d').date()
    print((date.today() - d).days)
except:
    print(0)
" 2>/dev/null)

  if [ -n "$DAYS_OLD" ] && [ "$DAYS_OLD" -gt "$STALENESS_DAYS" ] 2>/dev/null; then
    echo "[DevOps] Profile loaded but last refreshed ${DAYS_OLD} days ago (threshold: ${STALENESS_DAYS}d). Run /init profile --refresh to update."
  fi
fi

# ── Lightweight consistency checks ──────────────────────────────

# 1. JSON syntax validation (core data files)
for JSON_FILE in "$PLUGIN_ROOT/data/state_machine.json" "$PLUGIN_ROOT/data/project_defaults.json" "$PLUGIN_ROOT/data/hierarchy_rules.json"; do
  if [ -f "$JSON_FILE" ] && command -v python3 &>/dev/null; then
    if ! python3 -c "import json; json.load(open('$JSON_FILE'))" 2>/dev/null; then
      echo "[DevOps] WARNING: $(basename $JSON_FILE) has invalid JSON syntax. Plugin data may be corrupted."
    fi
  fi
done

# 2. Plugin version check
PLUGIN_JSON="$PLUGIN_ROOT/.claude-plugin/plugin.json"
if [ -f "$PLUGIN_JSON" ] && command -v python3 &>/dev/null; then
  PLUGIN_VER=$(python3 -c "import json; print(json.load(open('$PLUGIN_JSON')).get('version',''))" 2>/dev/null)
  if [ -n "$PLUGIN_VER" ] && ! echo "$PLUGIN_VER" | grep -q '^6\.'; then
    echo "[DevOps] WARNING: Plugin version '$PLUGIN_VER' is not 6.x. Expected v6+."
  fi
fi

# 3. Profile schema version check
if [ -f "$PROFILE_PATH" ] && command -v python3 &>/dev/null; then
  PROFILE_VER=$(grep -E '^schemaVersion:' "$PROFILE_PATH" | head -1 | sed 's/^schemaVersion:[[:space:]]*//' | tr -d '"')
  MIN_SCHEMA=$(python3 -c "import json; print(json.load(open('$DEFAULTS_FILE')).get('compatibility', {}).get('minProfileSchema', '6.0.0'))" 2>/dev/null)
  if [ -n "$PROFILE_VER" ] && [ -n "$MIN_SCHEMA" ]; then
    PROFILE_MAJOR=$(echo "$PROFILE_VER" | cut -d. -f1)
    MIN_MAJOR=$(echo "$MIN_SCHEMA" | cut -d. -f1)
    if [ "$PROFILE_MAJOR" -lt "$MIN_MAJOR" ] 2>/dev/null; then
      echo "[DevOps] Profile schema version '$PROFILE_VER' is older than required '$MIN_SCHEMA'. Run /init profile --refresh to upgrade."
    fi
  fi
fi

# 4. Core data file existence
for DATA_FILE in "state_machine.json" "hierarchy_rules.json" "project_defaults.json"; do
  if [ ! -f "$PLUGIN_ROOT/data/$DATA_FILE" ]; then
    echo "[DevOps] WARNING: data/$DATA_FILE is missing. Plugin may not function correctly."
  fi
done

# 4. Profile required fields check
for FIELD in "role:" "defaultProject:" "teamMembers:"; do
  if ! grep -q "^$FIELD" "$PROFILE_PATH"; then
    echo "[DevOps] Profile missing '$FIELD'. Run /init profile to complete setup."
  fi
done

# Extract role for session context — only warn if missing
USER_ROLE=$(grep -E '^role:' "$PROFILE_PATH" | head -1 | sed 's/^role:[[:space:]]*//' | tr -d '"')
DEFAULT_PROJECT=$(grep -E '^defaultProject:' "$PROFILE_PATH" | head -1 | sed 's/^defaultProject:[[:space:]]*//' | tr -d '"')

if [ -n "$USER_ROLE" ] && [ -n "$DEFAULT_PROJECT" ]; then
  # Silent load -- don't add noise when everything is configured
  exit 0
fi

exit 0
