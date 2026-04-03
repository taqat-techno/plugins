#!/usr/bin/env bash
# SessionStart hook: Profile check + staleness detection
# Outputs JSON in official hookSpecificOutput format.
# Exit 0 always. Fail-open on timeout.

# ── Internal timeout: fail-open after 8 seconds ──────────────────────────
# SessionStart hooks must NEVER hang. If Python is slow or missing, bail.
( sleep 8 && kill -9 $$ 2>/dev/null ) &
_TIMEOUT_PID=$!
trap 'kill $_TIMEOUT_PID 2>/dev/null; echo "{\"hookSpecificOutput\":{\"hookEventName\":\"SessionStart\",\"additionalContext\":\"\"}}"' EXIT

INPUT=$(cat)

# ── Windows path fix ──────────────────────────────────────────
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

# Collect all messages instead of printing directly
MESSAGES=""
add_msg() {
  if [ -n "$MESSAGES" ]; then
    MESSAGES="$MESSAGES\n$1"
  else
    MESSAGES="$1"
  fi
}

# ── Profile check ─────────────────────────────────────────────
if [ ! -f "$PROFILE_PATH" ]; then
  add_msg "[DevOps] Profile not configured. Run /init profile to set up your identity, role, team members, and state permissions."
fi

# ── Staleness check ───────────────────────────────────────────
if [ -f "$PROFILE_PATH" ]; then
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

  LAST_REFRESH=$(grep -E '^lastRefresh:|^lastUpdated:' "$PROFILE_PATH" 2>/dev/null | head -1 | sed 's/^[^:]*:[[:space:]]*//' | tr -d '"' | tr -d "'")

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
      add_msg "[DevOps] Profile last refreshed ${DAYS_OLD} days ago (threshold: ${STALENESS_DAYS}d). Run /init profile --refresh."
    fi
  fi

  # Profile required fields check
  for field_pair in "role:Primary Role" "defaultProject:Default Project" "teamMembers:Team Members"; do
    yaml_key="${field_pair%%:*}"
    md_label="${field_pair##*:}"
    if ! grep -qi "^${yaml_key}\b" "$PROFILE_PATH" 2>/dev/null \
       && ! grep -qi "|\s*\*\*${md_label}\*\*\s*|" "$PROFILE_PATH" 2>/dev/null \
       && ! grep -qi "^##.*${md_label}" "$PROFILE_PATH" 2>/dev/null; then
      add_msg "[DevOps] Profile missing '${yaml_key}'. Run /init profile to complete setup."
    fi
  done
fi

# ── Core data file checks (consolidated) ──────────────────────
if [ -n "$PYTHON" ]; then
  VALIDATION=$($PYTHON -c "
import json, os
root = r'$PLUGIN_ROOT'
msgs = []
for f in ['state_machine.json', 'hierarchy_rules.json', 'project_defaults.json']:
    p = os.path.join(root, 'data', f)
    if not os.path.isfile(p):
        msgs.append(f'[DevOps] WARNING: data/{f} is missing.')
    else:
        try: json.load(open(p))
        except: msgs.append(f'[DevOps] WARNING: {f} has invalid JSON.')
print('\n'.join(msgs))
" 2>/dev/null)
  [ -n "$VALIDATION" ] && add_msg "$VALIDATION"
fi

# ── Output in official JSON format ────────────────────────────
# Escape the messages for JSON embedding
if [ -n "$PYTHON" ]; then
  $PYTHON -c "
import json
msg = '''$MESSAGES'''
print(json.dumps({'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': msg.strip()}}))
" 2>/dev/null || echo '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":""}}'
else
  echo '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":""}}'
fi

exit 0
