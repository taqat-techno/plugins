# Changelog

All notable changes to the notification plugin are documented here.
This project follows [Semantic Versioning](https://semver.org/).

## [1.1.0] - 2026-09-13

### Fixed

- **One notification per question.** Claude Code presents `AskUserQuestion`
  through its permission-prompt path, so every question also raised a generic
  `permission_prompt` a few seconds later and two notifications appeared. The
  question hook now leaves a short-lived per-session marker under
  `${CLAUDE_PLUGIN_DATA}/state/`, the permission notification is suppressed while
  it stands, and a new `PostToolUse` hook on `AskUserQuestion`, `Stop`, `StopFailure` and
  your next prompt clear it. It also expires on its own after 120 seconds. Every
  failure fails toward notifying. See D-013.
- **Non-ASCII text on Windows.** Python decodes a piped stdin with the ANSI code
  page on Windows, so questions containing Arabic, emoji or box-drawing
  characters arrived as mojibake or were silently dropped. The payload is now
  read as raw bytes and decoded as UTF-8.

### Changed

- **Cleaner layout.** The title names the project and what happened
  (`❓ claude_plugins needs your answer`), the body carries the content, and the
  attribution line is `session 2ecaaa`.
- **Readable content.** Markdown is stripped from Claude's final message, the
  generic "Claude needs your permission" is replaced with where to act, API error
  codes are humanised (`rate_limit` becomes "Rate limit reached") without
  repeating the detail, a prompt with several questions shows `(+N more)`, and
  long text is clipped at a word boundary.
- **Windows: "Claude Code" instead of "Windows PowerShell".** Toasts appear under a
  per-user app identity, with the plugin icon in the header and their own entry in Settings >
  Notifications, registered under HKCU on first use - no admin, and a fallback to
  PowerShell's identity on any failure. See D-014.
- **Waiting-for-you notifications stay until you close them.** Questions,
  approvals, errors and "is done" stay on screen until closed - on Windows with a
  Close button, which Windows requires for this (a menu-only action was tested
  and does not keep the toast up); on Linux via critical urgency. Task completions stay transient. Per-category `persistent` option.
  See D-015.
- **Notifications never replace each other.** Every toast gets its own id, so a
  new question or "is done" stacks instead of overwriting the previous one. The
  1.0 replace-in-place behaviour is gone on Windows and Linux.
- **Stale notifications are withdrawn only when you act (Windows).** Answering a
  question removes its toast, and your next prompt removes that session's
  waiting toasts, through a new async `UserPromptSubmit` hook. A new
  notification never removes an older one.
- `/notification:doctor` reports the real plugin version and the
  `persistent` setting.
- Tests: 43 to 79, including the captured live `permission_prompt` payload, a
  cp1252 stdin reproduction, and a PowerShell parse check of the toast script.

## [1.0.1] - 2026-09-12

Records decision D-012: this plugin ships no eval suite. It has no `skills/`
and no `agents/`, so there is no routing surface for `claude plugin eval` to
measure and every case would report `Delta = 0` by construction. This is the
N/A path of the marketplace's behavioural-verification rule. Hook behaviour
remains covered by `tests/test_notification.py`. No runtime behaviour changed.

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
