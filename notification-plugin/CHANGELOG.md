# Changelog

All notable changes to the notification plugin are documented here.
This project follows [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-08-21

First release. Replaces the retired `ntfy-notifications` plugin, which pushed to
the external ntfy.sh service; this one uses each operating system's own notifier
and requires no account, no network, and no third-party service.

### Added

- Five async hook registrations, all routed to one stdlib-only Python entry point:
  - `PreToolUse` matcher `AskUserQuestion` - "Claude Needs Your Answer"
  - `Notification` matcher `permission_prompt` - "Claude Needs Approval"
  - `TaskCompleted` - "Task Completed", carrying `task_subject`
  - `Stop` - "Claude Finished"
  - `StopFailure` - "Claude Failed", carrying the API error type and message
- Native backends for Windows (WinRT toast via Windows PowerShell 5.1), macOS
  (`osascript`) and Linux (`notify-send`).
- Two intrusiveness classes: attention notifications are sticky where the OS
  allows it and play a sound; informational ones are transient and silent.
- Identity line on every notification - `project - sessiontag` - so concurrent
  sessions stay distinguishable. Project name comes from the git root, so a
  worktree reads as its own workspace.
- Replace-in-place on bursts: toast tag/group on Windows, server-side hints on
  Linux, so five task completions update one notification instead of stacking.
- Deterministic suppression rules: subagent events, teammate tasks, turns with
  background tasks or scheduled wakeups still in flight, and stop-hook-driven
  continuations.
- Safe-skip capability detection for WSL, SSH, headless Linux, and hosts with no
  notifier installed.
- Optional configuration at `${CLAUDE_PLUGIN_DATA}/config.json`; absent means all
  categories enabled.
- `/notification:doctor` - reports platform, backend, config and task-tool
  availability, and sends test notifications. Runs with no arguments.
- `docs/decisions.md` - eleven binding architecture decisions (D-001..D-011),
  each with non-violation checks and reverse-only criteria.
- `tests/test_notification.py` - 43 stdlib-only contract tests, including
  structural assertions that every hook is async and that no SessionStart hook
  exists.

### Notes

- `TaskCompleted` does not fire on Opus 4.8, Sonnet 5, Fable 5, Mythos 5 or later
  families unless Claude Code is started with `CLAUDE_CODE_ENABLE_TODO_TOOLS=1`.
  Since Claude Code v2.1.233 those models are not given the Task tools, so the
  task list is never populated. The doctor command detects and reports this.
- `PermissionRequest` is deliberately not registered: it fires on every permission
  ask rather than only when the user has stepped away, and a hook on that event
  can allow or deny permissions on the user's behalf.
- `terminalSequence` is deliberately not used: it would require converting every
  hook to synchronous, giving up the non-blocking guarantee. See D-009.
- Hard-crash detection is out of scope for v1. See D-010.
- Requires Claude Code v2.1.202 or later; v2.1.233+ recommended.
