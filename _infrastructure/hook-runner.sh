#!/usr/bin/env bash
# ============================================================================
# hook-runner.sh — Centralized wrapper for all command-type hooks
#
# Provides: timeout enforcement, JSONL logging, safe-mode checking,
#           graceful degradation, and error normalization.
#
# Usage (in hooks.json):
#   "command": "bash \"${CLAUDE_PLUGIN_ROOT}/../_infrastructure/hook-runner.sh\"
#              --plugin=odoo-upgrade --hook=guard_core_odoo.py
#              --type=PreToolUse --timeout=5 --blocking"
#
# The outer hooks.json timeout should be ~3s higher than --timeout to allow
# wrapper overhead (logging, safe-mode check).
# ============================================================================

# NOTE: No 'set -e' or 'set -u'. This wrapper MUST NOT crash.
# It must survive: non-zero child exit codes (exit 2 = intentional block),
# unset variables (CLAUDE_PLUGIN_ROOT may not exist), and pipe failures.
# A crashed wrapper = a broken hook with no logging or fallback.

# ── Defaults ────────────────────────────────────────────────────────────────
PLUGIN=""
HOOK=""
HOOK_TYPE=""
TIMEOUT=10
BLOCKING=false
VERBOSE=false

# ── Parse arguments ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --plugin=*)   PLUGIN="${1#*=}"; shift ;;
    --hook=*)     HOOK="${1#*=}"; shift ;;
    --type=*)     HOOK_TYPE="${1#*=}"; shift ;;
    --timeout=*)  TIMEOUT="${1#*=}"; shift ;;
    --blocking)   BLOCKING=true; shift ;;
    --verbose)    VERBOSE=true; shift ;;
    *)            shift ;;
  esac
done

if [[ -z "$PLUGIN" || -z "$HOOK" || -z "$HOOK_TYPE" ]]; then
  echo "[hook-runner] ERROR: --plugin, --hook, and --type are required" >&2
  exit 0  # Fail-open: don't block on wrapper misconfiguration
fi

# ── Windows path fix ────────────────────────────────────────────────────────
fix_path() {
  local p="$1"
  if [[ "$p" =~ ^/([a-zA-Z])/ ]]; then
    echo "${BASH_REMATCH[1]}:/${p:3}"
  else
    echo "$p"
  fi
}

# ── Resolve paths ───────────────────────────────────────────────────────────
INFRA_DIR="$(fix_path "$(cd "$(dirname "$0")" && pwd)")"
PLUGINS_ROOT="$(dirname "$INFRA_DIR")"
SCRIPT_PATH="$PLUGINS_ROOT/$PLUGIN/hooks/$HOOK"
HOME_DIR="$(fix_path "$HOME")"
LOG_DIR="$HOME_DIR/.claude/logs"
LOG_FILE="$LOG_DIR/hook-audit.jsonl"
SAFE_MODE_FILE="$HOME_DIR/.claude/hook-safe-mode.json"

# Ensure log directory exists
mkdir -p "$LOG_DIR" 2>/dev/null || true

# ── Timestamp helper ────────────────────────────────────────────────────────
iso_now() {
  date -u +"%Y-%m-%dT%H:%M:%S.000Z" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%S"
}

# ── Logging helper ──────────────────────────────────────────────────────────
log_entry() {
  local exit_code="$1"
  local duration_ms="$2"
  local timed_out="$3"
  local blocked="$4"
  local error="$5"
  local skipped="$6"

  # Write JSONL log entry (best-effort, don't fail if logging fails)
  printf '{"ts":"%s","hook_type":"%s","plugin":"%s","hook_name":"%s","script":"%s","exit_code":%s,"duration_ms":%s,"timed_out":%s,"blocked":%s,"skipped":%s,"error":%s}\n' \
    "$(iso_now)" "$HOOK_TYPE" "$PLUGIN" "${HOOK%.*}" "$HOOK" \
    "$exit_code" "$duration_ms" "$timed_out" "$blocked" "$skipped" \
    "$error" \
    >> "$LOG_FILE" 2>/dev/null || true
}

# ── Safe-mode check ────────────────────────────────────────────────────────
if [[ -f "$SAFE_MODE_FILE" ]]; then
  # Check if Python is available for JSON parsing
  PYTHON=""
  if command -v python3 &>/dev/null; then
    PYTHON="python3"
  elif command -v python &>/dev/null; then
    PYTHON="python"
  fi

  if [[ -n "$PYTHON" ]]; then
    SAFE_MODE_RESULT=$($PYTHON -c "
import json, sys
try:
    with open(r'$SAFE_MODE_FILE') as f:
        sm = json.load(f)
    if not sm.get('enabled', False):
        print('disabled')
        sys.exit(0)
    # Check if this specific plugin is disabled
    if '$PLUGIN' in sm.get('disabled_plugins', []):
        print('skip:plugin')
        sys.exit(0)
    # Check if this specific hook is disabled
    if '$HOOK' in sm.get('disabled_hooks', []):
        print('skip:hook')
        sys.exit(0)
    # Check prompt-only mode
    if sm.get('allow_prompt_only', False):
        print('skip:prompt-only')
        sys.exit(0)
    print('active')
except:
    print('disabled')
" 2>/dev/null)

    case "$SAFE_MODE_RESULT" in
      skip:*)
        log_entry 0 0 "false" "false" "null" "\"$SAFE_MODE_RESULT\""
        exit 0
        ;;
    esac
  fi
