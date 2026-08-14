#!/usr/bin/env bash
# wt-inventory.sh - Emit a JSON inventory of this repository's git worktrees.
#
# Git is the source of truth. This script keeps no state of its own; it reads
# `git worktree list --porcelain`, enriches each entry, and prints JSON.
#
# Portability: bash 3.2+ (macOS system bash) and Git Bash / MSYS on Windows.
# No jq, python, awk-scripting-language assumptions beyond POSIX awk, and no
# other runtime dependency.
#
# PERFORMANCE NOTE (important on Windows): every forked process costs ~100ms
# here, so the string helpers below are pure-bash and assign to globals rather
# than being called through $(...) command substitution. An earlier version
# using sed/tr helpers took 23s on an 8-worktree repo; this one takes <2s.
#
# Usage: wt-inventory.sh [--no-sessions] [--fast]
#   --no-sessions  Skip `claude agents --json` session discovery.
#   --fast         Skip per-worktree dirty/ahead/merged computation.
#
# Exit codes: 0 always; failures are reported as {"ok":false,...}.

set -u

WANT_SESSIONS=1
WANT_STATUS=1
for arg in "$@"; do
  case "$arg" in
    --no-sessions) WANT_SESSIONS=0 ;;
    --fast)        WANT_STATUS=0 ;;
    -h|--help)     sed -n '2,20p' "$0"; exit 0 ;;
  esac
done

LOCK_PREFIX='worktree-plugin:'

# ---------------------------------------------------------------- platform ---
IS_WIN=0
case "$(uname -s 2>/dev/null || echo unknown)" in
  MINGW*|MSYS*|CYGWIN*) IS_WIN=1 ;;
esac
[ "${OS:-}" = "Windows_NT" ] && IS_WIN=1
# Windows filesystems are case-insensitive; compare paths accordingly.
[ "$IS_WIN" = 1 ] && shopt -s nocasematch 2>/dev/null

# ------------------------------------------------- fork-free string helpers ---

