#!/usr/bin/env bash
# env-doctor WSL performance branch -- READ-ONLY measured probes, run INSIDE the distro:
#
#   wsl.exe -d <distro> -- bash -s -- [/mnt/c/path/to/project] [files=200] < wsl_perf_probe.sh
#
# Each probe prints one line:  PROBE <name>: <measurement> -> <verdict>
# It reads files and /proc only; it writes, kills and installs nothing. The /mnt/c sample is
# bounded (maxdepth 4, first N files) so the probe itself cannot hang on a slow 9p walk.
set -uo pipefail
export LC_ALL=C
PROJ="${1:-}"
N="${2:-200}"
H="$HOME"
say() { printf 'PROBE %s: %s -> %s\n' "$1" "$2" "$3"; }
ms_now() { date +%s%N; }

read_cost() {  # read_cost <dir> -> "<files> <total_ms>" reading up to N small files under dir
  local dir="$1" list t0 t1 n
  list=$(timeout 60 find "$dir" -maxdepth 4 -type f -size -64k \( -name '*.py' -o -name '*.xml' -o -name '*.js' -o -name '*.txt' -o -name '*.conf' \) 2>/dev/null | head -n "$N")
  n=$(printf '%s\n' "$list" | grep -c .)
  [ "$n" -gt 0 ] || { echo "0 0"; return; }
  t0=$(ms_now)
  printf '%s\n' "$list" | while IFS= read -r f; do cat -- "$f" > /dev/null 2>&1; done
  t1=$(ms_now)
  echo "$n $(( (t1 - t0) / 1000000 ))"
}

# --- where the code runs from ---------------------------------------------------------------
mnt_paths=()
while IFS= read -r d; do
  pid="${d#/proc/}"; pid="${pid%/cmdline}"
  args=$(tr '\0' ' ' 2>/dev/null < "$d") || continue
  case "$args" in *odoo-bin*|*manage.py\ runserver*|*node\ *|*uvicorn*|*gunicorn*) ;; *) continue ;; esac
  case "$args" in *wsl_perf_probe*) continue ;; esac
  cwd=$(readlink "/proc/$pid/cwd" 2>/dev/null)
  where=ext4; case "$cwd $args" in */mnt/[a-z]/*) where="/mnt (9p)"; mnt_paths+=("$cwd") ;; esac
  say "server pid $pid" "cwd=$cwd; ${args:0:110}" "code on $where"
done < <(ls /proc/[0-9]*/cmdline 2>/dev/null)
on_mnt=0; total=0
for f in "$H"/.config/*/*.conf; do
  [ -f "$f" ] || continue
  ap=$(sed -nE 's/^[[:space:]]*addons_path[[:space:]]*=[[:space:]]*//p' "$f" | head -1 | tr -d '\r')
  [ -n "$ap" ] || continue
  total=$((total + 1))
  case "$ap" in */mnt/[a-z]/*) on_mnt=$((on_mnt + 1)); [ -z "$PROJ" ] && PROJ="${ap%%,*}" ;; esac
done
[ "$total" -gt 0 ] && say "confs with addons_path on /mnt" "$on_mnt of $total" \
  "$([ "$on_mnt" -gt 0 ] && echo 'every module file is read through 9p (+ Windows Defender): expect slow start/first page' || echo ok)"
if [ -d "$H/odoo-sources" ]; then say "ext4 core mirror" "$H/odoo-sources present" "check it is selected (HEADs equal) before trusting it"
else say "ext4 core mirror" "none" "$([ "$on_mnt" -gt 0 ] && echo 'candidate fix 1: run read-only core/deps from an ext4 mirror' || echo n/a)"; fi

# --- per-file read cost: /mnt vs ext4 ---------------------------------------------------------
[ -z "$PROJ" ] && [ -d /mnt/c/Windows/System32/drivers/etc ] && PROJ=/mnt/c/Windows/System32/drivers/etc
if [ -n "$PROJ" ] && [ -d "$PROJ" ]; then
  read -r n1 t1 < <(read_cost "$PROJ")
  read -r n2 t2 < <(read_cost "$PROJ")
  if [ "$n1" -gt 0 ]; then
    c1=$(awk -v t="$t1" -v n="$n1" 'BEGIN{printf "%.2f", t/n}'); c2=$(awk -v t="$t2" -v n="$n2" 'BEGIN{printf "%.2f", t/n}')
    # judge the first (cold) pass: that is what a server start or a first page pays
    v=$(awk -v c="$c1" 'BEGIN{ if (c>5) print "SLOW: 9p + on-access scan; Odoo-size trees will take minutes to load"; else if (c>1) print "elevated"; else print "ok" }')
    say "read cost /mnt ($PROJ)" "$n1 files: ${c1} ms/file first pass, ${c2} ms/file second pass" "$v"
  fi
else
  say "read cost /mnt" "no /mnt path to sample (pass one as the first argument)" "skipped"
fi
base=""
for d in /usr/lib/python3*/ /usr/share/perl*/; do [ -d "$d" ] && base="$d" && break; done
if [ -n "$base" ]; then
  read -r n3 t3 < <(read_cost "$base")
  [ "$n3" -gt 0 ] && say "read cost ext4 ($base)" "$n3 files: $(awk -v t="$t3" -v n="$n3" 'BEGIN{printf "%.2f", t/n}') ms/file" "baseline (healthy is well under 1 ms)"
