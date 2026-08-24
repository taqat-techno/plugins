#!/usr/bin/env bash
# wt-lanes.sh - Emit a JSON board of this repository's PDLE lanes.
#
# Reads the lane records under .claude/lanes/*.lane (the only persisted state)
# and DERIVES everything else from git, the filesystem, and `claude agents
# --json`. Nothing computable is ever read from a record - see
# references/lane-record.md and references/board-states.md.
#
# Portability: bash 3.2+ (macOS system bash) and Git Bash / MSYS on Windows.
# No jq, no python, no bash-4 features (no associative arrays, no mapfile).
#
# PERFORMANCE: forks cost ~100ms on Windows, so per-lane git calls are batched
# into one `git status --porcelain` plus two rev-list counts. Use --fast to
# skip git state entirely when only the records are wanted.
#
# Usage: wt-lanes.sh [--no-sessions] [--fast]
#   --no-sessions  Skip `claude agents --json` owner-liveness discovery.
#   --fast         Skip per-lane git state (staged/modified/ahead/merged).
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

# ---------------------------------------------------------------- platform ---
IS_WIN=0
case "$(uname -s 2>/dev/null || echo unknown)" in
  MINGW*|MSYS*|CYGWIN*) IS_WIN=1 ;;
esac
[ "${OS:-}" = "Windows_NT" ] && IS_WIN=1

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

# _trim <text> -> TR : leading and trailing whitespace removed.
TR=''
_trim() {
  local s=${1-}
  s=${s#"${s%%[![:space:]]*}"}
  s=${s%"${s##*[![:space:]]}"}
  TR=$s
}

# _norm <path> -> NP : canonical comparable path form (matches wt-inventory.sh).
NP=''
_norm() {
  local s=${1-}
  s=${s//\\//}
  case "$s" in
    [A-Za-z]:/*) s="/${s%%:*}${s#*:}" ;;
  esac
  while [ "${s%/}" != "$s" ] && [ "$s" != "/" ]; do s=${s%/}; done
  NP=$s
}

_fail() { _jstr "$1"; printf '{"ok":false,"error":"%s","lanes":[]}\n' "$JS"; exit 0; }

# -------------------------------------------------------------------- repo ---
MAIN_ROOT=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || \
  _fail "not a git repository"
MAIN_ROOT=${MAIN_ROOT%/.git}
MAIN_ROOT=${MAIN_ROOT%/}
[ -n "$MAIN_ROOT" ] || _fail "cannot resolve repository root"

DEFAULT_BRANCH=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null)
DEFAULT_BRANCH=${DEFAULT_BRANCH#origin/}
if [ -z "$DEFAULT_BRANCH" ]; then
  for c in main master; do
    if git show-ref --verify --quiet "refs/heads/$c"; then DEFAULT_BRANCH=$c; break; fi
  done
fi
[ -n "$DEFAULT_BRANCH" ] || DEFAULT_BRANCH=main

LANES_ROOT="$MAIN_ROOT/.claude/lanes"
REPORTS_ROOT="$LANES_ROOT/reports"

# ---------------------------------------------------- registered worktrees ---
# One porcelain pass: build parallel arrays of registered path + prunable flag.
REG_PATHS=""   # newline-separated normalised paths
REG_PRUNABLE="" # newline-separated 0/1 aligned with REG_PATHS
_cur=''
while IFS= read -r line; do
  case "$line" in
    worktree\ *) _norm "${line#worktree }"; _cur=$NP
                 REG_PATHS="$REG_PATHS$_cur"$'\n'
                 REG_PRUNABLE="$REG_PRUNABLE"0$'\n' ;;
    prunable*)   REG_PRUNABLE="${REG_PRUNABLE%0$'\n'}1"$'\n' ;;
  esac
done <<EOF
$(git worktree list --porcelain 2>/dev/null)
EOF

# _registered <normpath> -> REG_HIT (0/1), REG_DUP (0/1 same path seen twice)
REG_HIT=0; REG_DUP=0
_registered() {
  local want=$1 n=0
  REG_HIT=0; REG_DUP=0
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    if [ "$IS_WIN" = 1 ]; then
      shopt -s nocasematch 2>/dev/null
      [[ "$p" == "$want" ]] && n=$((n+1))
      shopt -u nocasematch 2>/dev/null
    else
      [ "$p" = "$want" ] && n=$((n+1))
    fi
  done <<EOF
$REG_PATHS
EOF
  [ "$n" -ge 1 ] && REG_HIT=1
  [ "$n" -ge 2 ] && REG_DUP=1
}

# A worktree registered under two different spellings of the same directory is
# the WSL-vs-Git-Bash trap: one of the pair is reported prunable, and a prune
# from the wrong shell would deregister staged work.
DUP_REGISTRATION=0
_dupcheck() {
  local a b seen=0
  while IFS= read -r a; do
    [ -n "$a" ] || continue
    seen=0
    while IFS= read -r b; do
      [ -n "$b" ] || continue
      if [ "$IS_WIN" = 1 ]; then
        shopt -s nocasematch 2>/dev/null; [[ "$a" == "$b" ]] && seen=$((seen+1)); shopt -u nocasematch 2>/dev/null
      else
        [ "$a" = "$b" ] && seen=$((seen+1))
      fi
    done <<EOF2
$REG_PATHS
EOF2
    [ "$seen" -ge 2 ] && DUP_REGISTRATION=1
  done <<EOF3
$REG_PATHS
EOF3
}
_dupcheck

# ---------------------------------------------------------------- sessions ---
SESSIONS_AVAILABLE=false
SESS=""   # one line per session: name<TAB>kind<TAB>status<TAB>cwd<TAB>pid
if [ "$WANT_SESSIONS" = 1 ]; then
  RAW=$(claude agents --json 2>/dev/null)
  if [ -n "$RAW" ]; then
    SESSIONS_AVAILABLE=true
    SESS=$(printf '%s' "$RAW" | awk 'BEGIN{RS="}"}
      function get(k,  s){
        if (match($0, "\"" k "\"[ \t]*:[ \t]*\"[^\"]*\"")) {
          s = substr($0, RSTART, RLENGTH); sub(/^"[^"]*"[ \t]*:[ \t]*"/, "", s)
          sub(/"$/, "", s)   # closing quote: without this every value keeps it
          return s
        }
        if (match($0, "\"" k "\"[ \t]*:[ \t]*[0-9]+")) {
          s = substr($0, RSTART, RLENGTH); sub(/^.*:[ \t]*/, "", s); return s
        }
        return ""
      }
      {
        n = get("name"); if (n == "") next
        printf "%s\t%s\t%s\t%s\t%s\n", n, get("kind"), get("status"), get("cwd"), get("pid")
      }')
  fi
