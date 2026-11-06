---
name: long-running-jobs
description: >-
  Use when about to run a test suite, build, module install or upgrade, migration, database
  dump or restore, or any command that may take more than about 3 minutes, when a command
  needs a long timeout, or when tempted to wait, sleep or poll for a job to finish. Jobs over
  ~3 minutes run in the background and the session keeps working; covers estimating the
  duration, durable launches inside WSL, waiting without polling, reading the real exit code,
  and capping concurrency.
version: 0.1.0
user-invocable: false
metadata:
  last_reviewed: 2026-11-06
  owns:
    - the 3-minute rule (foreground only when expected to finish within ~3 minutes)
    - durable background launch patterns (harness background, systemd-run inside WSL)
    - non-polling waits, liveness and exit-code rules for long jobs
    - concurrency limits and CPU/memory caps for parallel heavy jobs
  defers_to:
    - the hooks/long_job_advisory.py PreToolUse hook (spots long-job shapes; advisory, never blocks)
    - stack-specific plugins for their own fast test tiers (for example the odoo plugin's test skill)
    - env-doctor-router references/windows-wsl.md for WSL VM lifecycle and the restart protocol
---

# long-running-jobs

## Purpose

Agents have spent whole sessions inside one blocking call: 350 of 527 recorded Odoo test
runs were started in the foreground with 10-60 minute timeouts, while the user waited and
nothing else moved. Full suites there take 20-43 minutes. A long job is not a reason to
stop working. This skill makes the rule concrete and gives the patterns that keep a
background job durable and its result trustworthy.

## The rule

| Expected duration | Do this |
|---|---|
| ≤ 3 minutes | May run in the foreground and block. Set `timeout` explicitly (≤ 180000 ms is the signal that you expect it short). |
| > 3 minutes (5, 10, 30 min, unknown) | Start it in the **background**, **continue with the next task**, and act when the completion notification arrives: on failure, read the log and fix; on success, confirm and move on. It is not a blocker. |

- **Never** `sleep` or poll in a loop waiting for it. The harness notifies you when a
  `run_in_background` command exits; do not read its output file to "check on it".
- **Never** kill a healthy long run because a tool timeout is near: background it instead.
- **Never** hold a report, a hand-off or a delivery hostage to a long run you could finish
  around. "Long testing is never a blocker" — say what is running and carry on.
- While developing, prefer a **small targeted test** that finishes in under 3 minutes over
  re-running a long suite. Run the long suite once at the end, in the background.

## Estimating the duration

1. The last recorded duration of the same command, if known. Record it: after a long job,
   note `<date> <command shape> <minutes>` in the project's task notes (for example
   `.claude/tasks/todo.md`) so the next estimate is a number, not a guess.
2. Otherwise assume **long** for: full or module-wide test suites, `-i`/`-u` on a fresh or
   large database, `npm run test:e2e` / full Playwright runs, `pg_dump`/`pg_restore` of anything
   non-trivial, cold asset builds, first runs on a slow file system (`/mnt/c` in WSL).
3. Short: a single test method on a warm database, a lint of changed files, a unit test file.

The PreToolUse hook (`hooks/long_job_advisory.py`) recognises the common long shapes
(`--test-enable` / `--test-tags` wider than one method, `-i`/`-u … --stop-after-init`,
`pytest` on a whole tree, `manage.py test` with no label, `test:e2e`, `playwright test` with no
spec, `pg_dump`/`pg_restore`) and adds a reminder when such a call would sit in the foreground
(no `run_in_background`, and a timeout above 180000 ms or none at all — the 2-minute default
would kill it). It never blocks. Silence it with `ENV_DOCTOR_LONG_JOBS=off` or the
`long_job_advice` plugin option.

## Launching so it survives

| Where | Use | Not |
|---|---|---|
| Claude Code harness | `run_in_background: true` on the Bash/PowerShell call | a foreground call with a 30-minute timeout |
| Inside WSL, called from Windows | `systemd-run --user --unit=<name> --collect <script>` (add `--working-directory=<dir>`; returns at once; the unit keeps running) | `nohup … &` or `setsid` inside `wsl -- …`: they die when that `wsl.exe` call exits (0-byte log, no process) |
| Survive a Claude Code restart | a systemd user unit (WSL/Linux) or a Windows-side `Start-Process wsl.exe …` | the harness background task, which dies with the session |
| Cap its impact on a live server | `systemd-run --user --scope -p CPUQuota=300% -p MemoryMax=6G nice -n 19 <cmd>` | uncapped parallel heavy jobs (disk I/O cannot be capped in WSL: schedule restores off-hours) |

Write the job as a script file (LF endings) and run it by path or on stdin; do not pass a
multi-line job through `bash -lc "…"` quoting from Git Bash or PowerShell.

## Waiting without polling

- Harness background job: wait for the completion notification. Nothing else.
- systemd unit or a process you did not start in the harness: use `Monitor` with an
  until-condition on **its PID** (`kill -0 <pid>`) or on **a marker line in its log** — or start
  a small background command that waits for that condition and exits, and take its
  notification.
- **Never** wait on `pgrep -f <name>` / `pkill -f`: the pattern matches the probing shell's own
  command line (the Bash tool wraps your script in `bash -c '<script>'`), so it never reports
  "gone" (a poll that ran forever after a suite had finished) or it kills its own shell
  (exit 144). Capture the PID when you start it (`P=$!`, or the unit name) and use that.
- **Silence is not a hang.** Asset generation and registry loads log nothing for minutes.
  Positive liveness signals: the PID is alive and its database shows recent
  `pg_stat_activity.state_change`. Prove death (no PID, no DB activity) before declaring it
  stuck; a healthy 27-minute run was once killed on two broken liveness probes.

## Reading the result correctly

- The notification reports the **wrapper's** exit code. `cmd; echo done` exits 0 whatever
  `cmd` did. End the script with the job's own status (`cmd; rc=$?; …; exit $rc`) or write
  `rc` to a result file and read it.
- Odoo appends to its log across runs: attribute errors by PID and timestamp, not by grep alone.
- Exit 137 on a test run is usually another session's `pkill -9`, not OOM. Exit 143 is a
  timeout or a TERM. Check before adding retries.

## Concurrency

- At most **one heavy background job per project database**, and at most **two heavy test
  processes** on the machine: eight Odoo test processes on 4 cores / 11 GB made each run 2-4×
  slower. Count before starting one (`ps -eo args | grep -c '[o]doo-bin.*--test-enable'`).
- Never two servers on one database; never start a job that stops or restarts a service
  another session is using.
- Leave nothing behind: stop the servers you started for a test when it ends (by PID or unit,
  never `pkill -f`). Agents have left six test servers running for 11-18 hours.

## Anti-patterns

| Anti-pattern | Correct |
|---|---|
| Foreground `pytest` / full suite with `timeout: 1800000`, then "still running…" turns | `run_in_background: true`, next task, handle the notification |
| `while ! grep -q done log; do sleep 30; done` in the foreground | Monitor until-condition on the log marker, or the harness notification |
| `nohup ./run_tests.sh &` inside `wsl -- bash -lc "…"` | `systemd-run --user --unit=tests-<x> --collect ./run_tests.sh` |
| `pgrep -f odoo-bin` to see if the run is alive | the captured PID or unit (`systemctl --user is-active tests-<x>`) |
| Killing a quiet run after 10 minutes of no log output | prove death first: PID and database activity |
| Re-running the 30-minute suite after each small edit | one targeted test per edit, the suite once at the end |
