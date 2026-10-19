# notification

## What it does

Native desktop notifications when a Claude Code session needs you. Start a long
task, switch to something else, and your desktop tells you when Claude has a
question, is waiting on a permission prompt, finished a task, ended its turn, or
hit an API error.

**Hooks only.** No skills, no agents, no MCP server, no model call, no
transcript parsing. Every character of every notification is a field the hook
payload already contained, so the plugin costs zero tokens while it runs.

For anyone who runs Claude Code on a desktop and steps away while it works.

| Notification | Fires on | Class |
|---|---|---|
| ❓ **‹project› needs your answer** | Claude asks a multiple-choice question; exactly one notification per question | attention |
| 🔐 **‹project› needs your approval** | A permission prompt has waited ~6 s with no keystroke | attention |
| ❌ **‹project› hit an error** | The turn ended on an API error (rate limit, auth, overloaded, …) | attention |
| ☑️ **‹project› finished a task** | A task was marked complete | informational |
| ✅ **‹project› is done** | Claude finished responding | informational |

Everything that means Claude is waiting for you (a question, an approval, an
error, a finished turn) **stays on screen until you close it**, and is withdrawn
on Windows once you answer or type your next prompt. New notifications never
replace older ones. Task completions are transient. Questions, approvals and
errors play a sound; the rest are silent.

```
❓ acme-erp needs your answer             ✅ my-app is done
Which migration strategy should I use?   Fixed the duplicate notification.
session a1b2c3                           session 7f2e91
```

Each notification names what happened and the project (the git repository the
session works in; a worktree reads as itself), the content, and the first six
characters of the session id. Markdown is stripped, API error codes become plain
words, and several questions show `(+2 more)`.

## Install

```
/plugin marketplace add taqat-techno/plugins
/plugin install notification@taqat-techno-plugins
```

Restart Claude Code (hooks load at session start), then verify with
`/notification:doctor`.

## Requirements

| Requirement | Check |
|---|---|
| Claude Code v2.1.202 or later (v2.1.233+ recommended) | `claude --version` |
| Python 3.8+ reachable as `python3`, `python` or `py -3` | `/notification:doctor`, section "Hook interpreters" |
| Windows: Windows PowerShell 5.1 (built in) | `powershell -Command $PSVersionTable.PSVersion` |
| macOS: `osascript` (built in) plus the Script Editor permission below | `osascript -e 'display notification "test"'` |
| Linux: `notify-send` (libnotify) and a notification daemon | `command -v notify-send` |

The hooks try all three interpreter names, so a host with only `python3`
(default macOS, Debian, Ubuntu) and a Windows host with only `python` or `py`
both work.

## Commands

| Command | Description |
|---|---|
| `/notification:doctor [--no-test] [--json] [--write-config] [--uninstall-windows-identity]` | Platform, resolved backend, the interpreters the hooks will use and the one that handled the last event, effective configuration, task-tool availability; sends two test notifications unless `--no-test` |

## Skills

None.

## Agents

None.

## Hooks

Seven events, each registered three times (`python3`, `python`, `py -3`), all in
exec form, all `async: true` with a 10-second timeout, all routed to
`hooks/notify.py`. **None can block**: async hooks cannot block or control
Claude, the script writes nothing to stdout and always exits 0.

| Event | Matcher | Does |
|---|---|---|
| `PreToolUse` | `AskUserQuestion` | question notification |
| `PostToolUse` | `AskUserQuestion` | closes the question; never notifies |
| `UserPromptSubmit` | — | withdraws this session's waiting toasts (Windows); never notifies |
| `Notification` | `permission_prompt` | approval notification (suppressed while a question is open) |
| `TaskCompleted` | — | task notification |
| `Stop` | — | "is done" notification |
| `StopFailure` | — | error notification |

Why three registrations: exec form has no shell to fall back between names
(D-003), and no single name exists everywhere. A missing name never starts; the
first process that starts claims the event under `${CLAUDE_PLUGIN_DATA}/state/`
and the others exit, so you get one notification (D-016).

`PermissionRequest` is deliberately not registered: a hook there can allow or
deny permissions on your behalf. There is no `SessionStart` hook.

## Configuration

**userConfig** (set in `/plugin` for this plugin):

| Option | Type | Default | Effect |
|---|---|---|---|
| `title_only` | boolean | `false` | Show only what happened and in which project, never the question, Claude's message or the error text. Hooks receive it as `CLAUDE_PLUGIN_OPTION_TITLE_ONLY`. |