fi

# --- memory, OOM, CPU ------------------------------------------------------------------------
read -r _ mt mu mf _ _ ma < <(free -m | awk '/^Mem:/')
read -r _ st su _ < <(free -m | awk '/^Swap:/')
say memory "total ${mt} MiB, available ${ma} MiB, swap ${su}/${st} MiB used" \
  "$(awk -v a="$ma" -v t="$mt" 'BEGIN{ if (t>0 && a/t<0.10) print "LOW: OOM kills likely (raise memory= in .wslconfig or run fewer heavy jobs)"; else print "ok" }')"
oom=$(dmesg 2>/dev/null | grep -ciE 'out of memory|oom-kill|killed process')
if [ -z "$oom" ] || ! dmesg >/dev/null 2>&1; then oom=$(journalctl -k -b --no-pager 2>/dev/null | grep -ciE 'out of memory|oom-kill|killed process'); fi
say "OOM kills since boot" "${oom:-unknown (dmesg/journal not readable)}" "$([ "${oom:-0}" -gt 0 ] 2>/dev/null && echo 'the memory cap is being hit' || echo ok)"
cores=$(nproc); load=$(cut -d' ' -f1 /proc/loadavg)
heavy=0; tests=0; declare -A per_db
while IFS= read -r d; do
  args=$(tr '\0' ' ' 2>/dev/null < "$d") || continue
  case "$args" in *wsl_perf_probe*) continue ;; esac
  case "$args" in *odoo-bin*|*pytest*|*"manage.py test"*|*"playwright test"*|*pg_restore*|*pg_dump\ *) heavy=$((heavy + 1)) ;; esac
  case "$args" in *--test-enable*|*pytest*|*"manage.py test"*) tests=$((tests + 1)) ;; esac
  db=$(printf '%s' "$args" | grep -oE '(^| )(-d|--database)[ =][A-Za-z0-9_.-]+' | head -1 | sed -E 's/.*[ =]//')
  case "$args" in *odoo-bin*) [ -n "$db" ] && per_db[$db]=$(( ${per_db[$db]:-0} + 1 )) ;; esac
done < <(ls /proc/[0-9]*/cmdline 2>/dev/null)
say cpu "$cores cores, load $load, $heavy heavy process(es), $tests test run(s)" \
  "$(awk -v l="$load" -v c="$cores" -v t="$tests" 'BEGIN{ if (t>2) print "TOO MANY test runs: each one slows the others 2-4x; keep at most 2"; else if (l>c*1.5) print "oversubscribed"; else print "ok" }')"
for db in "${!per_db[@]}"; do
  [ "${per_db[$db]}" -gt 1 ] && say "servers on one database" "$db: ${per_db[$db]} odoo-bin processes" "duplicate servers on one DB fight over its registry and cron locks"
done

# --- disk ---------------------------------------------------------------------------------------
read -r used size < <(df -B1 --output=used,size / | tail -1)
say "root filesystem" "$(awk -v u="$used" 'BEGIN{printf "%.1f", u/1073741824}') GiB used of $(awk -v s="$size" 'BEGIN{printf "%.0f", s/1073741824}') GiB" \
  "compare with the ext4.vhdx size on Windows (host_probe.py); a much larger image needs /env-doctor:clean --scope wsl-disk"
exit 0
