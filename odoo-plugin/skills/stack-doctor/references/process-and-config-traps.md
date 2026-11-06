# Odoo process and config traps (reference)

Detail for the `odoo-stack-doctor` skill's **Stack & DB lifecycle safety** section. Read it
when a local server behaves like old code, a restart or launch misbehaves, a config key
seems to do nothing, or an install fails for a reason the log does not make obvious.
Placeholders: `<port>`, `<config>`, `<db>`, `<logfile>`, `<venv>`, `<pid>`.

---

## 1. Processes and restarts

**Kill by the listening port, not by a name pattern.** A process whose command line differs
(other port args, a forked child, an earlier launch) survives a `pgrep -f`/`pkill -f`, keeps
the port, and the new server fails to bind but stays alive. Requests then hit the old
registry: `ValueError: Invalid field <model>.<field>` right after a clean `-u`.

```bash
ss -ltnp | grep ":<port> " | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u | xargs -r kill
ss -ltnp | grep ":<port> " || echo free     # must say free before you start
```

After starting, confirm the PID that owns the port is the one you launched before trusting
any result. The mirror case: a new server exits with "address in use" while the port answers
200, which means another session owns that port. Leave it alone.

**Restart the process after a `-u` that drops or renames a field.** A registry reload re-imports
no Python, so the running code still selects the dropped column and every request 500s.

**Name patterns match their own shell.** The Bash tool runs the whole script inside
`bash -c '<script>'`, so `pkill -f "<config>"`, a `pgrep`-based kill loop, or a liveness poll
on `pgrep -f <name>` matches its own command line (exit 144/15, or a poll that never ends).
Capture the PID at launch (`P=$!`) or resolve it from the port, and act on that PID only.

**Launch durably.** `nohup ... &` or `setsid` inside a `wsl -- ...` call dies when that WSL
session exits (0-byte log, no listener), and a harness background task dies when the client
restarts. On WSL/systemd, start long-lived servers as a user unit:
`systemd-run --user --unit=<name> --collect --working-directory=<dir> bash -c 'exec <cmd>'`.

**Readiness on a slow mount.** A cold boot over a network or 9p mount can take minutes before
the first request answers, so a short curl returns `000` and looks dead. Poll for a log marker
with the bounded loop from SKILL.md, and give it the real boot time as its budget.

**Proving a process is dead** before you kill or restart it: see "Long runs are background
jobs" in `skills/test/SKILL.md` (silence is not a hang).

## 2. Config keys and flags

**Dev mode is CLI-only.** `--dev=<modes>` works only on the command line; a `dev_mode =` key in
the conf is silently ignored. Proof it is on: with `reload` in the modes, the boot log warns
that `inotify` is not installed (Python autoreload needs the `inotify` pip package). Avoid
`--dev=all`: it enables post-mortem `pdb`, which hangs a headless server on the first unhandled
exception. Use `--dev=reload,qweb,xml` for template work. `--dev=xml` reads view arch from
disk, which also skips DB translations and the record-rule cache, so never validate
translations or record rules with it (see `skills/test/SKILL.md`).

**A server pinned to one database: set `db_name`, leave `dbfilter` empty.** With both set,
every request performs a database lookup, and with a low `db_maxconn` the first page fails
with "Connection Pool Is Full" or a login 500. Single-DB test confs: `db_name`, no
`dbfilter`, `db_maxconn` around 64.

**Attribute log lines before counting them.** Odoo appends to its logfile across restarts, so
an ERROR from a previous run reads as a failure of this one. Filter by the current PID
(the third field of each line) or by the start timestamp. A `DeprecationWarning` stack logged
at WARNING is not a crash.

```bash
grep -E "^[0-9-]{10} [0-9:,]+ <pid> (ERROR|CRITICAL) " <logfile> | wc -l
```

## 3. addons_path

**One entry per repository root.** An entry that holds no manifests directly (a parent of
several repos, or a repo whose modules sit one level deeper) is skipped with only a warning,
and every module under it is "not installable". Boot once and read which roots were accepted:

```bash
grep -iE "addons paths|invalid addons directory" <logfile>
```

Order and the "installed but missing from the path" case are in SKILL.md.

## 4. Installs

**One missing Python `external_dependencies` package aborts the whole `-i`.** Every module in
the command rolls back, not just the one that needed the package. Before a multi-module
install, collect the dependency closure, grep every manifest in it for
`external_dependencies`, and `pip install --dry-run` the union. Odoo pins several libraries
(for example `cryptography`, `urllib3`), so re-check the pinned requirements after adding any.
(Manifest-key semantics: `skills/reviewer/references/module_manifest.md`.)

**A fresh install leaves the new module's security groups empty.** Admin then gets AccessError
on every custom model. That is correct behaviour, not a broken install. Grant the groups as a
documented local step; do not change the module to "fix" it.

## 5. Fast local loop over a slow mount

When the Odoo core sits on a slow mount (a Windows drive seen from WSL, a network share), boot
and asset builds dominate every run. Keep a native-disk mirror of the core checked out at the
exact same commit (verify `HEAD` matches before each use, fall back to the original tree if
not), clone a neutralized template DB per task instead of installing fresh, and skip `-u` for
Python-only changes. The template-clone test loop itself is in `skills/test/SKILL.md`.
Generic disk and mount performance belongs to the `env-doctor` plugin.

## 6. Postgres discovery

Machines differ: probe instead of assuming which cluster serves which port.

```bash
pg_lsclusters                          # managed clusters (Debian/Ubuntu)
pg_isready -h 127.0.0.1 -p <pgport>
psql -h 127.0.0.1 -p <pgport> -Atc "SHOW data_directory"
```
