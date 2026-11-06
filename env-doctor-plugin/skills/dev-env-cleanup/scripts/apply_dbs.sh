#!/usr/bin/env bash
# env-doctor dev-env-cleanup -- back up and drop the databases of an APPROVED plan.
#
#   bash apply_dbs.sh dry|run <dbs.tsv> [backup_dir]
#
# <dbs.tsv> comes from `plan.py emit`, one database per line:
#   <port><TAB><db><TAB><backup 0|1><TAB><host or -><TAB><user or -><TAB><filestore path or ->
# backup_dir defaults to ~/env-doctor-backups/clean_<date>/ (created only in run mode).
#
# Per database, in run mode:
#   1. refuse system databases and names outside [A-Za-z0-9_.-];
#   2. re-check open connections NOW and skip the database if any (no FORCE, ever);
#   3. when backup=1: `pg_dump -Fc` streamed to <backup_dir>/<db>.dump, then verify the dump's
#      table of contents has one TABLE DATA entry per table in the live database; filestore
#      (if given) -> <db>.filestore.tgz. Any failure skips the drop;
#   4. `DROP DATABASE` with the name passed as a psql variable (never spliced into SQL).
# `dry` prints the same decisions and changes nothing. Every action is logged to
# ~/.local/state/env-doctor/clean_<date>.log. Restore: pg_restore -p <port> -C -d postgres <db>.dump
set -euo pipefail
export LC_ALL=C

MODE="${1:-dry}"; [ "$MODE" = run ] || MODE=dry
LIST="${2:?usage: apply_dbs.sh dry|run <dbs.tsv> [backup_dir]}"
case "$LIST" in [A-Za-z]:\\*|[A-Za-z]:/*) LIST=$(wslpath -u "$LIST") ;; esac
[ -f "$LIST" ] || { echo "ERROR list not found: $LIST" >&2; exit 2; }
H="${HOME:?HOME is not set}"
BACKUP="${3:-$H/env-doctor-backups/clean_$(date +%Y%m%d)}"
LOGDIR="$H/.local/state/env-doctor"; LOG="$LOGDIR/clean_$(date +%Y%m%d).log"
log() { printf '%s %s\n' "$(date '+%F %T')" "$*" | { [ "$MODE" = run ] && { mkdir -p "$LOGDIR"; tee -a "$LOG"; } || cat; }; }

psqlc() {  # psqlc <port> <host> <user> <db> [psql args...]
  local port="$1" host="$2" user="$3" db="$4"; shift 4
  PGCONNECT_TIMEOUT=10 psql -X -w -At -v ON_ERROR_STOP=1 ${host:+-h "$host"} ${user:+-U "$user"} -p "$port" -d "$db" "$@"
}

failed=0; dropped=0
while IFS=$'\t' read -r port db backup host user fs || [ -n "${port:-}" ]; do
  port="${port%$'\r'}"; db="${db:-}"; backup="${backup:-1}"; fs="${fs:-}"; fs="${fs%$'\r'}"
  [ -z "$port" ] && continue
  case "$port" in \#*) continue ;; esac
  [ "$host" = - ] && host=""; [ "$user" = - ] && user=""; [ "$fs" = - ] && fs=""
  if ! [[ "$port" =~ ^[0-9]+$ ]] || ! [[ "$db" =~ ^[A-Za-z0-9_.-]+$ ]]; then
    log "REFUSE '$db'@'$port': bad port or database name"; failed=$((failed + 1)); continue
  fi
  case "$db" in postgres|template0|template1) log "REFUSE $db@$port: system database"; failed=$((failed + 1)); continue ;; esac
  exists=$(psqlc "$port" "$host" "$user" postgres -v name="$db" <<<"select count(*) from pg_database where datname = :'name';" 2>/dev/null || echo ERR)
  if [ "$exists" = ERR ]; then log "FAIL $db@$port: cannot connect"; failed=$((failed + 1)); continue; fi
  if [ "$exists" = 0 ]; then log "SKIP $db@$port: already gone"; continue; fi
  conns=$(psqlc "$port" "$host" "$user" postgres -v name="$db" <<<"select count(*) from pg_stat_activity where datname = :'name';")
  if [ "$conns" != 0 ]; then log "SKIP $db@$port: $conns open connection(s) now (never forced)"; continue; fi
  size=$(psqlc "$port" "$host" "$user" postgres -v name="$db" <<<"select pg_size_pretty(pg_database_size(:'name'));")
  if [ "$MODE" = dry ]; then
    if [ "$backup" = 1 ]; then how=" after pg_dump -Fc to $BACKUP/$db.dump${fs:+ + filestore tgz}"; else how=" (no dump: small inactive dev copy)"; fi
    log "DRY drop $db@$port ($size)$how"
    continue
  fi
  if [ "$backup" = 1 ]; then
    mkdir -p -- "$BACKUP"
    dump="$BACKUP/$db.dump"
    if ! PGCONNECT_TIMEOUT=10 pg_dump -w -Fc ${host:+-h "$host"} ${user:+-U "$user"} -p "$port" -d "$db" > "$dump"; then
      log "FAIL $db@$port: pg_dump failed; not dropped"; failed=$((failed + 1)); continue
    fi
    toc=$(pg_restore -l "$dump" | grep -c ' TABLE DATA ' || true)
    # one TABLE DATA entry per ordinary table (unlogged included, temp excluded) outside system schemas
    tables=$(psqlc "$port" "$host" "$user" "$db" <<<"select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace where c.relkind = 'r' and c.relpersistence <> 't' and n.nspname not in ('pg_catalog', 'information_schema') and n.nspname not like 'pg\_toast%' and n.nspname not like 'pg\_temp%';")
    if [ "$toc" -lt "$tables" ]; then
      log "FAIL $db@$port: dump TOC has $toc TABLE DATA entries for $tables tables; not dropped (dump kept at $dump)"
      failed=$((failed + 1)); continue
    fi
    if [ -n "$fs" ] && [ -d "$fs" ]; then
      if ! tar -czf "$BACKUP/$db.filestore.tgz" -C "$(dirname -- "$fs")" -- "$(basename -- "$fs")"; then
        log "FAIL $db@$port: filestore archive failed; not dropped"; failed=$((failed + 1)); continue
      fi
    fi
    log "BACKUP $db@$port -> $dump ($(du -h -- "$dump" | cut -f1), $toc table entries)${fs:+ + $db.filestore.tgz}"
  fi
  conns=$(psqlc "$port" "$host" "$user" postgres -v name="$db" <<<"select count(*) from pg_stat_activity where datname = :'name';")
  if [ "$conns" != 0 ]; then log "SKIP $db@$port: a connection appeared during the backup; not dropped"; continue; fi
  if psqlc "$port" "$host" "$user" postgres -v name="$db" <<<'DROP DATABASE :"name";' >/dev/null; then
    log "DROPPED $db@$port ($size)"; dropped=$((dropped + 1))
  else
    log "FAIL $db@$port: DROP DATABASE failed"; failed=$((failed + 1))
  fi
done < "$LIST"

log "SUMMARY mode=$MODE dropped=$dropped failed_or_refused=$failed backups=$BACKUP"
[ "$failed" -eq 0 ]
