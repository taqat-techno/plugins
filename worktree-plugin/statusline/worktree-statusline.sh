#!/usr/bin/env bash
# worktree-statusline.sh - Claude Code status line showing the active worktree.
#
#   [tree] wallet-fix | fix/wallet-131 | wallet-dev
#   [dot]  MAIN | develop
#
# Reads the status-line JSON payload on stdin. Written to be fork-free: on
# Windows every spawned process costs ~100ms and Claude Code re-runs this on a
# 300ms debounce, cancelling any render still in flight. The branch is read
# straight out of .git/HEAD rather than by shelling out to git.
#
# Environment overrides (optional):
#   WT_GLYPH_TREE   marker for "in a worktree"   (default: a tree emoji)
#   WT_GLYPH_MAIN   marker for the main checkout (default: a filled circle)
#   WT_SEP          separator                    (default: " | ")
#   WT_SHOW_DIRTY   set to 1 to append a dirty/ahead indicator. OFF by default:
#                   it costs a `git status` fork on every render.
#
# Always exits 0 and always prints something; a status line must never be able
# to disrupt a session.

RAW=$(cat 2>/dev/null)

GT=${WT_GLYPH_TREE-$'\xf0\x9f\x8c\xb3'}   # tree
GM=${WT_GLYPH_MAIN-$'\xe2\x97\x89'}       # circled dot
SEP=${WT_SEP- | }

V=''
OBJ=''

# _scope <key> -> OBJ : the brace-delimited body of a top-level object value.
# Matching on the quoted key means "worktree" never matches "git_worktree".
_scope() {
  local s=${RAW#*\"$1\"}
  OBJ=''
  [ "$s" = "$RAW" ] && return 1
  s=${s#*\{}
  OBJ=${s%%\}*}
  return 0
}

# _get <blob> <key> -> V : first string value for key inside blob.
_get() {
  local blob=$1 k=$2 s
  V=''
  s=${blob#*\"$k\"}
  [ "$s" = "$blob" ] && return 1
  s=${s#*:}
  while [ -n "$s" ] && { [ "${s#[[:space:]]}" != "$s" ]; }; do s=${s#?}; done
  case $s in
    \"*) s=${s#\"}; V=${s%%\"*}; return 0 ;;
  esac
  return 1
}

# ------------------------------------------------------------ payload reads ---
_get "$RAW" current_dir || _get "$RAW" cwd
DIR=$V

NAME=''; BRANCH=''; MARKER=$GM

# Tier 1: a --worktree / EnterWorktree session carries the answer already.
if _scope worktree; then
  _get "$OBJ" name   && NAME=$V
  _get "$OBJ" branch && BRANCH=$V
fi

# Tier 2: any linked git worktree, including ones made with `git worktree add`.
if [ -z "$NAME" ]; then
  _get "$RAW" git_worktree && NAME=$V
fi

if [ -n "$NAME" ]; then MARKER=$GT; else NAME=MAIN; fi

_get "$RAW" session_name && SESSION=$V || SESSION=''
AGENT=''
if _scope agent; then _get "$OBJ" name && AGENT=$V; fi

# --------------------------------------------------- branch from .git/HEAD ---
# Walk up for a .git entry. In a linked worktree .git is a file containing
# "gitdir: <path>"; that path holds the worktree's own HEAD.
if [ -z "$BRANCH" ] && [ -n "$DIR" ]; then
  d=$DIR gitdir='' i=0
  while [ -n "$d" ] && [ $i -lt 40 ]; do
    if [ -d "$d/.git" ]; then gitdir="$d/.git"; break; fi
    if [ -f "$d/.git" ]; then
      IFS= read -r line < "$d/.git" 2>/dev/null
      case $line in
        gitdir:*)
          g=${line#gitdir:}
          while [ "${g# }" != "$g" ]; do g=${g# }; done
          case $g in
            /*|[A-Za-z]:[/\\]*) gitdir=$g ;;
            *) gitdir="$d/$g" ;;
          esac
          ;;
      esac
      break
    fi
    parent=${d%/*}
    [ "$parent" = "$d" ] && break
    [ -z "$parent" ] && break
    d=$parent; i=$((i+1))
  done

  if [ -n "$gitdir" ] && [ -r "$gitdir/HEAD" ]; then
    IFS= read -r head < "$gitdir/HEAD" 2>/dev/null
    case $head in
      ref:*)
        b=${head#ref:}
        while [ "${b# }" != "$b" ]; do b=${b# }; done
        BRANCH=${b#refs/heads/}
        ;;
      ?*) BRANCH="@${head:0:7}" ;;   # detached HEAD
    esac
  fi
fi

# ------------------------------------------------------- optional indicator ---
EXTRA=''
if [ "${WT_SHOW_DIRTY:-0}" = 1 ] && [ -n "$DIR" ] && command -v git >/dev/null 2>&1; then
  st=$(git -C "$DIR" status --porcelain 2>/dev/null)
  if [ -n "$st" ]; then
    n=0
    while IFS= read -r l; do [ -n "$l" ] && n=$((n+1)); done <<< "$st"
    EXTRA=" *$n"
  fi
fi

# -------------------------------------------------------------------- print ---
if [ "$MARKER" = "$GT" ]; then out="$GT $NAME"; else out="$GM MAIN"; fi
[ -n "$BRANCH" ]  && out="$out$SEP$BRANCH"
[ -n "$EXTRA" ]   && out="$out$EXTRA"
[ -n "$SESSION" ] && out="$out$SEP$SESSION"
[ -n "$AGENT" ]   && out="$out$SEP@$AGENT"
printf '%s\n' "$out"
exit 0