fi

# _session <name> -> S_COUNT S_KIND S_STATUS S_CWD
S_COUNT=0; S_KIND=""; S_STATUS=""; S_CWD=""
_session() {
  local want=$1 nm kd st cw pd
  S_COUNT=0; S_KIND=""; S_STATUS=""; S_CWD=""
  [ -n "$SESS" ] || return 0
  while IFS=$'\t' read -r nm kd st cw pd; do
    [ -n "$nm" ] || continue
    if [ "$nm" = "$want" ]; then
      S_COUNT=$((S_COUNT+1))
      [ -z "$S_KIND" ] && { S_KIND=$kd; S_STATUS=$st; S_CWD=$cw; }
    fi
  done <<EOF
$SESS
EOF
}

# ------------------------------------------------------------------- lanes ---
if [ ! -d "$LANES_ROOT" ]; then
  printf '{"ok":true,"pdle":false,"repo":{"mainRoot":"%s","defaultBranch":"%s"},"lanes":[]}\n' \
    "$MAIN_ROOT" "$DEFAULT_BRANCH"
  exit 0
fi

printf '{\n  "ok": true,\n  "pdle": true,\n'
_jstr "$MAIN_ROOT"; MR=$JS
_jstr "$DEFAULT_BRANCH"; DB=$JS
printf '  "repo": { "mainRoot": "%s", "defaultBranch": "%s" },\n' "$MR" "$DB"
printf '  "sessionsAvailable": %s,\n' "$SESSIONS_AVAILABLE"
printf '  "duplicateWorktreeRegistration": %s,\n' "$([ "$DUP_REGISTRATION" = 1 ] && printf true || printf false)"
printf '  "lanes": [\n'

OWNS_PAIRS=""   # "<lane>\t<component>" per line, for the intersection check
FIRST=1

