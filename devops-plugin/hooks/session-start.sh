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

# ── Lightweight consistency checks (consolidated into single Python call) ──

# Checks: JSON syntax, data file existence, plugin version, profile schema
if [ -n "$PYTHON" ]; then
  $PYTHON -c "
import json, os, sys
root = r'$PLUGIN_ROOT'
profile = r'$PROFILE_PATH'
errors = []

# 1. Core data file existence + JSON syntax validation
for f in ['state_machine.json', 'hierarchy_rules.json', 'project_defaults.json']:
    p = os.path.join(root, 'data', f)
    if not os.path.isfile(p):
        errors.append(f'WARNING: data/{f} is missing. Plugin may not function correctly.')
    else:
        try:
            json.load(open(p))
        except Exception:
            errors.append(f'WARNING: {f} has invalid JSON syntax. Plugin data may be corrupted.')

# 2. Plugin version check
pj = os.path.join(root, '.claude-plugin', 'plugin.json')
if os.path.isfile(pj):
    try:
        v = json.load(open(pj)).get('version', '')
        if v and not v.startswith('6.'):
            errors.append(f\"WARNING: Plugin version '{v}' is not 6.x. Expected v6+.\")
    except Exception:
        pass

# 3. Profile schema version check
defaults_file = os.path.join(root, 'data', 'project_defaults.json')
if os.path.isfile(profile) and os.path.isfile(defaults_file):
    try:
        with open(profile) as pf:
            for line in pf:
                if line.startswith('schemaVersion:'):
                    profile_ver = line.split(':', 1)[1].strip().strip('\"').strip(\"'\")
                    break
            else:
                profile_ver = None
        if profile_ver:
            defaults = json.load(open(defaults_file))
            min_schema = defaults.get('compatibility', {}).get('minProfileSchema', '6.0.0')
            p_major = int(profile_ver.split('.')[0])
            m_major = int(min_schema.split('.')[0])
            if p_major < m_major:
                errors.append(f\"Profile schema version '{profile_ver}' is older than required '{min_schema}'. Run /init profile --refresh to upgrade.\")
    except Exception:
        pass

for e in errors:
    print(f'[DevOps] {e}')
" 2>/dev/null
else
  # No Python available — do basic file existence check with bash
  for DATA_FILE in "state_machine.json" "hierarchy_rules.json" "project_defaults.json"; do
    if [ ! -f "$PLUGIN_ROOT/data/$DATA_FILE" ]; then
      echo "[DevOps] WARNING: data/$DATA_FILE is missing. Plugin may not function correctly."
    fi
  done
fi

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
