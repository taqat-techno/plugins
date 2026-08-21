---
description: Check desktop notifications - platform, backend, config, task-tool availability - and send test notifications.
argument-hint: "[--no-test] [--json] [--write-config]"
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
python "${CLAUDE_PLUGIN_ROOT}/hooks/notify.py" --doctor
```

If `python` is not found, retry once with `python3`, then `py -3`. If none of
them resolve, that IS the finding: report that no Python interpreter is on PATH,
so every notification hook fails silently, and that installing Python from
python.org (not the Microsoft Store alias) fixes it.

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
for this session. If they are absent, confirm that `✅ Task Completed` cannot
fire here — the task list is never populated, so the `TaskCompleted` event never
occurs — and that starting Claude Code with `CLAUDE_CODE_ENABLE_TODO_TOOLS=1`
enables it. Do not describe this as a plugin bug; it is a model-availability
rule in Claude Code v2.1.233 and later.

## Flags

| Flag | Effect |
|---|---|
| `--no-test` | Report only; send no test notifications |
| `--json` | Emit the raw capability report as JSON |
| `--write-config` | Write a default `config.json` to the plugin data directory and print its path |

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
  "suppress_teammate_tasks": true
}
```

Turning off `turn` is the usual first edit — `✅ Claude Finished` fires once per
assistant turn, which is the highest-volume notification the plugin sends.

## Scope

This command reports and tests. It does not edit hooks, settings, or any file
other than `config.json` when `--write-config` is passed explicitly.
