# notification

Native desktop notifications when a Claude Code session needs you.

Start a long task, switch to something else, and let your desktop tell you when
Claude has a question, is waiting on a permission prompt, finished a task, ended
its turn, or hit an API error.

**Hooks only.** No skills, no agents, no MCP server, no model call, no transcript
parsing. Every character of every notification is a field the hook payload
already contained, so the plugin costs exactly zero tokens while it runs and
behaves identically every time.

---

## What you get

| Notification | Fires on | Class |
|---|---|---|
| ❓ **Claude Needs Your Answer** | Claude is about to ask a multiple-choice question | attention |
| 🔐 **Claude Needs Approval** | A permission prompt has waited ~6 s with no keystroke | attention |
| ❌ **Claude Failed** | The turn ended on an API error (rate limit, auth, overloaded, …) | attention |
| ✅ **Task Completed** | A single task was marked complete | informational |
| ✅ **Claude Finished** | Claude finished responding | informational |

**Attention** notifications stay on screen until dismissed where the OS allows
it, and play a sound. **Informational** ones are transient and silent.

Every notification carries an identity line — `project · a1b2c3` — so several
concurrent sessions stay distinguishable at a glance. The project name is the git
repository the session is working in (a worktree reads as itself), and the tag is
the first six characters of the session id.

```
❓ Claude Needs Your Answer          ❌ Claude Failed
KhairGate-BMS-19 · a1b2c3            claude_plugins · 7f2e91
Which migration strategy             rate_limit — API Error: Rate
should I use?                        limit reached
```

---

## Install

```
/plugin marketplace add taqat-techno/plugins
/plugin install notification@taqat-techno-plugins
```

Then restart Claude Code. There is nothing to configure and no setup step — the
hooks detect your platform on their own.

Verify with:

```
/notification:doctor
```

It prints your platform, the notification backend it resolved, the effective
configuration, and sends two test notifications.

**Requires** Python 3.8+ on `PATH` (the same requirement as most plugins in this
marketplace) and Claude Code **v2.1.202 or later**; v2.1.233+ is recommended.

---

## Platform support

| | Windows 10/11 | macOS | Linux desktop |
|---|---|---|---|
| Mechanism | WinRT toast via Windows PowerShell 5.1 | `osascript` | `notify-send` (libnotify) |
| Extra install | none | none | `libnotify-bin` if `notify-send` is missing |
| Attention notifications stay until dismissed | **yes** | see below | **yes** (GNOME, KDE) |
| Replace-in-place on bursts | yes | no | yes (GNOME, dunst) |

**Persistence: best available.** Windows uses the `reminder` toast scenario, and
GNOME and KDE honour the freedesktop rule that critical notifications should not
auto-expire. macOS has no programmatic equivalent — `display notification`
produces a banner, and whether it waits for you is a *user* setting.

### macOS one-time setup

Notifications route through Script Editor, and the command **fails silently** if
Script Editor lacks permission — macOS will not prompt you. Run this once:

```bash
osascript -e 'display notification "test"'
```

Nothing appears yet. Open **System Settings ▸ Notifications**, find **Script
Editor**, turn on **Allow Notifications**, and set its style to **Alerts** if you
want attention notifications to wait for you. Run the command again to confirm.

### Where notifications are skipped

WSL, SSH sessions, headless Linux (no `DISPLAY` or `WAYLAND_DISPLAY`), and any
machine without a notifier are detected and skipped **silently**. Every hook
still exits 0 and Claude behaves exactly as it would without the plugin.

WSL is detected deliberately rather than treated as Linux: WSL2 with WSLg has a
display but usually no notification daemon, so `notify-send` would appear to work
and quietly do nothing. A WSL-to-Windows-host adapter is planned.

---

## Task notifications need one opt-in on current models

Since Claude Code v2.1.233, the Task tools (`TaskCreate`, `TaskUpdate`,
`TaskList`, `TodoWrite`) are **not provided** on Opus 4.8, Sonnet 5, Fable 5,
Mythos 5 or later families unless you opt in. Without them the task list is never
populated, so the `TaskCompleted` event never fires and **✅ Task Completed will
never appear**.

