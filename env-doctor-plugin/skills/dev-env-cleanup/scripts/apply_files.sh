#!/usr/bin/env bash
# env-doctor dev-env-cleanup -- delete or archive the paths of an APPROVED plan.
#
#   bash apply_files.sh dry|run <list.tsv>
#
# <list.tsv> comes from `plan.py emit` (files.tsv or confs.tsv), one action per line:
#   delete<TAB><absolute path>
#   archive<TAB><absolute path><TAB><destination dir>
# A Windows path to the list (C:\...) is converted with wslpath.
#
# `dry` (the default if the mode is anything but `run`) prints what would happen and
# changes nothing. `run` acts, and logs every action to
# ~/.local/state/env-doctor/clean_<date>.log.
#
# Guards, each of which refuses the line (never the whole run silently):
#   * empty, relative, `..`-containing or glob-character paths;
#   * paths outside the allow-list of prefixes below, or equal to a prefix itself;
#   * paths whose resolved location (symlinks followed) leaves the allow-list;
#   * a data dir that any live ~/.config/*/*.conf still names as its data_dir;
#   * archive of anything but a *.conf file, or into a destination outside its own folder.
# It never builds a command from a string: every path is quoted and `rm` is called as
# `rm -rf -- "${p:?}"`. This is the guard the 2026-09-29 incident (an empty $d in
# `wsl -- bash -lc "... rm -rf ~/.local/share/Odoo/$d"`) did not have.
set -euo pipefail
export LC_ALL=C

MODE="${1:-dry}"; [ "$MODE" = run ] || MODE=dry
LIST="${2:?usage: apply_files.sh dry|run <list.tsv>}"
case "$LIST" in [A-Za-z]:\\*|[A-Za-z]:/*) LIST=$(wslpath -u "$LIST") ;; esac
[ -f "$LIST" ] || { echo "ERROR list not found: $LIST" >&2; exit 2; }

H="${HOME:?HOME is not set}"
case "$H" in /|"") echo "ERROR refusing to run with HOME=$H" >&2; exit 2 ;; esac
ALLOW=(
  "$H/.local/share/Odoo/"
  "$H/.local/share/odoo/"
  "$H/tmp/"
  "$H/.cache/pip/" "$H/.cache/uv/" "$H/.npm/_cacache/" "$H/.cache/yarn/" "$H/.cache/pnpm/" "$H/.cache/go-build/"
  "$H/.config/"
)
# Exact roots that are never removed even though they sit under an allowed prefix.
NEVER=("$H/.local/share/Odoo/addons" "$H/.local/share/odoo/addons" "$H/.local/share/Odoo/filestore" "$H/.local/share/odoo/filestore" "$H/.config")
# The cache roots themselves may go (they are rebuilt); everything else must be strictly inside a prefix.
CACHE_ROOTS=("$H/.cache/pip" "$H/.cache/uv" "$H/.npm/_cacache" "$H/.cache/yarn" "$H/.cache/pnpm" "$H/.cache/go-build")

LOGDIR="$H/.local/state/env-doctor"; LOG="$LOGDIR/clean_$(date +%Y%m%d).log"
log() { printf '%s %s\n' "$(date '+%F %T')" "$*" | { [ "$MODE" = run ] && { mkdir -p "$LOGDIR"; tee -a "$LOG"; } || cat; }; }

allowed() {  # allowed <path>: inside an allow-list prefix, not a prefix itself, not a NEVER root
  local p="$1" a r
  for r in "${NEVER[@]}"; do [ "$p" = "$r" ] && return 1; done
  for r in "${CACHE_ROOTS[@]}"; do [ "$p" = "$r" ] && return 0; done
  for a in "${ALLOW[@]}"; do
    case "$p" in "$a"?*) return 0 ;; esac
  done
  return 1
}

conf_data_dirs() {
  local f
  for f in "$H"/.config/*/*.conf "$H"/.config/*/conf/*.conf; do
    [ -f "$f" ] || continue
    sed -nE 's/^[[:space:]]*data_dir[[:space:]]*=[[:space:]]*//p' "$f" | tr -d '\r' | sed -E "s#^~#$H#; s#/+\$##"
  done
}
# bash 3.2 (macOS) has no mapfile
LIVE_DATA_DIRS=()
while IFS= read -r _d; do LIVE_DATA_DIRS+=("$_d"); done < <(conf_data_dirs | sort -u)

refused=0; done_n=0
while IFS=$'\t' read -r action path dest || [ -n "${action:-}" ]; do
  action="${action%$'\r'}"; path="${path%$'\r'}"; dest="${dest:-}"; dest="${dest%$'\r'}"
  [ -z "$action" ] && continue
  case "$action" in \#*) continue ;; esac
  why=""
  if [ -z "${path:-}" ]; then why="empty path"
  elif [ "${path#/}" = "$path" ]; then why="not absolute"
  elif [[ "$path" == *"/../"* || "$path" == *"/.." || "$path" == *"/./"* ]]; then why="contains . or .. segments"
  elif [[ "$path" == *[\*\?\[]* ]]; then why="contains glob characters"
  fi
  path="${path%/}"
  if [ -z "$why" ] && ! allowed "$path"; then why="outside the allow-list"; fi
  if [ -z "$why" ] && [ -e "$path" ]; then
    real=$(realpath -m -- "$path")
    allowed "$real" || why="resolves outside the allow-list ($real)"
  fi
  if [ -z "$why" ]; then
    for d in ${LIVE_DATA_DIRS[@]+"${LIVE_DATA_DIRS[@]}"}; do  # bash 3.2 + set -u: empty array is unbound
      if [ -n "$d" ] && [ "$path" = "$d" ]; then why="still the data_dir of a live conf"; fi
    done
  fi
  if [ -z "$why" ] && [ ! -e "$path" ] && [ ! -L "$path" ]; then
    log "SKIP $action $path (already gone)"; continue
  fi
  case "$action" in
    delete) : ;;
    archive)
      [[ "$path" == *.conf && -f "$path" ]] || why="${why:-archive takes a .conf file only}"
      [ -n "$dest" ] && [ "$(dirname -- "$dest")" = "$(dirname -- "$path")" ] || why="${why:-archive destination must sit next to the conf}"
      ;;
    *) why="unknown action '$action'" ;;
  esac
  if [ -n "$why" ]; then
    log "REFUSE $action $path: $why"; refused=$((refused + 1)); continue
  fi
  size=$(du -sh -- "$path" 2>/dev/null | cut -f1)
  if [ "$MODE" = dry ]; then
    log "DRY $action ${size:-?} $path${dest:+ -> $dest/}"; continue
  fi
  if [ "$action" = delete ]; then
    rm -rf -- "${path:?}"
    log "DELETED ${size:-?} $path"
  else
    mkdir -p -- "${dest:?}"
    mv -n -- "${path:?}" "${dest:?}/"
    log "ARCHIVED $path -> $dest/"
  fi
  done_n=$((done_n + 1))
done < "$LIST"

log "SUMMARY mode=$MODE acted=$done_n refused=$refused list=$LIST"
[ "$refused" -eq 0 ]
