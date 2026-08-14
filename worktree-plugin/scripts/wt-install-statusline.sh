#!/usr/bin/env bash
# wt-install-statusline.sh - Install (or remove) the worktree status line.
#
# A plugin cannot ship a `statusLine`: a plugin's settings.json only supports
# the `agent` and `subagentStatusLine` keys. So the status line has to be
# installed into the user's own settings, which is what /worktree:init does.
#
# This script handles only the deterministic half: detect the platform, copy
# the script to a STABLE user-level path, and print the exact JSON value to
# use. It never edits settings.json - that edit is made by Claude so the user
# sees a diff and confirms it.
#
# The copy matters: the plugin lives in a VERSIONED cache directory
# (~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/...), so pointing
# settings.json there would break the status line on every plugin update.
#
# Usage:
#   wt-install-statusline.sh install [--force-ps1]
#   wt-install-statusline.sh remove
#   wt-install-statusline.sh detect
#
# Output is KEY=VALUE lines for the caller to read.

set -u

ACTION=${1:-detect}
FORCE_PS1=0
for a in "$@"; do [ "$a" = "--force-ps1" ] && FORCE_PS1=1; done

IS_WIN=0
case "$(uname -s 2>/dev/null || echo unknown)" in
  MINGW*|MSYS*|CYGWIN*) IS_WIN=1 ;;
esac
[ "${OS:-}" = "Windows_NT" ] && IS_WIN=1

# Resolve this plugin's root from the script location, so the plugin works from
# any install path.
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PLUGIN_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
SRC_SH="$PLUGIN_ROOT/statusline/worktree-statusline.sh"
SRC_PS1="$PLUGIN_ROOT/statusline/worktree-statusline.ps1"

HOME_DIR=${HOME:-${USERPROFILE:-}}
[ -n "$HOME_DIR" ] || { echo "ERROR=cannot determine home directory"; exit 1; }
DEST_DIR="$HOME_DIR/.claude/worktree-plugin"

# Does Claude Code have Git Bash available for status-line execution?
GIT_BASH=''
if [ "$IS_WIN" = 1 ]; then
  for c in "/c/Program Files/Git/bin/bash.exe" "/c/Program Files (x86)/Git/bin/bash.exe" \
           "${PROGRAMFILES:-}/Git/bin/bash.exe"; do
    [ -n "$c" ] && [ -x "$c" ] && { GIT_BASH=$c; break; }
  done
  # A bash we are already running under counts, as long as it is not WSL's.
  [ -z "$GIT_BASH" ] && case "$(uname -s 2>/dev/null)" in MINGW*|MSYS*) GIT_BASH="(current MSYS bash)" ;; esac
fi

USE_PS1=0
if [ "$IS_WIN" = 1 ] && { [ -z "$GIT_BASH" ] || [ "$FORCE_PS1" = 1 ]; }; then
  USE_PS1=1
fi

# Windows-form path with forward slashes. Git Bash eats unquoted backslashes in
# the settings.json command string, so backslashes must never appear there.
win_path() {
  if command -v cygpath >/dev/null 2>&1; then
    cygpath -m "$1" 2>/dev/null && return
  fi
  printf '%s' "$1"
}

echo "PLATFORM=$([ "$IS_WIN" = 1 ] && echo windows || echo posix)"
echo "GIT_BASH=${GIT_BASH:-none}"
echo "PLUGIN_ROOT=$PLUGIN_ROOT"
echo "DEST_DIR=$DEST_DIR"
echo "FLAVOUR=$([ "$USE_PS1" = 1 ] && echo powershell || echo bash)"

case "$ACTION" in
  detect)
    exit 0
    ;;

  install)
    [ -f "$SRC_SH" ]  || { echo "ERROR=missing $SRC_SH"; exit 1; }
    mkdir -p "$DEST_DIR" || { echo "ERROR=cannot create $DEST_DIR"; exit 1; }
    cp "$SRC_SH"  "$DEST_DIR/statusline.sh"  || { echo "ERROR=copy failed"; exit 1; }
    [ -f "$SRC_PS1" ] && cp "$SRC_PS1" "$DEST_DIR/statusline.ps1"
    chmod +x "$DEST_DIR/statusline.sh" 2>/dev/null

    if [ "$USE_PS1" = 1 ]; then
      P=$(win_path "$DEST_DIR/statusline.ps1")
      echo "INSTALLED=$DEST_DIR/statusline.ps1"
      echo "COMMAND=powershell -NoProfile -File $P"
    else
      # "~" expands to the user's home and avoids embedding an absolute path.
      echo "INSTALLED=$DEST_DIR/statusline.sh"
      echo "COMMAND=~/.claude/worktree-plugin/statusline.sh"
    fi
    echo "OK=1"
    ;;

  remove)
    rm -f "$DEST_DIR/statusline.sh" "$DEST_DIR/statusline.ps1" 2>/dev/null
    rmdir "$DEST_DIR" 2>/dev/null
    echo "REMOVED=$DEST_DIR"
    echo "OK=1"
    ;;

  *)
    echo "ERROR=unknown action '$ACTION' (expected install|remove|detect)"
    exit 1
    ;;
esac
