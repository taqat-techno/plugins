# WSL / local-service performance and host resource pressure

Branch for: "Odoo / Django / node is slow in WSL", "the first page or login takes minutes",
`PoolError: The Connection Pool Is Full` on a dev server, "WSL is laggy", `vmmem` eating
all RAM, a distro killed by the OOM killer, WSL refusing to boot with `Wsl/0x8007000e`, or
`wsl.exe` crashing with `0xc00000fd`.

Failure class: **performance / resource pressure** (the eighth class in the router's
taxonomy). A slow service whose code is fine is almost always one of four things, in this
order of likelihood: per-file I/O cost, memory pressure, CPU oversubscription, disk pressure.
Measure before you name one.

Everything here is read-only. Fixes are proposed, one at a time, for the user to apply.

## The cause chain to keep in mind

A dev server that reads its code through `/mnt/c` pays the Windows file-system cost for
**every** file it opens: the 9p bridge plus Windows Defender's on-access scan. Odoo opens
tens of thousands of small files at start-up and on the first asset build. With a healthy
disk a Windows-native read costs about 0.05 ms per file; on an org-managed machine with
Defender for Endpoint it has been measured at **31 ms per file** natively and **55 ms per file
through `/mnt/c`**, against well under 1 ms from the distro's own ext4 disk. That turned an
Odoo start-up of **50 s (core on ext4) into 343 s (core on `/mnt/c`)**, same database, same
conf, same commits.

Requests then stall in Python while holding a database cursor. With `workers = 0` and a
browser firing parallel asset requests, the connection pool fills and the server answers
`PoolError` / 500. The pool error is the **consequence**, not the cause: raising
`db_maxconn` hides it for a while and changes nothing. A Python-vs-SQL split from the server
log (e.g. average 28 s in Python vs 0.11 s in SQL per request) proves which side is slow.

## Probes

Run the two probe scripts first; they print `PROBE <name>: <measurement> -> <verdict>`
lines you can quote in the report. Both are read-only and bounded.

```bash
# Windows side (PowerShell, no elevation): drive, pagefile, commit, Defender/MDE state,
# Windows-native per-file read cost, WSL version, .wslconfig keys.
powershell -NoProfile -ExecutionPolicy Bypass -File "<plugin>/skills/env-doctor-router/scripts/windows_perf_probe.ps1" -Path C:\path\to\project

# Inside the distro (from Git Bash or PowerShell, script on stdin, never through bash -lc "..."):
wsl.exe -d <distro> -- bash -s -- /mnt/c/path/to/project 200 < "<plugin>/skills/env-doctor-router/scripts/wsl_perf_probe.sh"

# Disk images vs use (Windows side; does not start WSL):
python "<plugin>/skills/dev-env-cleanup/scripts/host_probe.py"
```

`wsl_perf_probe.sh` starts the distro if it is stopped (any `wsl.exe -d` does). That is a
read, not a change, but say so; never `wsl --shutdown` to "reset" a measurement.

What each probe answers:

| Probe | Healthy | Finding | Classification |
|---|---|---|---|
| `read cost /mnt (...)` vs `read cost ext4 (...)` | /mnt within a few × ext4 | /mnt over ~5 ms/file, ext4 under 1 ms | performance (file I/O through 9p) |
| `read cost Windows (...)` | ~0.05-0.5 ms/file | over ~5 ms/file | performance (on-access scanning) |
| `server pid ...` / `confs with addons_path on /mnt` | code on ext4 | interpreter, venv or addons path under `/mnt/c` | performance (code location) |
| `Defender real-time protection`, `Defender for Endpoint (Sense)`, `Defender exclusions` | workspace + VHDX folder excluded | real-time on, Sense running, exclusions hidden by policy | performance (needs IT) |
| `memory`, `OOM kills since boot` | available > 10 %, no OOM lines | low available, OOM lines, killed IDE backend / terminal | resource pressure (memory cap) |
| `cpu` / `servers on one database` | at most 2 test runs, load < 1.5 × cores | 3+ test runs, duplicate servers on one DB | resource pressure (CPU) |
| `system drive`, `pagefile`, `commit` | > 10 % free, pagefile ≥ 4 GB, commit < 85 % | C: under 10 %, pagefile shrunk to ~2.5 GB, commit near the limit | resource pressure (host) |
| `WSL version` | current | 2.6.3 | wrong version |
| `.wslconfig` | keys in the right section | `autoMemoryReclaim` / `sparseVhd` under `[wsl2]` | config-shadowing (ignored key) |
| `root filesystem` vs `host_probe.py` `vhdx` | image ≈ used | image ≫ used (it never shrinks) | resource pressure (disk) → cleanup skill |

Manual equivalents when a script cannot run: `Get-MpComputerStatus | Select
RealTimeProtectionEnabled,IsTamperProtected`; `Get-Service Sense`; `Get-CimInstance
Win32_PageFileUsage`; `(Get-CimInstance Win32_OperatingSystem) | Select
TotalVirtualMemorySize,FreeVirtualMemory`; inside WSL `free -m`, `nproc`, `cat /proc/loadavg`,
`readlink /proc/<pid>/cwd`, `journalctl -k -b | grep -i oom`.

