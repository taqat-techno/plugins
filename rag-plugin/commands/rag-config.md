---
description: Manage rag-plugin local plugin configuration. Currently controls the opt-in local-only usage-log toggle (default off, no network egress).
argument-hint: "status | telemetry on | telemetry off"
allowed-tools: Bash(test:*), Bash(mkdir:*), Bash(echo:*), Bash(cat:*), Bash(printenv:*), Read, Write
disable-model-invocation: false
author: TaqaTechno
version: 0.1.0
---

# /rag-config

Manage `rag-plugin` plugin configuration. Currently exposes one feature: a **local-only opt-in usage-log toggle**. Default off. No network egress, ever. This honors decision **D-012** in `docs/decisions.md`.

## Behavior

Three subcommands:

| Subcommand | Effect |
|---|---|
| `status` | Show current telemetry state and the log file path. Read-only. |
| `telemetry on` | Create/touch `~/.claude/rag-plugin/usage.log` and set the on-marker file alongside it |
| `telemetry off` | Remove the on-marker file (the existing log is preserved so the user can read it; `cat` it themselves if they want, then `rm` it themselves) |

The plugin reads the on-marker before recording any usage event. If the marker is absent → no recording. If the marker is present → append one JSON line per command invocation.

## What gets recorded (when telemetry is on)

A single JSONL file at `~/.claude/rag-plugin/usage.log`. One JSON object per line:

```json
{"ts": "2026-04-14T13:42:51Z", "command": "rag-status", "outcome": "ok", "failure_id": null}
{"ts": "2026-04-14T13:43:08Z", "command": "rag-repair", "outcome": "ok", "failure_id": "F-003"}
{"ts": "2026-04-14T13:44:12Z", "command": "rag-projects", "outcome": "user-cancel", "failure_id": null}
```

**Field schema:**

| Field | Type | Values |
|---|---|---|
| `ts` | string (ISO 8601 UTC) | `2026-04-14T13:42:51Z` |
| `command` | string | One of: `rag-status`, `rag-doctor`, `rag-setup`, `rag-repair`, `rag-projects`, `rag-upgrade`, `rag-reset`, `rag-config` |
| `outcome` | string | `ok` / `error` / `user-cancel` / `refused` |
| `failure_id` | string or null | F-NNN if `/rag-repair` classified one, else `null` |

**What is NOT recorded** (binding rules from D-012):

