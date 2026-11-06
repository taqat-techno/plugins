#!/usr/bin/env bash
# env-doctor -- READ-ONLY "is this Linux environment quiet?" gate.
#
#   bash idle_gate.sh [quiet_minutes=10]
#
# Prints `IDLE`, or one `BUSY:<reason>` line per reason, and exits 0 when idle, 1 when busy.
# Use it before `wsl --shutdown`, a VHDX compaction, a WSL restart or a heavy job. Pass the
# gate twice, 60 s apart, before acting (a job can be between steps on the first look).
#
# Busy when any of these hold:
#   * a long job is running: --stop-after-init, --test-enable, pg_dump, pg_restore,
#     `odoo-bin shell`, pytest, `manage.py test`, playwright test;
#   * a server log a conf names (logfile=) or a file under ENVDOC_LOG_DIRS was written in the
#     last <quiet_minutes>;
#   * a Postgres cluster has an active client query (state = active, not this probe).
# It matches process command lines read from /proc, never with `pgrep -f`, so it cannot
# match itself.
set -uo pipefail
export LC_ALL=C
QUIET="${1:-10}"
H="${HOME:-/root}"
busy=()

self=$$
for d in /proc/[0-9]*; do
  pid="${d#/proc/}"
  [ "$pid" = "$self" ] && continue
  [ "$pid" = "$PPID" ] && continue
  args=$(tr '\0' ' ' 2>/dev/null < "$d/cmdline") || continue  # 2> first: the process may be gone
  [ -n "$args" ] || continue
  case "$args" in
    *idle_gate.sh*) continue ;;
    *--stop-after-init*|*--test-enable*|*"odoo-bin shell"*|*"odoo shell"*) busy+=("job pid $pid: ${args:0:120}") ;;
    pg_dump\ *|*/pg_dump\ *|pg_restore\ *|*/pg_restore\ *) busy+=("dump/restore pid $pid: ${args:0:120}") ;;
    *" -m pytest"*|pytest\ *|*/pytest\ *|*"manage.py test"*|*"playwright test"*) busy+=("test run pid $pid: ${args:0:120}") ;;
  esac
done

logs=()
for f in "$H"/.config/*/*.conf "$H"/.config/*/conf/*.conf; do
  [ -f "$f" ] || continue
  l=$(sed -nE 's/^[[:space:]]*logfile[[:space:]]*=[[:space:]]*//p' "$f" | head -1 | tr -d '\r')
  l="${l/#\~/$H}"
  [ -n "$l" ] && [ "$l" != False ] && [ -f "$l" ] && logs+=("$l")
done
for d in ${ENVDOC_LOG_DIRS:-}; do
  [ -d "$d" ] && while IFS= read -r f; do logs+=("$f"); done < <(find "$d" -maxdepth 2 -type f -name '*.log' 2>/dev/null)
done
if [ "${#logs[@]}" -gt 0 ]; then
  while IFS= read -r f; do busy+=("log written in the last ${QUIET} min: $f"); done \
    < <(find "${logs[@]}" -maxdepth 0 -mmin "-$QUIET" 2>/dev/null | sort -u | head -5)
fi

if command -v psql >/dev/null 2>&1; then
  ports=()
  command -v pg_lsclusters >/dev/null 2>&1 && while read -r _ _ port status _; do
    [ "$status" = online ] && ports+=("$port")
  done < <(pg_lsclusters -h 2>/dev/null)
  logins=("")  # the current user over the socket, then each db_user a conf names, over TCP (~/.pgpass)
  while IFS= read -r u; do [ -n "$u" ] && logins+=("-h 127.0.0.1 -U $u"); done < <(
    sed -nE 's/^[[:space:]]*db_user[[:space:]]*=[[:space:]]*([A-Za-z0-9_.-]+).*/\1/p' "$H"/.config/*/*.conf 2>/dev/null | sort -u)
  for port in "${ports[@]}"; do
    n=""
    for login in "${logins[@]}"; do
      # shellcheck disable=SC2086
      n=$(PGCONNECT_TIMEOUT=5 timeout 8 psql -X -w -At $login -p "$port" -d postgres -c \
        "select count(*) from pg_stat_activity where state = 'active' and backend_type = 'client backend' and pid <> pg_backend_pid()" 2>/dev/null) && break
    done
    if [ -z "$n" ]; then busy+=("cannot read pg_stat_activity on port $port (treated as busy)")
    elif [ "$n" != 0 ]; then busy+=("$n active query(ies) on port $port"); fi
  done
fi

if [ "${#busy[@]}" -eq 0 ]; then echo IDLE; exit 0; fi
printf 'BUSY:%s\n' "${busy[@]}"
exit 1
