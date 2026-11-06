# Cleanup safety rules and why each exists

Each rule below is enforced by a script (`scripts/plan.py`, `apply_files.sh`,
`apply_dbs.sh`, `compact-wsl.ps1`) and is here so a reviewer can see what it protects
against. Do not relax a rule to make an apply "go through"; fix the plan instead.

| Rule | Enforced by | Incident / reason |
|---|---|---|
| Destructive steps never run from a quoted `bash -lc "..."` / `bash -c "$(cat x)"` string; scripts go by stdin (`bash -s`) or by path | skill protocol | 2026-09-29: from Git Bash, `wsl -- bash -lc "for d in a b; do dropdb \$d; rm -rf ~/.local/share/Odoo/\$d; done"` received `$d` EMPTY. `rm -rf /home/<u>/.local/share/Odoo/` wiped every filestore and session of 34 configs. The warning sign, `dropdb: missing database name`, was ignored. |
| `rm -rf -- "${p:?}"`; empty path refused; `set -euo pipefail` | apply_files.sh | same incident: an unset variable must stop the script, not widen the target |
| Allow-list of prefixes under `$HOME` (Odoo data dirs, `~/tmp`, pure package caches, `~/.config` for conf archives); a prefix root itself is refused (cache roots excepted) | apply_files.sh | a plan line can be wrong; the script is the last line of defence and must not be able to reach `$HOME`, `/` or a sibling project |
| Symlinks resolved (`realpath -m`) and re-checked against the allow-list | apply_files.sh | a link inside `~/tmp` pointing at a real project would otherwise be followed |
| A path that a live conf names as `data_dir` is refused | apply_files.sh (re-reads confs at apply time) | the plan may be hours old; a new lane may have started using a dir since |
| `..`, `/./` and glob characters refused | apply_files.sh | `rm -rf ~/tmp/*` style lines expand at the wrong moment |
| Dry run first; mode defaults to dry unless the word is exactly `run` | all apply scripts | read the expanded list before anything happens |
| Confs are moved to `_archive_<date>/` beside them, never deleted; only `*.conf` files | apply_files.sh | a "dead" conf is often the only record of how a lane was configured |
| `DROP DATABASE` without FORCE; skipped when a connection exists, re-checked right before the drop | apply_dbs.sh | another session's server or test run holds that connection; forcing kills its work |
| Database name passed as a psql variable (`:"name"`), names outside `[A-Za-z0-9_.-]` refused, system DBs refused | apply_dbs.sh | no SQL is built by string concatenation |
| `pg_dump -Fc` streamed through stdout into a dated backup dir, then the dump's TOC must hold one `TABLE DATA` entry per table, before the drop; filestore tarred beside it | apply_dbs.sh | the postgres OS user often cannot write into `$HOME`; a truncated dump must stop the drop (measured: 2 DBs of 24 GB → 2.3 GB of dumps) |
| Keep-list: open connections, canonical conf DBs and their `dbfilter`, running servers, activity < 7 days, tool state files, keep file | plan.py | a parallel QA track once dropped another session's deliverable DB and its baseline while that session sat paused ~80 min; a cleaner dropped a `tpl_*` template a fast-test script needed |
| Orphan detection off when any cluster could not be inventoried | plan.py | "no database of that name" is only true when every cluster was listed |
| Plan id = hash of the items; `emit` refuses another id, an edited plan, or a plan older than 24 h | plan.py | approval is for exactly what the user saw; state moves while a plan sits |
| An excluded database also excludes its filestore | plan.py emit | deleting the filestore of a kept DB loses its attachments and asset bundles |
| `odoo-local` items cannot override env-doctor's keep-list | plan.py merge | two planners, one set of rails |
| VHDX compaction: user-run, elevated, idle gate twice, no other `wsl.exe` clients, wait for `vmmem` to exit; diskpart readonly attach; never `--set-sparse` | compact-wsl.ps1 | another session's `wsl --shutdown` stopped a user's server, both PG clusters and two MCP processes; starting WSL mid-compaction aborts it; `--set-sparse` is gated behind `--allow-unsafe` on WSL 2.6.x over corruption reports |
| No passwordless root assumed | skill protocol | `wsl -u root` was authorised once, for one cleaning job; that is not a standing permission |
| Backups made by the cleaner are moved only with an OK and deleted only with an explicit OK | skill protocol | they are the undo |
| Derived caches are deleted only after proving the derivation (a clean clone of a source still on disk); trees with no history are kept | plan.py reports them for judgment | `~/.cache/rcptsync-src` (21k files, no git history) was the only copy |
| Synced trees: a delete propagates | skill protocol | Syncthing/OneDrive replicate deletions to every peer |
