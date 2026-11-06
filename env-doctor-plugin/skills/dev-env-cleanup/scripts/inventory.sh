#!/usr/bin/env bash
# env-doctor dev-env-cleanup -- READ-ONLY inventory of accumulated local state.
#
# Prints one tab-separated record per line on stdout; plan.py turns it into a plan.
# It deletes, moves and writes nothing (not even a temp file). Run it inside the Linux
# environment that owns the state (WSL: `wsl.exe -d <distro> -- bash -s -- <scope> < inventory.sh`).
#
#   bash inventory.sh [all|db|files|docker|wsl-disk]        (default: all)
#
# Records (field 1 = kind):
#   meta     <key> <value>
#   df       <mount> <used_bytes> <size_bytes>
#   conf     <path> <mtime> <db_name> <db_port> <db_host> <db_user> <data_dir> <logfile> <dbfilter>
#   cluster  <version> <name> <port> <status> <conn: socket | tcp:<host>:<user> | unreachable>
#   db       <port> <name> <size_bytes> <open_conns> <last_stats_epoch> <last_login_epoch> <is_odoo>
#   datadir  <path> <size_bytes> <mtime>
#   filestore <data_dir> <db_name> <size_bytes> <mtime>
#   path     <category: tmp|cache|log> <path> <size_bytes> <mtime>
#   journal  <bytes>
#   docker   <type> <size> <reclaimable>
#   proc     <pid> <elapsed_s> <args>
#   ref      <value> <file>          values from tool state files (~/.config/*/**/*.env)
#   keep     <pattern>               lines of ~/.config/env-doctor/keep.txt
#   note     <text>                  a probe that could not run, and why
#
# Database access: the current user over the local socket first, then each (host, user)
# a conf names for that port with `-w` (never prompts; uses ~/.pgpass). A conf's
# db_password is used only when ENVDOC_USE_CONF_PASSWORD=1, passed to psql through its
# environment and never printed.
set -uo pipefail
export LC_ALL=C

SCOPE="${1:-all}"
H="${ENVDOC_HOME:-$HOME}"
NOW=$(date +%s)

rec() { local IFS=$'\t'; printf '%s\n' "$*"; }
note() { rec note "$*"; }
size_of() { du -sb -- "$1" 2>/dev/null | cut -f1; }
mtime_of() { stat -c %Y -- "$1" 2>/dev/null || echo 0; }
want() { [ "$SCOPE" = all ] || [ "$SCOPE" = "$1" ]; }
clean() { tr '\t\r\n' '   '; }

rec meta now "$NOW"
rec meta user "$(id -un)"
rec meta home "$H"
rec meta host "$(hostname 2>/dev/null || echo unknown)"
rec meta scope "$SCOPE"
[ -n "${WSL_DISTRO_NAME:-}" ] && rec meta distro "$WSL_DISTRO_NAME"
read -r used size < <(df -B1 --output=used,size / 2>/dev/null | tail -1) && rec df / "$used" "$size"