**config.json** (optional, `${CLAUDE_PLUGIN_DATA}/config.json`; write the
defaults with `/notification:doctor --write-config`):

```json
{
  "enabled": true,
  "categories": { "question": true, "permission": true, "task": true, "turn": true, "failure": true },
  "sound": { "attention": true, "informational": false },
  "suppress_teammate_tasks": true,
  "title_only": false,
  "persistent": { "question": true, "permission": true, "failure": true, "turn": true, "task": false }
}
```

- `title_only` here and the userConfig option combine: either can turn it on.
- Turning off `categories.turn` is the usual first edit; ✅ *is done* fires once
  per assistant turn.
- `persistent` chooses which notifications stay until closed.

**Environment:** `CLAUDE_CODE_ENABLE_TODO_TOOLS=1` (a Claude Code setting, not
this plugin's) is needed for task notifications on current models: since Claude
Code v2.1.233 the Task tools are not provided on Opus 4.8, Sonnet 5, Fable 5,
Mythos 5 or later families unless you opt in, so `TaskCompleted` never fires.
The doctor reports this.

No per-project files.

## Platform support

| | Windows 10/11 | macOS | Linux desktop | WSL | SSH / headless |
|---|---|---|---|---|---|
| Mechanism | WinRT toast via Windows PowerShell 5.1 | `osascript` | `notify-send` | skipped | skipped |
| Stays until closed | yes (Close button) | user setting (Alerts style) | yes (GNOME, KDE: critical urgency) | — | — |
| Withdraws stale toasts | yes | no | no | — | — |

**macOS one-time setup.** Notifications route through Script Editor and fail
silently without permission. Run `osascript -e 'display notification "test"'`
once, then System Settings ▸ Notifications ▸ Script Editor ▸ Allow
Notifications (style Alerts if you want them to wait).

**Skipped hosts.** WSL, SSH sessions, headless Linux and machines without a
notifier are detected and skipped silently; every hook still exits 0. WSL is
not treated as Linux because WSLg usually has no notification daemon
(`notify-send` would appear to work and do nothing). A WSL-to-Windows bridge is
not implemented.

## Data & privacy

- **What appears on screen.** By default the body shows up to 180 characters of
  the question, the permission message, the task subject, Claude's final message
  or the API error. That text can contain file contents, customer data or
  anything Claude echoed. It appears in the OS notification centre, on the lock
  screen and in screen shares or recordings, and waiting-for-you notifications
  stay until closed. Token-, key- and password-shaped strings are masked as
  `[REDACTED]`, but masking is shape-based and cannot catch everything. Turn on
  **`title_only`** on shared, recorded or presented screens.
- **What is stored.** Only under `${CLAUDE_PLUGIN_DATA}`: optional
  `config.json`, short-lived `state/question-*` and `state/claim-*` markers
  (swept automatically), and `state/last-hook-run.json` (interpreter path,
  Python version, last verb, time). No notification text is written to disk.
- **What leaves the machine.** Nothing. No network, no third-party service.
- **Windows registry.** The first toast registers the app identity
  `HKCU\Software\Classes\AppUserModelId\TaqaTechno.ClaudeCode.Notifications`
  (`DisplayName` "Claude Code", `ShowInSettings`, and `IconUri` pointing at
  `hooks/icon.png` inside the plugin's install directory). No admin rights, no
  HKLM. Uninstalling the plugin does **not** remove it; run
  `/notification:doctor --uninstall-windows-identity` first. After an update the
  old version directory may be gone, so `IconUri` is stale until the next toast
  re-points it, and Windows may keep showing its cached icon until you sign out.

## Limitations

- macOS has no programmatic persistence or withdrawal.
- WSL is not supported (detected and skipped).
- On hosts where two or three interpreter names resolve, up to three short
  processes start per event; one notifies. If `${CLAUDE_PLUGIN_DATA}` is
  unwritable, a duplicate notification is possible.
- Task notifications need `CLAUDE_CODE_ENABLE_TODO_TOOLS=1` on current models.
- Editing the plugin source has no effect until `/reload-plugins` or a restart:
  Claude Code runs plugins from `~/.claude/plugins/cache/`.

Troubleshooting starts with `/notification:doctor`: it names the reason when
the backend is `unsupported`, warns when no interpreter is usable, and shows
which interpreter handled the last event. Design rationale is in
[`docs/decisions.md`](docs/decisions.md).

Tests: `python -m pytest -q -p no:cacheprovider` from this directory (110
stdlib-only tests, no desktop required).

## License

MIT, see [LICENSE](LICENSE). No third-party components are bundled.