To enable it, start Claude Code with:

```bash
CLAUDE_CODE_ENABLE_TODO_TOOLS=1 claude
```

`/notification:doctor` detects and reports this. On older families such as Opus
4.7 the Task tools are on by default and nothing is needed. Every other
notification works regardless of model.

---

## Configuration

Optional. With no config file, every category is enabled.

```
/notification:doctor --write-config
```

writes defaults to `${CLAUDE_PLUGIN_DATA}/config.json`
(`~/.claude/plugins/data/notification-taqat-techno-plugins/config.json`):

```json
{
  "enabled": true,
  "categories": {
    "question": true,
    "permission": true,
    "task": true,
    "turn": true,
    "failure": true
  },
  "sound": { "attention": true, "informational": false },
  "suppress_teammate_tasks": true
}
```

Turning off `turn` is the usual first edit — ✅ Claude Finished fires once per
assistant turn, the highest-volume notification the plugin sends.

Config never lives under the plugin's install directory, which is replaced on
every update.

---

## Why it cannot break your session

This plugin observes the same lifecycle events that can *control* Claude, so its
safety properties are structural rather than aspirational:

- **Every hook is `async: true`.** Async hooks cannot block or control Claude.
  That matters because exit code 2 on `PreToolUse` would suppress Claude's
  question, on `Stop` would trap Claude in a non-terminating turn, and on
  `TaskCompleted` would refuse the completion. Async removes the capability
  entirely.
- **The notifier writes nothing to stdout,** so there is no output for Claude
  Code to parse and nothing that can be malformed.
- **No shell, anywhere.** Hooks use exec form; backends run argument vectors with
  `shell=False`; on Windows the text travels in environment variables. Notification
  text is untrusted data and is never executable content.
- **Nothing runs at session start.** The plugin registers no `SessionStart` hook,
  so installing it cannot slow or disturb a session.
- **Every failure is silent.** No notifier, no desktop, no Python — the hook
  exits 0 and Claude continues untouched.

Full rationale, including what would justify reversing each rule, is in
[`docs/decisions.md`](docs/decisions.md).

---

## Hooks registered

| Event | Matcher | Category |
|---|---|---|
| `PreToolUse` | `AskUserQuestion` | question |
| `Notification` | `permission_prompt` | permission |
| `TaskCompleted` | — | task |
| `Stop` | — | turn |
| `StopFailure` | — | failure |

Five registrations, one script, all async, each with a 10-second timeout.

`PermissionRequest` is deliberately **not** registered: it fires on every
permission ask rather than only when you have stepped away, and a hook on that
event can allow or deny permissions on your behalf. An observability plugin has
no business on the permission decision path.

---

## Troubleshooting

**Nothing appears at all.** Run `/notification:doctor`. If the backend reports
`unsupported`, the report names the reason. If it reports a real backend but the
test notifications did not appear, check your OS notification settings — Focus
Assist on Windows, Do Not Disturb on macOS, or the Script Editor permission above.

**Notifications appear but ✅ Task Completed never does.** See the opt-in section
above.

**Too many ✅ Claude Finished notifications.** Set `"turn": false` in
`config.json`.

**Nothing changed after editing the plugin.** Claude Code runs plugins from
`~/.claude/plugins/cache/`, and hooks are loaded at session start. Run
`/reload-plugins` or restart the session.

---

## Tests

```bash
python notification-plugin/tests/test_notification.py
```

43 stdlib-only tests, no desktop required. They cover the isolation contract
(silent stdout, always exit 0, survives garbage input), text safety (shell
metacharacters, ANSI escapes, non-ASCII, clipping), rendering per category,
identity derivation, every suppression rule, and structural assertions on
`hooks.json` itself — including that every hook is async and that no
`SessionStart` hook exists.

---

## License

MIT — see [LICENSE](LICENSE).
