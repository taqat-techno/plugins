# Notification Plugin

**Package:** `notification` · **Version:** `1.0.0` · **Category:** productivity · **License:** MIT · **Source:** [`notification-plugin/`](../../notification-plugin/)

## Purpose

Send a **native desktop notification** whenever a Claude Code session needs you — a question is waiting, a permission prompt has gone unanswered, a task finished, the turn ended, or the API failed.

It replaces the retired `ntfy-notifications` plugin, which pushed to the external [ntfy.sh](https://ntfy.sh) service. This one uses each operating system's own notifier: no account, no network, no third party.

## What it does

| Notification | Fires on | Class |
|---|---|---|
| ❓ **Claude Needs Your Answer** | Claude is about to ask a multiple-choice question | attention |
| 🔐 **Claude Needs Approval** | A permission prompt has waited ~6 s with no keystroke | attention |
| ❌ **Claude Failed** | The turn ended on an API error | attention |
| ✅ **Task Completed** | A single task was marked complete | informational |
| ✅ **Claude Finished** | Claude finished responding | informational |

**Attention** notifications stay on screen until dismissed where the OS allows it, and play a sound. **Informational** ones are transient and silent.

Every notification carries an identity line — `project · a1b2c3` — so several concurrent sessions stay distinguishable. The project name is the git repository the session is working in (a worktree reads as its own workspace), and the tag is the first six characters of the session id.

```
❓ Claude Needs Your Answer          ❌ Claude Failed
KhairGate-BMS-19 · a1b2c3            claude_plugins · 7f2e91
Which migration strategy             rate_limit — API Error: Rate
should I use?                        limit reached
```

## How it works

**Hooks only.** No skills, no agents, no MCP server, no model call, no transcript parsing. Every character of every notification is a field the hook payload already carried, so the plugin costs exactly zero tokens while it runs and behaves identically every time.

```
Claude Code lifecycle event
      │  JSON on stdin (never on a command line)
      ▼
hooks.json — async: true, exec form, timeout 10
      │  Claude Code does NOT wait; it has already continued
      ▼
hooks/notify.py — filter → render → sanitise → backend → exit 0
      ▼
Windows: PowerShell 5.1 + WinRT toast   (payload via environment)
macOS:   osascript `on run argv`        (payload via argv)
Linux:   notify-send                    (payload via argv)
```

### Hooks registered

| Event | Matcher | Category |
|---|---|---|
| `PreToolUse` | `AskUserQuestion` | question |
| `Notification` | `permission_prompt` | permission |
| `TaskCompleted` | — | task |
| `Stop` | — | turn |
| `StopFailure` | — | failure |

`PermissionRequest` is deliberately **not** registered: it fires on every permission ask rather than only when you have stepped away, and a hook on that event can allow or deny permissions on your behalf. An observability plugin has no business on the permission decision path.

## Command

**`/notification:doctor`** — runs with no arguments. Reports platform, resolved backend, effective configuration, and task-tool availability, then sends two test notifications.

| Flag | Effect |
|---|---|
| `--no-test` | Report only |
| `--json` | Raw capability report as JSON |
| `--write-config` | Write a default `config.json` and print its path |

## Platform support

| | Windows 10/11 | macOS | Linux desktop |
|---|---|---|---|
| Mechanism | WinRT toast via Windows PowerShell 5.1 | `osascript` | `notify-send` (libnotify) |
| Extra install | none | none | `libnotify-bin` if missing |
| Attention notifications stay until dismissed | **yes** (`scenario="reminder"`) | user setting only | **yes** (`-u critical`, GNOME/KDE) |
| Replace-in-place on bursts | yes (toast tag/group) | no | yes (server-side hints) |

**Persistence: best available.** macOS has no programmatic equivalent — `display notification` produces a banner, and whether it waits for you is a *user* setting.

### macOS one-time setup

Notifications route through Script Editor and **fail silently** if it lacks permission; macOS will not prompt you. Run once:

```bash
osascript -e 'display notification "test"'
```

Nothing appears yet. Open **System Settings ▸ Notifications**, find **Script Editor**, turn on **Allow Notifications**, and set its style to **Alerts** if you want attention notifications to wait for you.

### Where notifications are skipped

WSL, SSH sessions, headless Linux (no `DISPLAY` / `WAYLAND_DISPLAY`), and machines with no notifier are detected and skipped **silently**. Every hook still exits 0 and Claude behaves exactly as it would without the plugin.

WSL is detected deliberately rather than treated as Linux: WSL2 with WSLg has a display but usually no notification daemon, so `notify-send` would appear to work and quietly do nothing.

## Configuration

Optional. With no config file, every category is enabled. `/notification:doctor --write-config` writes defaults to `${CLAUDE_PLUGIN_DATA}/config.json`:

```json
{
  "enabled": true,
  "categories": {
    "question": true, "permission": true,
    "task": true, "turn": true, "failure": true
  },
  "sound": { "attention": true, "informational": false },
  "suppress_teammate_tasks": true
}
```

Turning off `turn` is the usual first edit — ✅ Claude Finished fires once per assistant turn.

Config never lives under the plugin's install directory, which is replaced on every update.

## Dependencies

- **Python 3.8+** on `PATH` (stdlib only — no packages)
- **Claude Code v2.1.202 or later**; v2.1.233+ recommended

## Known limitations

- **Task notifications need an opt-in on current models.** Since Claude Code v2.1.233 the Task tools are not provided on Opus 4.8, Sonnet 5, Fable 5, Mythos 5 or later families unless you opt in. Without them the task list is never populated, so `TaskCompleted` never fires and ✅ Task Completed never appears. Start Claude Code with `CLAUDE_CODE_ENABLE_TODO_TOOLS=1` to enable it. `/notification:doctor` detects and reports this.
- **macOS persistence is a user setting**, not something the plugin can control.
- **WSL is unsupported in v1** — detected and skipped. A WSL-to-Windows-host adapter is planned.
- **Hard process crashes are not reported.** A hook is a child of the process it would report on; `SessionEnd` fires only on graceful termination. `StopFailure` covers the API-error family, which is the large majority of "the session died on me" cases. See decision D-010.

## Why it cannot break your session

This plugin observes the same lifecycle events that can *control* Claude, so its safety properties are structural rather than aspirational:

- **Every hook is `async: true`.** Async hooks cannot block or control Claude — which matters because exit code 2 on `PreToolUse` would suppress Claude's question, on `Stop` would trap Claude in a non-terminating turn, and on `TaskCompleted` would refuse the completion.
- **The notifier writes nothing to stdout,** so there is no output to parse and nothing that can be malformed.
- **No shell, anywhere.** Hooks use exec form; backends run argument vectors with `shell=False`; on Windows the text travels in environment variables. Notification text is untrusted data and is never executable content.
- **Nothing runs at session start.** No `SessionStart` hook, so installing it cannot slow or disturb a session.

Eleven binding decisions with non-violation checks and reverse-only criteria: [`notification-plugin/docs/decisions.md`](../../notification-plugin/docs/decisions.md).

## Tests

```bash
python notification-plugin/tests/test_notification.py
```

43 stdlib-only tests, no desktop required — isolation contract, text safety, rendering, identity, suppression rules, and structural assertions on `hooks.json` itself.

## Related plugins and integrations

| Pairs with | Why |
|---|---|
| [[Odoo Plugin\|Odoo-Plugin]] | Long `/upgrade` and Docker runs tell your desktop when they finish |
| [[Remotion Plugin\|Remotion-Plugin]] | Render completions surface without watching the terminal |
| Any plugin | Questions and permission prompts stop being something you have to watch for |

## See also

- [[Plugin Catalog|Plugin-Catalog]]
- [[Troubleshooting]]
- [Claude Code hooks reference](https://code.claude.com/docs/en/hooks)