# ------------------------------------------------------------------ confs (always: keep-list input)
conf_val() { sed -nE "s/^[[:space:]]*$2[[:space:]]*=[[:space:]]*//p" "$1" 2>/dev/null | head -1 | clean | sed -E 's/[[:space:]]+$//'; }
CONFS=()
for f in "$H"/.config/*/*.conf "$H"/.config/*/conf/*.conf ${ENVDOC_CONF_DIRS:+$(printf '%s/*.conf ' $ENVDOC_CONF_DIRS)}; do
  [ -f "$f" ] || continue
  grep -qE '^[[:space:]]*\[options\]' "$f" 2>/dev/null || continue   # Odoo-style server confs only
  CONFS+=("$f")
  dd=$(conf_val "$f" data_dir); dd="${dd/#\~/$H}"
  rec conf "$f" "$(mtime_of "$f")" "$(conf_val "$f" db_name)" "$(conf_val "$f" db_port)" \
      "$(conf_val "$f" db_host)" "$(conf_val "$f" db_user)" "$dd" "$(conf_val "$f" logfile)" "$(conf_val "$f" dbfilter)"
done

# ------------------------------------------------------------------ keep file + tool state refs
if [ -f "$H/.config/env-doctor/keep.txt" ]; then
  while IFS= read -r line; do
    line="${line%$'\r'}"; [ -n "${line// }" ] && rec keep "$line"
  done < <(grep -vE '^[[:space:]]*(#|$)' "$H/.config/env-doctor/keep.txt")
fi
while IFS= read -r f; do
  while IFS= read -r v; do [ -n "$v" ] && rec ref "$v" "$f"; done \
    < <(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?[A-Za-z_][A-Za-z0-9_]*=["'\'']?([A-Za-z0-9_.-]+)["'\'']?[[:space:]]*$/\2/p' "$f" 2>/dev/null)
done < <(find "$H/.config" -mindepth 2 -maxdepth 4 -name '*.env' -type f 2>/dev/null)

# ------------------------------------------------------------------ running servers (keep-list input)
while read -r pid et args; do
  rec proc "$pid" "$et" "$(printf '%s' "$args" | clean)"
done < <(ps -eo pid=,etimes=,args= 2>/dev/null | grep -E '[o]doo(-bin)?([[:space:]]|$)|[m]anage\.py|[p]ostgres: .* (pg_dump|pg_restore)' )

# ------------------------------------------------------------------ databases
pg_try() {  # pg_try <port> <host-or-empty> <user-or-empty> <password-or-empty> -> exit 0 when it connects
  local port="$1" host="$2" user="$3" pw="$4"
  PGPASSWORD="$pw" PGCONNECT_TIMEOUT=5 timeout 10 psql -X -w -At ${host:+-h "$host"} ${user:+-U "$user"} \
    -p "$port" -d postgres -c 'select 1' >/dev/null 2>&1
}
declare -A CONN_HOST CONN_USER CONN_PW CL_VER CL_NAME CL_STATUS
if want db; then
  if ! command -v psql >/dev/null 2>&1; then
    note "psql not found; database inventory skipped"
  else
    ports=()
    if command -v pg_lsclusters >/dev/null 2>&1; then
      while read -r ver name port status _; do
        ports+=("$port"); CL_VER[$port]="$ver"; CL_NAME[$port]="$name"; CL_STATUS[$port]="$status"
      done < <(pg_lsclusters -h 2>/dev/null)
    fi
    for f in "${CONFS[@]}"; do p=$(conf_val "$f" db_port); [ -n "$p" ] && ports+=("$p"); done
    for p in ${ENVDOC_PG_PORTS:-}; do ports+=("$p"); done
    mapfile -t ports < <(printf '%s\n' "${ports[@]}" | grep -E '^[0-9]+$' | sort -un)
    for port in "${ports[@]}"; do
      conn=unreachable
      if pg_try "$port" "" "" ""; then
        conn=socket; CONN_HOST[$port]=""; CONN_USER[$port]=""; CONN_PW[$port]=""
      else
        for f in "${CONFS[@]}"; do
          [ "$(conf_val "$f" db_port)" = "$port" ] || continue
          h=$(conf_val "$f" db_host); u=$(conf_val "$f" db_user); [ "$h" = False ] && h=""; [ -z "$h" ] && h=127.0.0.1
          pw=""; [ "${ENVDOC_USE_CONF_PASSWORD:-0}" = 1 ] && pw=$(conf_val "$f" db_password)
          if pg_try "$port" "$h" "$u" "$pw"; then
            conn="tcp:$h:$u"; CONN_HOST[$port]="$h"; CONN_USER[$port]="$u"; CONN_PW[$port]="$pw"; break
          fi
        done
      fi
      rec cluster "${CL_VER[$port]:-?}" "${CL_NAME[$port]:-?}" "$port" "${CL_STATUS[$port]:-?}" "$conn"
      [ "$conn" = unreachable ] && { note "port $port: no login worked (socket as $(id -un), or conf users via ~/.pgpass); its databases are not listed and orphan checks are disabled"; continue; }
      q() {  # q <db> <sql>
        PGPASSWORD="${CONN_PW[$port]}" PGCONNECT_TIMEOUT=5 timeout 30 psql -X -w -At -F $'\t' \
          ${CONN_HOST[$port]:+-h "${CONN_HOST[$port]}"} ${CONN_USER[$port]:+-U "${CONN_USER[$port]}"} -p "$port" -d "$1" -c "$2" 2>/dev/null
      }
      while IFS=$'\t' read -r name size conns allow; do
        [ -n "$name" ] || continue
        last=0; login=0; odoo=0
        if [ "$allow" = t ]; then
          last=$(q "$name" "select coalesce(extract(epoch from max(greatest(last_vacuum,last_autovacuum,last_analyze,last_autoanalyze)))::bigint,0) from pg_stat_user_tables")
          if [ "$(q "$name" "select to_regclass('public.ir_module_module') is not null")" = t ]; then
            odoo=1
            login=$(q "$name" "select coalesce(extract(epoch from max(create_date))::bigint,0) from res_users_log")
          fi
        fi
        rec db "$port" "$name" "$size" "$conns" "${last:-0}" "${login:-0}" "$odoo"
      done < <(q postgres "select d.datname, pg_database_size(d.oid), (select count(*) from pg_stat_activity a where a.datname=d.datname and a.pid<>pg_backend_pid()), d.datallowconn from pg_database d where not d.datistemplate order by 2 desc")
    done
  fi
fi

# ------------------------------------------------------------------ data dirs, filestores, tmp, caches, logs
if want files || want db; then
  declare -A SEEN
  dirs=()
  for f in "${CONFS[@]}"; do d=$(conf_val "$f" data_dir); d="${d/#\~/$H}"; [ -n "$d" ] && dirs+=("$d"); done
  for base in "$H/.local/share/Odoo" "$H/.local/share/odoo"; do
    [ -d "$base" ] || continue
    dirs+=("$base")
    for c in "$base"/*/; do
      c="${c%/}"; n="${c##*/}"
      case "$n" in addons|filestore|sessions) continue ;; esac
      dirs+=("$c")
    done
  done
  for d in "${dirs[@]}"; do
    [ -d "$d" ] || continue
    [ -n "${SEEN[$d]:-}" ] && continue; SEEN[$d]=1
    case "$d" in "$H/.local/share/Odoo"|"$H/.local/share/odoo") : ;; *) rec datadir "$d" "$(size_of "$d")" "$(mtime_of "$d")" ;; esac
    for fs in "$d"/filestore/*/; do
      [ -d "$fs" ] || continue; fs="${fs%/}"
      rec filestore "$d" "${fs##*/}" "$(size_of "$fs")" "$(mtime_of "$fs")"
    done
  done
