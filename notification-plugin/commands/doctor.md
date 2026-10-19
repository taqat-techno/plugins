---
description: Check desktop notifications - platform, backend, config, task-tool availability - and send test notifications.
argument-hint: "[--no-test] [--json] [--write-config] [--uninstall-windows-identity]"
allowed-tools:
  - Bash
---

# /notification:doctor

The notification plugin is silent by design: when it cannot deliver, it exits 0
and says nothing, so Claude is never disturbed. That makes it impossible to tell
"working" from "quietly unsupported" without asking. This command asks.

## Bare-invocation behavior

With no arguments, run the full report and send two test notifications:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/notify.py" --doctor
```

The hooks themselves launch `python3`, `python` and `py -3` for every event and
the first one that starts handles it (D-016), so the interpreter you use to run
the doctor is not necessarily the one the hooks use. If `python3` does not run,
try `python`, then `py -3`, and **say which names failed and which one worked** -
do not hide the retry. If none of them runs, that IS the finding: no Python
interpreter is reachable, every notification hook fails silently, and installing
Python 3.8+ from python.org (not the Microsoft Store alias) fixes it.

The report's **Hook interpreters** section is authoritative: it probes each of
the three names exactly as the hooks launch them, and its `last run` line names
the interpreter that handled the most recent hook event.

Print the script's output verbatim, then add a short verdict of your own:

- **backend is `windows` / `macos` / `linux`** — notifications are live. Ask
  whether the two test notifications actually appeared. If they did not, walk
  through the platform notes the script printed.
- **backend is `unsupported`** — say plainly that notifications are off on this
  host and why (WSL, SSH, headless, or no notifier installed), and that this
  costs nothing: every hook still exits 0 and Claude behaves identically.

## Task notifications

The script reports whether `CLAUDE_CODE_ENABLE_TODO_TOOLS` is set. Add what only
you can see: check whether `TaskCreate` / `TaskUpdate` are in your own tool list
for this session. If they are absent, confirm that `☑️ … finished a task`
cannot fire here — the task list is never populated, so the `TaskCompleted` event never
occurs — and that starting Claude Code with `CLAUDE_CODE_ENABLE_TODO_TOOLS=1`
enables it. Do not describe this as a plugin bug; it is a model-availability
rule in Claude Code v2.1.233 and later.

## Flags

| Flag | Effect |
|---|---|
| `--no-test` | Report only; send no test notifications |
| `--json` | Emit the raw capability report as JSON |
| `--write-config` | Write a default `config.json` to the plugin data directory and print its path |
| `--uninstall-windows-identity` | Windows: delete the `HKCU\Software\Classes\AppUserModelId\TaqaTechno.ClaudeCode.Notifications` key the toasts register (do this before uninstalling the plugin; the next toast re-creates it if the plugin is still installed) |

Pass flags straight through to the script. For `--write-config`, print the
resulting path and show the user the file's contents so they can edit it.

## Configuration

Config is optional. Absent means every category is enabled. It lives at
`${CLAUDE_PLUGIN_DATA}/config.json` — never under the plugin root, which is
wiped on every plugin upgrade.

```json
{
  "enabled": true,
  "categories": {
    "question": true, "permission": true,
    "task": true, "turn": true, "failure": true
  },
  "sound": { "attention": true, "informational": false },
  "suppress_teammate_tasks": true,
  "title_only": false,
  "persistent": {
    "question": true,
    "permission": true,
    "failure": true,
    "turn": true,
    "task": false
  }
}
```

`persistent` lists the notifications that stay on screen until closed — by
default everything that means Claude is waiting for you. On Windows each of those
toasts carries a Close button, which Windows requires for this.

`title_only: true` (or the plugin option **Title-only notifications** in
`/plugin`) keeps every question, message and error text off the screen; the
notification then says only what happened and in which project. Either source
can turn it on; neither can turn the other off.

Turning off `turn` is the usual first edit — `✅ … is done` fires once per
assistant turn, which is the highest-volume notification the plugin sends.

## Scope

This command reports and tests. It does not edit hooks, settings, or any file
other than `config.json` when `--write-config` is passed explicitly, and the
registry key only when `--uninstall-windows-identity` is passed explicitly.