Never use a recursive `find` or `git status` over a large `/mnt/c` tree as a probe: on a
slow 9p path they run for 8-30 minutes. The scripts cap the sample (maxdepth 4, first N files).

## Fix ladder (propose one, the user applies it, re-probe)

1. **Run read-only trees from ext4.** The biggest win for the least risk: keep a git mirror
   of the large read-mostly trees (framework core, enterprise addons, themes) on the
   distro's ext4 disk and point the server at it. Recipe, generalised from the Odoo case:
   - `git clone --no-checkout /mnt/c/.../sources/<ver>/<repo> ~/<mirror>/<ver>/<repo>`, then
     `git -C <mirror> checkout --force --detach <the Windows copy's HEAD SHA>`. Git reads a
     few large pack files, so this is fast even where copying the tree over 9p crawls
     (an rsync of the tree measured ~400 MB per 10 minutes).
   - Use the mirror **only while it is current**: a selector compares every mirror's
     `.git/HEAD` with the Windows copy's HEAD and falls back to the `/mnt/c` path, with a
     warning, the moment they differ. A stale mirror silently runs old code, which is worse
     than slow code.
   - Point confs at the mirror through an environment variable (`$ODOO_SOURCES/<ver>/...`
     in `addons_path`; Odoo expands it) rather than a hard path, so the selector stays in
     charge. Migrate confs with a dry-run + backup step, skipping confs of running servers.
   - Keep the code you edit (custom addons in the IDE) on Windows: mirroring it costs a
     re-stat per run and risks stale code.
   - Measured: first `/web/login` 343 s → 64 s, then 0.21 s; another project's first 200 in 20 s.
   If the odoo plugin is installed, its local-services tools own the Odoo specifics.
2. **Ask IT for Defender exclusions** for the workspace folder and the WSL disk image folder
   (and `vmmem`/`vmmemWSL`). With Tamper Protection on or Defender for Endpoint (`Sense`)
   running, the user cannot change them and must not try. Draft the request text:
   > Please add Microsoft Defender exclusions for my development workspace `<path>` and the
   > WSL disk image folder `<vhdx folder>` (processes `vmmem`, `vmmemWSL`). Measured cost
   > today: `<x>` ms per file opened on Windows (normal ≈ 0.05 ms), which makes local
   > servers take minutes to start.
3. **Move hot code into the distro** (`~/projects/...`) when edits can happen there
   (VS Code Remote-WSL / JetBrains remote dev). Optional; only after 1 and 2.
4. **Memory:** raise `memory=` in `%USERPROFILE%\.wslconfig` (`[wsl2]`) to cover the
   concurrent load (database + servers + IDE backend + agents); keep `swap=` as a cushion;
   `autoMemoryReclaim=gradual` belongs under `[experimental]` on WSL 2.x. Applies after
   `wsl --shutdown` — which the user runs, when WSL is idle (see `windows-wsl.md`, WSL restart
   protocol).
5. **CPU:** at most two heavy test runs at a time, one server per database. Cap a heavy
   background step instead of letting it starve the interactive server:
   `systemd-run --user --scope -p CPUQuota=300% -p MemoryMax=6G nice -n 19 <command>`
   (kept a live instance's median latency flat at ~250 ms through a restore + upgrade).
   Disk I/O cannot be capped this way inside WSL (`ionice`/`IOWeight` are no-ops); schedule
   restores off-hours. See the `long-running-jobs` skill.
6. **Host disk / pagefile:** free the system drive above 10 % (`/env-doctor:clean`), and if
   Windows shrank the pagefile, set an explicit size (elevated, user-run; e.g. initial 16 GB,
   maximum 40 GB). Low free space → small pagefile → low commit limit → WSL cannot reserve
   its memory → `Wsl/0x8007000e`. That error means memory pressure, not a corrupt VHDX.
7. **WSL version:** `wsl --update` when WSL is idle (2.6.3 → 3.0.3 fixed repeated `wsl.exe`
   `0xc00000fd` crashes). It restarts the WSL service, not the distro; it applies on the
   next WSL start.

Secondary slow-downs worth one line each in the report when seen: cold asset-bundle builds
(minutes on 9p; an HTTP test's default 10 s `url_open` timeout fails spuriously on a cold
`/shop`), readiness polls with no delay (hundreds of forwarded connections a minute through
an IDE port forwarder), and Windows `winnat`/`hns` ephemeral-port leaks starving outbound
connections (see `windows-wsl.md`).

## Report shape

Quote the measured lines, then one classification and one fix, e.g.:

```
Probes run:
  - PROBE read cost Windows (C:\work): 200 files: 6.12 ms/file -> SLOW
  - PROBE read cost /mnt (/mnt/c/work/addons): 200 files: 41.30 ms/file second pass -> SLOW
  - PROBE read cost ext4 (/usr/lib/python3/): 200 files: 0.08 ms/file -> baseline
  - PROBE confs with addons_path on /mnt: 9 of 9 -> every module file is read through 9p
Classification: performance / resource pressure (file I/O through 9p + on-access scanning)
Safe next action: mirror the read-only core on ext4 (fix ladder step 1); Defender exclusion request for IT drafted below.
```
