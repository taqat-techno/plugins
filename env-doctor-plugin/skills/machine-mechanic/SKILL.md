---
name: machine-mechanic
description: >-
  Use when an "[env-doctor mechanic]" note arrives (a system reminder or prompt context about
  memory, CPU, disk or WSL pressure while a local service runs), or when the user asks to turn
  the background machine watcher on or off, tune its thresholds, or see what it measured. Says
  which findings the agent may fix itself and which it must take to the user.
version: 0.1.0
user-invocable: false
metadata:
  last_reviewed: 2026-11-13
  owns:
    - the authority policy for mechanic findings (what the agent may fix, what it must ask about)
    - how to answer a finding without stopping the user's task
  defers_to:
    - data/mechanic_rules.json (thresholds, wording, each rule's authority)
    - hooks/mechanic.py (sampler, daemon, state files) and hooks/mechanic_hook.py (delivery)
    - dev-env-cleanup (anything that deletes) and long-running-jobs (heavy jobs in the background)
---

# Machine mechanic

You are the driver: you run the user's task and the local services it needs. The mechanic is a
small background watcher that env-doctor starts when you start a local service (Odoo,
`manage.py runserver`, `npm run dev`, `docker compose up`, uvicorn, gunicorn, `systemd-run`, or
the odoo-local start, restart and relaunch tools). It samples memory, CPU, free disk and WSL
every ~45 seconds at below-normal priority and never changes anything. When a rule in
`data/mechanic_rules.json` holds, it hands you one note that starts with `[env-doctor mechanic]`.

## When a note arrives

1. **Finish the step you are on** unless the note says the disk is critical. A note is not an
   emergency stop.
2. **Read the authority at the end of each finding** and follow it exactly:

| Authority line | What you may do yourself | What needs the user |
|---|---|---|
| "You may fix this yourself, limited to services and jobs you started" | Stop or restart a service, test run, watcher or build **you started in this session** that is idle, stuck or duplicated. Rerun your own job with fewer workers or a lower memory limit. Move your own heavy job to the background (see `long-running-jobs`). | Stopping or changing anything you did not start: other sessions' services, the user's programs, other databases. |
| "Tell the user and ask before acting" | Gather facts read-only, or build a plan that changes nothing (`/env-doctor:clean` without `--apply`). | Every change: `wsl --shutdown`, editing `.wslconfig`, dropping databases, deleting files, compacting the WSL disk. |

3. **Tell the user in one or two lines** what the mechanic saw and what you did or propose, in
   plain words. Put a change that needs their OK as one question.
4. **Carry on with the task.** Do not wait, poll or re-measure in a loop; the mechanic tells you
   again if the problem comes back after its cooldown.

Never treat a note as permission for a destructive step. Deleting anything goes through
`dev-env-cleanup` and its plan id, whatever the note says.

## What it measures

| Metric | Meaning |
|---|---|
| `mem_used_pct`, `mem_avail_gib`, `mem_total_gib` | physical memory in use (Windows `GlobalMemoryStatusEx`, Linux `/proc/meminfo`) |
| `cpu_pct` | whole-machine CPU busy since the previous sample |
| `disk_free_gib` | free space on the system drive |
| `wsl_mem_gib`, `wsl_mem_pct` | working set of the WSL VM (`vmmemWSL`), every 4th sample |
| `wsl_reclaim` | the `autoMemoryReclaim` value in `%USERPROFILE%\.wslconfig`, or "not set" |
| `vhdx_slack_gib` | how much bigger the WSL disk image is than what the distro uses; hourly, only while WSL already runs |

The last sample is in `<state>/metrics.json` and every finding in `<state>/findings.jsonl`, where
`<state>` is `$CLAUDE_PLUGIN_DATA/mechanic` (or `~/.claude/env-doctor/mechanic`). Read them when the
user asks what it saw.

## Turning it off or tuning it

- Off: the `mechanic` plugin option, or `ENV_DOCTOR_MECHANIC=off` in the environment. The watcher
  exits at its next sample.
- Thresholds, wording and authority: edit `data/mechanic_rules.json` in the plugin; there is no
  second copy anywhere.
- It stops by itself 30 minutes after the last activity of every session that started a service,
  and after 12 hours at most. Only one watcher runs per machine, however many sessions are open.
- Sessions that never started a service never get notes.

## How a note reaches you

A background `PostToolUse` hook (`asyncRewake`) waits for a new finding and wakes you with it.
If none was listening, for example while you were idle, the `UserPromptSubmit` hook adds it to the
user's next message instead. Each finding reaches each session once.