# _jstr <text> -> JS : JSON-escaped string body (no surrounding quotes).
JS=''
_jstr() {
  local s=${1-}
  s=${s//\\/\\\\}
  s=${s//\"/\\\"}
  s=${s//$'\t'/\\t}
  s=${s//$'\r'/}
  s=${s//$'\n'/ }
  JS=$s
}

# _norm <path> -> NP : canonical comparable path form.
# Backslashes become slashes, "C:/x" becomes "/C/x", trailing slashes are
# dropped. Case is NOT folded here; comparisons use nocasematch on Windows.
# This is the most important correctness helper in the script: Claude reports
# session cwd as "C:\a\b", git reports "C:/a/b", the shell reports "/c/a/b".
NP=''
_norm() {
  local p=${1-}
  p=${p//\\//}
  case $p in
    [A-Za-z]:/*) p="/${p:0:1}${p:2}" ;;
  esac
  while [ ${#p} -gt 1 ] && [ "${p%/}" != "$p" ]; do p=${p%/}; done
  NP=$p
}

# _peq <a> <b> : paths equal (case-insensitive on Windows).
_peq() { [[ $1 == "$2" ]]; }
# _punder <child> <parent> : child is strictly under parent.
_punder() { [[ $1 == "$2"/* ]]; }

# is_alive <pid>
# Claude writes native Windows PIDs into its lock reasons; MSYS `kill -0`
# cannot see those, so query tasklist. MSYS_NO_PATHCONV/MSYS2_ARG_CONV_EXCL are
# required because Git Bash otherwise rewrites the leading-slash argument "/FI"
# into a filesystem path such as "C:/Program Files/Git/FI".
is_alive() {
  [ -n "${1:-}" ] || return 1
  if [ "$IS_WIN" = 1 ] && command -v tasklist >/dev/null 2>&1; then
    MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*' \
      tasklist /FI "PID eq $1" /NH 2>/dev/null | grep -q "[^0-9]$1\([^0-9]\|$\)" && return 0
    return 1
  fi
  kill -0 "$1" 2>/dev/null
}

# lock_kind <reason> -> LK : who owns a git worktree lock.
#   none | plugin | claude-live | claude-stale | foreign
LK=''
lock_kind() {
  local r=${1-} pid rest
  if [ -z "$r" ]; then LK=none; return; fi
  case $r in
    "$LOCK_PREFIX"*) LK=plugin; return ;;
  esac
  case $r in
    claude\ *"(pid "*)
      rest=${r#*"(pid "}
      pid=${rest%%[!0-9]*}
      if [ -n "$pid" ] && is_alive "$pid"; then LK=claude-live; else LK=claude-stale; fi
      return ;;
  esac
  LK=foreign
}

fail() {
  _jstr "$1"
  printf '{"ok":false,"error":"%s","worktrees":[]}\n' "$JS"
  exit 0
}

# ------------------------------------------------------------- repo lookup ---
command -v git >/dev/null 2>&1 || fail "git is not installed or not on PATH"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "not inside a git repository"

CUR_TOP=$(git rev-parse --show-toplevel 2>/dev/null)
PORCELAIN=$(git worktree list --porcelain 2>/dev/null) || fail "git worktree list failed"

# The first porcelain entry is always the main worktree.
MAIN_ROOT=''
while IFS= read -r l; do
  case $l in worktree\ *) MAIN_ROOT=${l#worktree }; break ;; esac
done <<< "$PORCELAIN"
[ -n "$MAIN_ROOT" ] || fail "could not determine the main worktree"

MANAGED_ROOT="$MAIN_ROOT/.claude/worktrees"
_norm "$MAIN_ROOT";    N_MAIN=$NP
_norm "$MANAGED_ROOT"; N_MANAGED=$NP
_norm "$CUR_TOP";      N_CUR=$NP

# Default branch: origin/HEAD, then a local main/master, else current HEAD.
DEFAULT_BRANCH=$(git -C "$MAIN_ROOT" symbolic-ref --short -q refs/remotes/origin/HEAD 2>/dev/null)
DEFAULT_BRANCH=${DEFAULT_BRANCH#origin/}
if [ -z "$DEFAULT_BRANCH" ]; then
  for cand in main master; do
    if git -C "$MAIN_ROOT" show-ref --verify --quiet "refs/heads/$cand"; then
      DEFAULT_BRANCH=$cand; break
    fi
  done
fi
[ -n "$DEFAULT_BRANCH" ] || DEFAULT_BRANCH=$(git -C "$MAIN_ROOT" symbolic-ref --short -q HEAD 2>/dev/null)

# --------------------------------------------------------- session discovery ---
TMPD=$(mktemp -d 2>/dev/null) || TMPD="${TMPDIR:-/tmp}/wtinv.$$"
mkdir -p "$TMPD" 2>/dev/null
cleanup() { rm -rf "$TMPD" 2>/dev/null; }
trap cleanup EXIT
SESS_FILE="$TMPD/sessions"
: > "$SESS_FILE"
SESSIONS_AVAILABLE=false

if [ "$WANT_SESSIONS" = 1 ] && command -v claude >/dev/null 2>&1; then
  RAW=$(claude agents --json 2>/dev/null)
  if [ -n "$RAW" ]; then
    SESSIONS_AVAILABLE=true
    # One awk pass over the whole array. RS="}" makes each session object a
    # record, which works for both pretty-printed and compact JSON.
    printf '%s' "$RAW" | awk 'BEGIN{RS="}"}
      function get(k,  s){
        if (match($0, "\"" k "\"[ \t]*:[ \t]*\"[^\"]*\"")) {
          s = substr($0, RSTART, RLENGTH); sub(/^"[^"]*"[ \t]*:[ \t]*"/, "", s); return s
        }
        if (match($0, "\"" k "\"[ \t]*:[ \t]*[0-9]+")) {
          s = substr($0, RSTART, RLENGTH); sub(/^.*:[ \t]*/, "", s); return s
        }
        return ""
      }
      { c = get("cwd"); if (c == "") next
        st = get("status"); if (st == "") st = get("state")
        printf "%s|%s|%s|%s\n", c, get("pid"), get("kind"), get("name") "\x1f" st }' \
      > "$TMPD/sessions.raw" 2>/dev/null

    while IFS='|' read -r c pid kind rest; do
      [ -n "$c" ] || continue
      c=${c//\\\\/\\}          # JSON-unescape backslashes
      _norm "$c"
      printf '%s|%s|%s|%s\n' "$NP" "$pid" "$kind" "$rest" >> "$SESS_FILE"
    done < "$TMPD/sessions.raw"
  fi
fi

# ------------------------------------------------------------------- output ---
_jstr "$MAIN_ROOT";      J_MAIN=$JS
_jstr "$MANAGED_ROOT";   J_MANAGED=$JS
_jstr "$DEFAULT_BRANCH"; J_DEF=$JS

printf '{\n  "ok": true,\n'
printf '  "platform": "%s",\n' "$([ "$IS_WIN" = 1 ] && printf windows || printf posix)"
printf '  "repo": { "mainRoot": "%s", "managedRoot": "%s", "defaultBranch": "%s" },\n' \
  "$J_MAIN" "$J_MANAGED" "$J_DEF"
printf '  "sessionsAvailable": %s,\n  "worktrees": [\n' "$SESSIONS_AVAILABLE"

FIRST=1
WT=''; BR=''; LOCKED=false; LOCKREASON=''; PRUNABLE=false; DETACHED=false; BARE=false

emit() {
  [ -n "$WT" ] || return 0
  local n_wt name kind is_current exists lk dirty untracked ahead behind merged
  local state_known sess_json scount switchable switch_block verdict why lr

  _norm "$WT"; n_wt=$NP
  name=${WT##*/}

  if _peq "$n_wt" "$N_MAIN"; then
    kind=main; name="(main checkout)"
  elif _punder "$n_wt" "$N_MANAGED"; then
    kind=managed
  else
    kind=external
  fi

  is_current=false; _peq "$n_wt" "$N_CUR" && is_current=true
  exists=true; [ -d "$WT" ] || exists=false
  lock_kind "$LOCKREASON"; lk=$LK

  dirty=0; untracked=0; ahead=0; behind=0; merged=false; state_known=false
  if [ "$WANT_STATUS" = 1 ] && [ "$exists" = true ] && [ "$BARE" = false ]; then
    local st
    if st=$(git -C "$WT" status --porcelain 2>/dev/null); then
      state_known=true
      if [ -n "$st" ]; then
        while IFS= read -r l; do
          [ -n "$l" ] || continue
          case $l in '??'*) untracked=$((untracked+1)) ;; *) dirty=$((dirty+1)) ;; esac
        done <<< "$st"
      fi
      if [ -n "$DEFAULT_BRANCH" ]; then
        # One call yields both directions: "<behind>\t<ahead>".
        lr=$(git -C "$WT" rev-list --count --left-right "$DEFAULT_BRANCH...HEAD" 2>/dev/null)
        if [ -n "$lr" ]; then
          behind=${lr%%[!0-9]*}
          ahead=${lr##*[!0-9]}
          [ -n "$behind" ] || behind=0
          [ -n "$ahead" ] || ahead=0
          [ "$ahead" = 0 ] && merged=true
        fi
      fi
    fi
  fi

  sess_json=''; scount=0
  if [ -s "$SESS_FILE" ]; then
    local scwd spid skind srest sname sstat
    while IFS='|' read -r scwd spid skind srest; do
      _peq "$scwd" "$n_wt" || continue
      sname=${srest%%$'\x1f'*}; sstat=${srest#*$'\x1f'}
      scount=$((scount+1))
      _jstr "$skind"; local jk=$JS
      _jstr "$sname"; local jn=$JS
      _jstr "$sstat"; local js=$JS
      [ -n "$sess_json" ] && sess_json="$sess_json, "
      sess_json="$sess_json{\"pid\": ${spid:-0}, \"kind\": \"$jk\", \"name\": \"$jn\", \"status\": \"$js\"}"
    done < "$SESS_FILE"
  fi

  # Switching mid-session is limited to worktrees under .claude/worktrees/, and
  # Claude refuses to enter one held by a live Claude Code session.
  switchable=true; switch_block=''
  if [ "$kind" = main ]; then
    switchable=false; switch_block="main checkout"
  elif [ "$kind" = external ]; then
    switchable=false; switch_block="outside .claude/worktrees/ - enterable only as a first entry from the launch directory"
  elif [ "$is_current" = true ]; then
    switchable=false; switch_block="already the current worktree"
  elif [ "$lk" = claude-live ]; then
    switchable=false; switch_block="held by a running Claude Code session - open a new terminal there instead"
  elif [ "$PRUNABLE" = true ] || [ "$exists" = false ]; then
    switchable=false; switch_block="directory is missing or marked prunable"
  fi

  # Cleanup verdict: conservative by construction. Anything not provably safe
  # is kept.
  if [ "$kind" = main ] || [ "$BARE" = true ]; then
    verdict=skip; why="not a disposable workspace"
  elif [ "$exists" = false ] || [ "$PRUNABLE" = true ]; then
    verdict=stale; why="directory missing; git metadata can be pruned"
  elif [ "$is_current" = true ]; then
    verdict=current; why="this session is inside it"
  elif [ "$scount" -gt 0 ]; then
    verdict=unsafe; why="$scount Claude session(s) attached"
  elif [ "$lk" = claude-live ]; then
    verdict=unsafe; why="locked by a running Claude Code session"
  elif [ "$lk" = foreign ]; then
    verdict=unsafe; why="locked by you or another tool"
  elif [ "$state_known" = false ]; then
    verdict=unsafe; why="git state could not be read"
  elif [ "$dirty" -gt 0 ] || [ "$untracked" -gt 0 ]; then
    verdict=unsafe; why="$dirty modified, $untracked untracked"
  elif [ "$merged" = true ]; then
    verdict=safe; why="clean and merged into $DEFAULT_BRANCH"
  elif [ "$ahead" -gt 0 ]; then
    verdict=review; why="clean but $ahead commit(s) not on $DEFAULT_BRANCH"
  else
    verdict=safe; why="clean, nothing to lose"
  fi

  # An externally-placed worktree was created deliberately outside the managed
  # zone and its path may be depended on. Never let it default to removal.
  if [ "$kind" = external ] && [ "$verdict" = safe ]; then
    verdict=review; why="$why (outside .claude/worktrees/ - confirm the path is disposable)"
  fi

  _jstr "$name";        local j_name=$JS
  _jstr "$WT";          local j_path=$JS
  _jstr "$BR";          local j_branch=$JS
  _jstr "$LOCKREASON";  local j_lock=$JS
  _jstr "$switch_block";local j_sb=$JS
  _jstr "$why";         local j_why=$JS

  [ "$FIRST" = 1 ] || printf ',\n'
  FIRST=0
  printf '    {"name": "%s", "path": "%s", "branch": "%s", "kind": "%s", "isCurrent": %s, "exists": %s, "bare": %s, "detached": %s, "prunable": %s, "locked": %s, "lockKind": "%s", "lockReason": "%s", "dirty": %s, "untracked": %s, "ahead": %s, "behind": %s, "merged": %s, "stateKnown": %s, "sessionCount": %s, "sessions": [%s], "switchable": %s, "switchBlockedBy": "%s", "verdict": "%s", "reason": "%s"}' \
    "$j_name" "$j_path" "$j_branch" "$kind" "$is_current" "$exists" "$BARE" "$DETACHED" \
    "$PRUNABLE" "$LOCKED" "$lk" "$j_lock" "$dirty" "$untracked" "$ahead" "$behind" \
    "$merged" "$state_known" "$scount" "$sess_json" "$switchable" "$j_sb" "$verdict" "$j_why"
}

# Read from a file rather than an unquoted heredoc, which would process
# backslash escapes inside lock reasons.
printf '%s\n' "$PORCELAIN" > "$TMPD/porcelain"
while IFS= read -r line; do
  case "$line" in
    worktree\ *)
      emit
      WT=${line#worktree }; BR=''; LOCKED=false; LOCKREASON=''
      PRUNABLE=false; DETACHED=false; BARE=false ;;
    branch\ *)  BR=${line#branch }; BR=${BR#refs/heads/} ;;
    detached)   DETACHED=true ;;
    bare)       BARE=true ;;
    locked)     LOCKED=true; LOCKREASON='' ;;
    locked\ *)  LOCKED=true; LOCKREASON=${line#locked } ;;
    prunable*)  PRUNABLE=true ;;
  esac
done < "$TMPD/porcelain"
emit

printf '\n  ]\n}\n'