fi

# ── Verify script exists ───────────────────────────────────────────────────
if [[ ! -f "$SCRIPT_PATH" ]]; then
  log_entry 1 0 "false" "false" "\"script_not_found:$SCRIPT_PATH\"" "false"
  echo "[hook-runner] WARNING: Script not found: $SCRIPT_PATH" >&2
  exit 0  # Fail-open: missing script should not block
fi

# ── Determine interpreter ──────────────────────────────────────────────────
INTERPRETER=""
case "$HOOK" in
  *.py)
    if command -v python3 &>/dev/null; then
      INTERPRETER="python3"
    elif command -v python &>/dev/null; then
      INTERPRETER="python"
    else
      log_entry 1 0 "false" "false" "\"python_not_available\"" "false"
      echo "[hook-runner] WARNING: Python not available, skipping $HOOK" >&2
      exit 0  # Fail-open
    fi
    ;;
  *.sh)
    INTERPRETER="bash"
    ;;
  *)
    INTERPRETER="bash"
    ;;
esac

# ── Read stdin into temp file (for piping to child) ────────────────────────
STDIN_TMP=$(mktemp 2>/dev/null || echo "/tmp/hook-runner-stdin-$$")
cat > "$STDIN_TMP"

# ── Execute with timeout ───────────────────────────────────────────────────
START_MS=$(date +%s%N 2>/dev/null | cut -b1-13 || date +%s)

STDOUT_TMP=$(mktemp 2>/dev/null || echo "/tmp/hook-runner-stdout-$$")
STDERR_TMP=$(mktemp 2>/dev/null || echo "/tmp/hook-runner-stderr-$$")

# Use timeout command (available in Git Bash via GNU coreutils)
if command -v timeout &>/dev/null; then
  timeout "$TIMEOUT" "$INTERPRETER" "$SCRIPT_PATH" < "$STDIN_TMP" > "$STDOUT_TMP" 2> "$STDERR_TMP"
  EXIT_CODE=$?
else
  # Fallback: run without timeout enforcement (wrapper timeout is best-effort)
  "$INTERPRETER" "$SCRIPT_PATH" < "$STDIN_TMP" > "$STDOUT_TMP" 2> "$STDERR_TMP"
  EXIT_CODE=$?
fi

END_MS=$(date +%s%N 2>/dev/null | cut -b1-13 || date +%s)

# Calculate duration
if [[ ${#START_MS} -gt 10 ]]; then
  DURATION_MS=$((END_MS - START_MS))
else
  DURATION_MS=$(( (END_MS - START_MS) * 1000 ))
fi

# ── Handle timeout (exit code 124 from GNU timeout) ────────────────────────
TIMED_OUT="false"
if [[ $EXIT_CODE -eq 124 ]]; then
  TIMED_OUT="true"
  EXIT_CODE=1  # Normalize timeout to non-fatal error
fi

# ── Determine blocking behavior ────────────────────────────────────────────
BLOCKED="false"
FINAL_EXIT=0

if [[ $EXIT_CODE -eq 2 ]] && [[ "$BLOCKING" == "true" ]] && [[ "$HOOK_TYPE" == "PreToolUse" ]]; then
  # Legitimate block: propagate exit 2 and stderr
  BLOCKED="true"
  FINAL_EXIT=2
  cat "$STDERR_TMP" >&2
elif [[ $EXIT_CODE -eq 2 ]]; then
  # Exit 2 from non-blocking hook or non-PreToolUse: log but don't block
  BLOCKED="false"
  FINAL_EXIT=0
fi

# ── Output stdout (becomes conversation context) ───────────────────────────
cat "$STDOUT_TMP"

# ── Log the invocation ─────────────────────────────────────────────────────
ERROR_JSON="null"
if [[ $TIMED_OUT == "true" ]]; then
  ERROR_JSON="\"timeout_after_${TIMEOUT}s\""
elif [[ $EXIT_CODE -ne 0 ]] && [[ $EXIT_CODE -ne 2 ]]; then
  ERROR_JSON="\"exit_code_$EXIT_CODE\""
fi

log_entry "$EXIT_CODE" "$DURATION_MS" "$TIMED_OUT" "$BLOCKED" "$ERROR_JSON" "false"

# ── Cleanup ─────────────────────────────────────────────────────────────────
rm -f "$STDIN_TMP" "$STDOUT_TMP" "$STDERR_TMP" 2>/dev/null || true

exit "$FINAL_EXIT"