- ❌ No paths (config dir, data dir, project paths, log paths)
- ❌ No project names or IDs
- ❌ No search queries (the plugin never sees them — search goes through the MCP server directly)
- ❌ No log contents (the `rag-log-scanner` agent's findings stay in-conversation, never written to disk)
- ❌ No machine identifiers, hostnames, IPs, MAC addresses, usernames
- ❌ No version strings (other than rag-plugin's own version, which is in the file header line)
- ❌ No environment variables
- ❌ No HTTP request bodies or responses
- ❌ No stack traces or error messages

The data is intentionally minimal. The point of recording it is so the user can answer "did I run `/rag-doctor` recently?" or "how often do I hit F-003?" — not so anyone (including the plugin author) can reconstruct what they were doing.

**Network egress: zero.** The log file lives only on the local disk. Nothing reads it except the user. There is no upload, no sync, no third-party endpoint. If you ever see `rag-plugin` make a network call other than the explicit ones in `/rag-upgrade` (GitHub releases API), `/rag-status` (HTTP API on 127.0.0.1), and `/rag-doctor` (HTTP API on 127.0.0.1), it is a bug — please report it.

## Required steps

### Step 0 — Mode detection

Print the standard mode banner. Telemetry is plugin-internal so it works regardless of `install_mode` and `service_mode`.

### Step 1 — Parse subcommand

Whitelist:

| Input | Action |
|---|---|
| `status` | Continue to status branch |
| `telemetry on` | Continue to enable branch |
| `telemetry off` | Continue to disable branch |
| Anything else | Print usage line and stop |

### Step 2 — Resolve the log directory

The log file lives at `~/.claude/rag-plugin/usage.log`. Resolve `~` per platform:

- Windows: `%USERPROFILE%\.claude\rag-plugin\`
- macOS / Linux: `$HOME/.claude/rag-plugin/`

The on-marker file is `~/.claude/rag-plugin/.telemetry-enabled` (an empty file whose presence is the signal).

### Step 3 — Execute the subcommand

#### `status`

1. Read the resolved log directory path.
2. Check whether `.telemetry-enabled` exists.
3. If it exists, read the line count of `usage.log` (if present).
4. Render compact output:

```
ragtools detected: <mode banner>

rag-plugin telemetry: <ON|OFF>
log file: ~/.claude/rag-plugin/usage.log
log size: <N events recorded | empty | not yet created>

what is recorded: timestamp, command name, outcome, optional failure_id
what is NOT recorded: paths, project names, search queries, log contents, identifiers
network egress: none — local-only

toggle: /rag-config telemetry <on|off>
```

#### `telemetry on`

1. Create the log directory if missing: `mkdir -p ~/.claude/rag-plugin/`
2. Create the on-marker: `echo "" > ~/.claude/rag-plugin/.telemetry-enabled`
3. Touch the log file (if missing): `test -f ~/.claude/rag-plugin/usage.log || echo "" > ~/.claude/rag-plugin/usage.log`
4. Print the recording schema (`{"ts": ..., "command": ..., "outcome": ..., "failure_id": ...}`) and the "what is NOT recorded" list one more time, so the user can't claim surprise
5. Confirm: `telemetry: ON. local-only. inspect with: cat ~/.claude/rag-plugin/usage.log`

#### `telemetry off`

1. Remove the on-marker: `test -f ~/.claude/rag-plugin/.telemetry-enabled && rm ~/.claude/rag-plugin/.telemetry-enabled` (or platform equivalent)
2. **Do not** delete the existing log file — the user might want to inspect it. Tell them how to delete it manually if they want:
   ```
   to delete the existing log: rm ~/.claude/rag-plugin/usage.log
   ```
3. Confirm: `telemetry: OFF. existing log preserved at ~/.claude/rag-plugin/usage.log (delete manually if desired).`

## How recording happens (informational)

This command toggles the marker. The actual recording is done by the other rag-plugin commands when they finish. Each command's footer logic checks for the marker and appends a single line to `usage.log` if present. Recording is intentionally **best-effort**: if the marker check or the append fails for any reason, the command's primary work is not affected.

This is documented here for transparency. The user does not need to do anything special — toggling the marker is enough.

## Failure handling

| Situation | Behavior |
|---|---|
| Unknown subcommand | Print usage and stop |
| Cannot resolve `~` (extreme edge case) | Print error and stop — do not invent a log path |
| Cannot create the log directory (permissions) | Print error explaining the path; stop. Telemetry remains off. |
| Log directory exists but `.telemetry-enabled` cannot be created | Print error; stop. Telemetry remains off. |
| `usage.log` is corrupt (not valid JSONL) | `status` reports "log file present but unreadable" — does NOT delete or repair |

## Boundary reminders

- **No network egress, ever.** This is the binding D-012 rule. If a future change to this command adds any network call other than the explicit `/rag-status` and `/rag-doctor` HTTP API probes (which are already loopback-only), revert it.
- **No automatic recording of sensitive data.** Paths, project names, search queries, log contents, identifiers — never. The schema is intentionally minimal.
- **No silent on by default.** The user must explicitly type `telemetry on`. Default state is off.
- **No silent off after enable.** Once `telemetry on` is set, it stays on until the user runs `telemetry off`. There is no auto-disable timer.
- **No deletion of the log file when toggling off.** The user owns the log file. They can `cat` it, `rm` it, or back it up themselves.
- **Compact-by-default** per D-008.

## See also

- `docs/decisions.md` — D-012 telemetry decision (binding, never networked)
- `README.md#what-we-record-telemetry` — user-facing summary
- `ARCHITECTURE.md#what-rag-plugin-never-does` — the boundary contract that forbids networked telemetry
