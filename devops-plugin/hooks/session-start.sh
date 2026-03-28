#!/usr/bin/env bash
# SessionStart hook: Profile check + staleness detection
# Reads JSON on stdin (required). Checks ~/.claude/devops.md.
# Exit 0 always. Stdout becomes conversation context.

INPUT=$(cat)

# ── Windows path fix ──────────────────────────────────────────
# Git Bash pwd returns /c/Users/... which Python cannot resolve.
# Convert to C:/Users/... for cross-tool compatibility.
fix_path() {
  local p="$1"
  if [[ "$p" =~ ^/([a-zA-Z])/ ]]; then
    echo "${BASH_REMATCH[1]}:/${p:3}"
  else
    echo "$p"
  fi
}

PLUGIN_ROOT="$(fix_path "$(cd "$(dirname "$0")/.." && pwd)")"
PROFILE_PATH="$(fix_path "$HOME/.claude/devops.md")"
DEFAULTS_FILE="$PLUGIN_ROOT/data/project_defaults.json"

# Prefer python3, fall back to python (Windows)
PYTHON=""
if command -v python3 &>/dev/null; then
  PYTHON="python3"
elif command -v python &>/dev/null; then
  PYTHON="python"
fi

if [ ! -f "$PROFILE_PATH" ]; then
  echo "[DevOps] Profile not configured. Run /init profile to set up your identity, role, team members, and state permissions."
  exit 0
fi

# Read configurable staleness threshold (default 14 days)
STALENESS_DAYS=14
if [ -f "$DEFAULTS_FILE" ] && [ -n "$PYTHON" ]; then
  CONFIGURED=$($PYTHON -c "
import json, sys
try:
    with open(r'$DEFAULTS_FILE') as f:
        print(json.load(f).get('workTracking', {}).get('profileStalenessThresholdDays', 14))
except:
    print(14)
" 2>/dev/null)
  [ -n "$CONFIGURED" ] && STALENESS_DAYS="$CONFIGURED"
fi

# Profile exists -- check staleness
LAST_REFRESH=$(grep -E '^lastRefresh:|^lastUpdated:' "$PROFILE_PATH" | head -1 | sed 's/^[^:]*:[[:space:]]*//' | tr -d '"' | tr -d "'")

if [ -n "$LAST_REFRESH" ] && [ -n "$PYTHON" ]; then
  DAYS_OLD=$($PYTHON -c "
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

# 1. JSON syntax validation (core data files) — use raw string paths for Python
for JSON_FILE in "$PLUGIN_ROOT/data/state_machine.json" "$PLUGIN_ROOT/data/project_defaults.json" "$PLUGIN_ROOT/data/hierarchy_rules.json"; do
  if [ -f "$JSON_FILE" ] && [ -n "$PYTHON" ]; then
    if ! $PYTHON -c "import json; json.load(open(r'$JSON_FILE'))" 2>/dev/null; then
      echo "[DevOps] WARNING: $(basename "$JSON_FILE") has invalid JSON syntax. Plugin data may be corrupted."
    fi
  fi
done

# 2. Plugin version check
PLUGIN_JSON="$PLUGIN_ROOT/.claude-plugin/plugin.json"
if [ -f "$PLUGIN_JSON" ] && [ -n "$PYTHON" ]; then
  PLUGIN_VER=$($PYTHON -c "import json; print(json.load(open(r'$PLUGIN_JSON')).get('version',''))" 2>/dev/null)
  if [ -n "$PLUGIN_VER" ] && ! echo "$PLUGIN_VER" | grep -q '^6\.'; then
    echo "[DevOps] WARNING: Plugin version '$PLUGIN_VER' is not 6.x. Expected v6+."
  fi
fi

# 3. Profile schema version check
if [ -f "$PROFILE_PATH" ] && [ -n "$PYTHON" ]; then
  PROFILE_VER=$(grep -E '^schemaVersion:' "$PROFILE_PATH" | head -1 | sed 's/^schemaVersion:[[:space:]]*//' | tr -d '"')
  MIN_SCHEMA=$($PYTHON -c "import json; print(json.load(open(r'$DEFAULTS_FILE')).get('compatibility', {}).get('minProfileSchema', '6.0.0'))" 2>/dev/null)
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

# 5. Profile required fields check
# Support both YAML format (role:), Markdown table (| **Label** |), and Markdown heading (## Label)
check_profile_field() {
  local yaml_key="$1"
  local md_label="$2"
  if ! grep -qi "^${yaml_key}\b" "$PROFILE_PATH" \
     && ! grep -qi "|\s*\*\*${md_label}\*\*\s*|" "$PROFILE_PATH" \
     && ! grep -qi "^##.*${md_label}" "$PROFILE_PATH"; then
    echo "[DevOps] Profile missing '${yaml_key}'. Run /init profile to complete setup."
  fi
}

check_profile_field "role" "Primary Role"
check_profile_field "defaultProject" "Default Project"
check_profile_field "teamMembers" "Team Members"

# Extract role for session context — only warn if missing
USER_ROLE=$(grep -E '^role:|Primary Role' "$PROFILE_PATH" | head -1 | sed 's/.*|\s*//' | tr -d '*|' | xargs)
DEFAULT_PROJECT=$(grep -E '^defaultProject:|Default Project' "$PROFILE_PATH" | head -1 | sed 's/.*|\s*//' | tr -d '*|' | xargs)

if [ -n "$USER_ROLE" ] && [ -n "$DEFAULT_PROJECT" ]; then
  # Silent load -- don't add noise when everything is configured
  exit 0
fi

exit 0