fi
if want files; then
  if [ -d "$H/tmp" ]; then
    for p in "$H"/tmp/* "$H"/tmp/.[!.]*; do [ -e "$p" ] && rec path tmp "$p" "$(size_of "$p")" "$(mtime_of "$p")"; done
  fi
  for c in .cache/pip .cache/uv .npm/_cacache .cache/yarn .cache/pnpm .cache/JetBrains .cache/ms-playwright .cache/ms-playwright-mcp .cache/odoo-src .cache/go-build; do
    [ -d "$H/$c" ] && rec path cache "$H/$c" "$(size_of "$H/$c")" "$(mtime_of "$H/$c")"
  done
  for f in "${CONFS[@]}"; do
    l=$(conf_val "$f" logfile); l="${l/#\~/$H}"
    [ -n "$l" ] && [ "$l" != False ] && [ -f "$l" ] && rec path log "$l" "$(size_of "$l")" "$(mtime_of "$l")"
  done
  if command -v journalctl >/dev/null 2>&1; then
    j=$(journalctl --disk-usage 2>/dev/null | grep -oE '[0-9.]+[KMGT]?B?' | head -1)
    [ -n "$j" ] && rec journal "$j"
  fi
fi

# ------------------------------------------------------------------ docker
if want docker; then
  if command -v docker >/dev/null 2>&1; then
    # Docker Desktop's WSL shim prints an "activate the WSL integration" text and exits non-zero.
    if out=$(timeout 15 docker system df --format '{{.Type}}\t{{.Size}}\t{{.Reclaimable}}' 2>/dev/null) && [ -n "$out" ]; then
      while IFS=$'\t' read -r t s r; do
        [ -n "$t" ] && [ -n "${s:-}" ] && rec docker "$t" "$s" "$(printf '%s' "${r:-}" | clean)"
      done <<<"$out"
    else
      note "docker did not answer (daemon stopped, or Desktop's WSL integration is off for this distro); docker skipped"
    fi
  fi
fi
exit 0