for rec in "$LANES_ROOT"/*.lane; do
  [ -e "$rec" ] || continue

  LANE=""; PACKAGE=""; WORKTREE=""; BRANCH=""; WAVE=""; BASE=""
  OWNER=""; DISPATCH=""; DISPATCHED_AT=""; ACKED_AT=""; HELD="false"
  OWNS_LIST=""; ENV_JSON=""

  while IFS= read -r line || [ -n "$line" ]; do
    line=${line%$'\r'}
    _trim "$line"; line=$TR
    [ -n "$line" ] || continue
    case "$line" in \#*) continue ;; esac
    key=${line%% *}
    val=${line#* }
    [ "$key" = "$line" ] && val=""
    _trim "$val"; val=$TR
    case "$key" in
      lane)          LANE=$val ;;
      package)       PACKAGE=$val ;;
      owns)          OWNS_LIST="$OWNS_LIST$val"$'\n' ;;
      worktree)      WORKTREE=$val ;;
      branch)        BRANCH=$val ;;
      wave)          WAVE=$val ;;
      base)          BASE=$val ;;
      owner)         OWNER=$val ;;
      dispatch)      DISPATCH=$val ;;
      dispatched-at) DISPATCHED_AT=$val ;;
      acked-at)      ACKED_AT=$val ;;
      held)          HELD=$val ;;
      env)           ek=${val%% *}; ev=${val#* }
                     [ "$ek" = "$val" ] && ev=""
                     _jstr "$ek"; k=$JS; _jstr "$ev"; v=$JS
                     [ -n "$ENV_JSON" ] && ENV_JSON="$ENV_JSON, "
                     ENV_JSON="$ENV_JSON\"$k\": \"$v\"" ;;
    esac
  done < "$rec"

  [ -n "$LANE" ] || LANE=$(basename "$rec" .lane)
  [ -n "$PACKAGE" ] || PACKAGE=$LANE

  # ---- filesystem + git derivation -----------------------------------------
  WT_ABS=""
  case "$WORKTREE" in
    /*|[A-Za-z]:*) WT_ABS=$WORKTREE ;;
    "")            WT_ABS="" ;;
    *)             WT_ABS="$MAIN_ROOT/$WORKTREE" ;;
  esac

  EXISTS=false; REGISTERED=false; DUPPATH=false
  ACTUAL_BRANCH=""; HEAD_SHA=""
  STAGED=0; MODIFIED=0; UNTRACKED=0; AHEAD=0; BEHIND=0; MERGED=false
  COMMITS_FROM_BASE=0
  STATE_KNOWN=false

  if [ -n "$WT_ABS" ] && [ -d "$WT_ABS" ]; then
    EXISTS=true
    _norm "$WT_ABS"; wtn=$NP
    _registered "$wtn"
    [ "$REG_HIT" = 1 ] && REGISTERED=true
    [ "$REG_DUP" = 1 ] && DUPPATH=true

    if [ "$WANT_STATUS" = 1 ]; then
      ACTUAL_BRANCH=$(git -C "$WT_ABS" symbolic-ref --quiet --short HEAD 2>/dev/null)
      HEAD_SHA=$(git -C "$WT_ABS" rev-parse --short HEAD 2>/dev/null)
      if [ -n "$HEAD_SHA" ]; then
        STATE_KNOWN=true
        while IFS= read -r st; do
          [ -n "$st" ] || continue
          x=${st:0:1}; y=${st:1:1}
          case "$st" in \?\?*) UNTRACKED=$((UNTRACKED+1)); continue ;; esac
          case "$x" in ' '|'') : ;; *) STAGED=$((STAGED+1)) ;; esac
          case "$y" in ' '|'') : ;; *) MODIFIED=$((MODIFIED+1)) ;; esac
        done <<EOF
$(git -C "$WT_ABS" status --porcelain 2>/dev/null)
EOF
        cmp_ref=$BRANCH
        [ -n "$cmp_ref" ] || cmp_ref=$HEAD_SHA
        AHEAD=$(git -C "$WT_ABS" rev-list --count "$DEFAULT_BRANCH..$cmp_ref" 2>/dev/null || echo 0)
        BEHIND=$(git -C "$WT_ABS" rev-list --count "$cmp_ref..$DEFAULT_BRANCH" 2>/dev/null || echo 0)
        case "$AHEAD" in ''|*[!0-9]*) AHEAD=0 ;; esac
        case "$BEHIND" in ''|*[!0-9]*) BEHIND=0 ;; esac

        # Commits this lane actually produced. A lane branch cut from the
        # integrated base and never committed to is TRIVIALLY an ancestor of
        # the default branch - without this counter every un-started lane
        # would report "merged".
        if [ -n "$BASE" ]; then
          COMMITS_FROM_BASE=$(git -C "$WT_ABS" rev-list --count "$BASE..$cmp_ref" 2>/dev/null || echo 0)
        else
          COMMITS_FROM_BASE=$AHEAD
        fi
        case "$COMMITS_FROM_BASE" in ''|*[!0-9]*) COMMITS_FROM_BASE=0 ;; esac

        # Merged means "this lane's work landed", not "this ref is reachable".
        if [ "$COMMITS_FROM_BASE" -gt 0 ] && \
           git -C "$WT_ABS" merge-base --is-ancestor "$cmp_ref" "$DEFAULT_BRANCH" 2>/dev/null; then
          MERGED=true
        fi
      fi
    fi
  fi

  # ---- reports (derived, never stored) -------------------------------------
  REPORT_COUNT=0; LAST_REPORT=""
  if [ -d "$REPORTS_ROOT" ]; then
    for rp in "$REPORTS_ROOT/$LANE"-*.md; do
      [ -e "$rp" ] || continue
      REPORT_COUNT=$((REPORT_COUNT+1))
      LAST_REPORT=$rp
    done
  fi

  # ---- owner liveness ------------------------------------------------------
  OWNER_LIVE=false; OWNER_KIND=""; OWNER_STATUS=""; OWNER_COUNT=0
  if [ -n "$OWNER" ] && [ "$SESSIONS_AVAILABLE" = true ]; then
    _session "$OWNER"
    OWNER_COUNT=$S_COUNT
    [ "$S_COUNT" -ge 1 ] && { OWNER_LIVE=true; OWNER_KIND=$S_KIND; OWNER_STATUS=$S_STATUS; }
  fi

  # ---- state derivation (see references/board-states.md) -------------------
  # Work is checked BEFORE ownership so that staged or dirty work is never
  # hidden behind "queued" when a worker died and the lane was unassigned.
  STATE="unknown"
  if [ "$MERGED" = true ] && [ "$STAGED" = 0 ] && [ "$MODIFIED" = 0 ] && [ "$UNTRACKED" = 0 ]; then
    STATE="merged"
  elif [ "$HELD" = "true" ] && [ -z "$ACKED_AT" ]; then
    STATE="dispatch-held"
  elif [ "$MODIFIED" -gt 0 ] || [ "$UNTRACKED" -gt 0 ]; then
    STATE="in-progress"
  elif [ "$STAGED" -gt 0 ] || [ "$COMMITS_FROM_BASE" -gt 0 ]; then
    STATE="at-gate"
  elif [ -z "$OWNER" ]; then
    STATE="queued"
  elif [ -n "$ACKED_AT" ]; then
    STATE="assigned-not-begun"
  else
    STATE="assigned-no-ack"
  fi

  # ---- anomaly flags -------------------------------------------------------
  FLAGS=""
  _flag() { [ -n "$FLAGS" ] && FLAGS="$FLAGS, "; _jstr "$1"; FLAGS="$FLAGS\"$JS\""; }
  [ "$EXISTS" = false ]      && _flag "worktree-missing"
  [ "$EXISTS" = true ] && [ "$REGISTERED" = false ] && _flag "worktree-not-registered"
  [ "$DUPPATH" = true ]      && _flag "worktree-registered-twice"
  [ -n "$ACTUAL_BRANCH" ] && [ -n "$BRANCH" ] && [ "$ACTUAL_BRANCH" != "$BRANCH" ] && _flag "branch-mismatch"
  [ "$BEHIND" -gt 0 ] && [ "$MERGED" = false ] && _flag "behind-default-branch"
  [ "$OWNER_COUNT" -gt 1 ]   && _flag "owner-name-ambiguous"
  [ -n "$OWNER" ] && [ "$SESSIONS_AVAILABLE" = true ] && [ "$OWNER_LIVE" = false ] && _flag "owner-not-live"
  [ -n "$OWNER_KIND" ] && [ "$OWNER_KIND" != "background" ] && _flag "owner-not-background"
  [ "$HELD" = "true" ]       && _flag "dispatch-held"
  [ "$STATE" = "at-gate" ] && [ "$REPORT_COUNT" = 0 ] && _flag "staged-but-unreported"
  [ "$MERGED" = true ] && [ -n "$OWNER" ] && _flag "merged-but-still-assigned"
  [ "$OWNER_LIVE" = false ] && [ "$STAGED" -gt 0 ] && [ "$SESSIONS_AVAILABLE" = true ] && _flag "staged-work-no-live-owner"

  # ---- owns pairs for the cross-lane intersection check --------------------
  OWNS_JSON=""
  while IFS= read -r c; do
    [ -n "$c" ] || continue
    OWNS_PAIRS="$OWNS_PAIRS$LANE"$'\t'"$c"$'\n'
    _jstr "$c"
    [ -n "$OWNS_JSON" ] && OWNS_JSON="$OWNS_JSON, "
    OWNS_JSON="$OWNS_JSON\"$JS\""
  done <<EOF
$OWNS_LIST
EOF

  [ "$FIRST" = 1 ] || printf ',\n'
  FIRST=0
  _jstr "$LANE";          F_LANE=$JS
  _jstr "$PACKAGE";       F_PKG=$JS
  _jstr "$WORKTREE";      F_WT=$JS
  _jstr "$BRANCH";        F_BR=$JS
  _jstr "$ACTUAL_BRANCH"; F_ABR=$JS
  _jstr "$BASE";          F_BASE=$JS
  _jstr "$OWNER";         F_OWN=$JS
  _jstr "$DISPATCH";      F_DSP=$JS
  _jstr "$DISPATCHED_AT"; F_DAT=$JS
  _jstr "$ACKED_AT";      F_AAT=$JS
  _jstr "$HEAD_SHA";      F_HEAD=$JS
  _jstr "$LAST_REPORT";   F_REP=$JS
  _jstr "$OWNER_KIND";    F_OK=$JS
  _jstr "$OWNER_STATUS";  F_OS=$JS
  _jstr "$STATE";         F_ST=$JS
  _jstr "${WAVE:-0}";     F_WAVE=$JS

  printf '    {"lane": "%s", "package": "%s", "owns": [%s], "worktree": "%s", "branch": "%s", "actualBranch": "%s", "wave": "%s", "base": "%s", "owner": "%s", "ownerLive": %s, "ownerKind": "%s", "ownerStatus": "%s", "ownerCount": %s, "dispatch": "%s", "dispatchedAt": "%s", "ackedAt": "%s", "held": %s, "exists": %s, "registered": %s, "head": "%s", "staged": %s, "modified": %s, "untracked": %s, "ahead": %s, "behind": %s, "commitsFromBase": %s, "merged": %s, "stateKnown": %s, "reportCount": %s, "lastReport": "%s", "state": "%s", "flags": [%s], "env": {%s}}' \
    "$F_LANE" "$F_PKG" "$OWNS_JSON" "$F_WT" "$F_BR" "$F_ABR" "$F_WAVE" "$F_BASE" \
    "$F_OWN" "$OWNER_LIVE" "$F_OK" "$F_OS" "$OWNER_COUNT" \
    "$F_DSP" "$F_DAT" "$F_AAT" "$([ "$HELD" = "true" ] && printf true || printf false)" \
    "$EXISTS" "$REGISTERED" "$F_HEAD" "$STAGED" "$MODIFIED" "$UNTRACKED" \
    "$AHEAD" "$BEHIND" "$COMMITS_FROM_BASE" "$MERGED" "$STATE_KNOWN" "$REPORT_COUNT" "$F_REP" "$F_ST" "$FLAGS" "$ENV_JSON"
done

printf '\n  ],\n'

# ------------------------------------------ cross-lane ownership collisions ---
# Two lanes may not run concurrently if their ownership sets intersect.
printf '  "ownsCollisions": ['
CFIRST=1
while IFS=$'\t' read -r la ca; do
  [ -n "$la" ] || continue
  while IFS=$'\t' read -r lb cb; do
    [ -n "$lb" ] || continue
    [ "$la" = "$lb" ] && continue
    if [ "$ca" = "$cb" ] && [ "$la" \< "$lb" ]; then
      [ "$CFIRST" = 1 ] || printf ', '
      CFIRST=0
      _jstr "$la"; A=$JS; _jstr "$lb"; B=$JS; _jstr "$ca"; C=$JS
      printf '{"a": "%s", "b": "%s", "component": "%s"}' "$A" "$B" "$C"
    fi
  done <<EOF2
$OWNS_PAIRS
EOF2
done <<EOF3
$OWNS_PAIRS
EOF3
printf ']\n}\n'
