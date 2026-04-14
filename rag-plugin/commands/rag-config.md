---
description: Manage rag-plugin local plugin configuration. Controls the opt-in usage-log toggle, the CLAUDE.md retrieval rule install/upgrade/remove, MCP-duplicate detection/cleanup, and the UserPromptSubmit hook observability log.
argument-hint: "status | telemetry <on|off> | claude-md <status|install|remove> [--yes] [--project] | mcp-dedupe <status|clean> [--yes] | hook-observability <status|on|off|analyze|clear>"
allowed-tools: Bash(test:*), Bash(mkdir:*), Bash(echo:*), Bash(cat:*), Bash(printenv:*), Bash(grep:*), Bash(diff:*), Bash(sed:*), Bash(wc:*), Bash(rm:*), Bash(python3:*), Read, Write, Edit
disable-model-invocation: false
author: TaqaTechno
version: 0.3.0
---

# /rag-config

Manage `rag-plugin` plugin configuration. Four feature groups:

1. **Telemetry toggle** — local-only opt-in usage log. Default off. Honors D-012.
2. **CLAUDE.md retrieval rule** — installs, upgrades, or removes the rule block that tells Claude to reach for `search_knowledge_base` before saying "I don't have information." Source of truth: `rules/claude-md-retrieval-rule.md`. Honors D-016.
3. **MCP-duplicate detection** — scans `~/.claude.json` and `~/.claude/.mcp.json` for duplicate `ragtools` MCP registrations that would conflict with the plugin-level `.mcp.json`. Honors D-015.
4. **UserPromptSubmit hook observability** — controls the `~/.claude/rag-plugin/hook-decisions.log` file that records decision metadata from the retrieval-reminder hook (D-017). Default ON. No user content ever logged.

## Subcommand catalog

| Subcommand | Purpose | Writes? |
|---|---|---|
| `status` | Show current state of all three feature groups in one compact banner | no |
| `telemetry on` / `telemetry off` | Toggle the opt-in usage log | yes (marker file) |
| `claude-md status` | Report whether the retrieval rule is installed, at what version, in which CLAUDE.md file | no |
| `claude-md install` | Install or upgrade the retrieval rule in `~/.claude/CLAUDE.md` (default) or `<cwd>/CLAUDE.md` with `--project` | yes (append to CLAUDE.md) |
| `claude-md remove` | Remove the retrieval rule block cleanly (keeps surrounding CLAUDE.md content) | yes (delete marker range) |
| `mcp-dedupe status` | Report any duplicate ragtools MCP registrations in user-level `.claude.json`, user-level `.mcp.json`, or project-level `.mcp.json` | no |
| `mcp-dedupe clean` | Remove duplicate ragtools MCP registrations from user-level configs, leaving the plugin-level one as the sole active registration | yes (edit JSON files) |
| `hook-observability status` | Show whether the retrieval-reminder hook's decision log is enabled, its path, and line count | no |
| `hook-observability on` | Remove the disable marker (enables hook-decisions logging — default state) | yes (remove marker file) |
| `hook-observability off` | Create the disable marker (disables hook-decisions logging; existing log is preserved) | yes (create marker file) |
| `hook-observability analyze` | Run `scripts/analyze_hook_decisions.py` and print aggregate stats from the log | no |
| `hook-observability clear` | Delete the hook-decisions log file (requires typed `CLEAR` confirmation) | yes (delete log file) |

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

---

# `claude-md` subcommand group

Installs, upgrades, removes, or reports on the **retrieval rule** in `~/.claude/CLAUDE.md`. The rule is the one-page instruction block that tells Claude to call `search_knowledge_base(query=...)` before answering "I don't have information" on any domain question. Source of truth: `${CLAUDE_PLUGIN_ROOT}/rules/claude-md-retrieval-rule.md`.

**Why this exists (D-016):** installing the plugin wires the MCP, but wiring the MCP is not enough — Claude needs a workflow instruction telling it when to use the MCP. Without the rule, Claude scans in-context CLAUDE.md, sees no mention of the user's topic, and says "I don't have information" — even though the answer is in the indexed knowledge base. This subcommand group installs the instruction that closes that loop.

## Resolution order for the target CLAUDE.md

1. If `--project` is passed → target is `<cwd>/CLAUDE.md`
2. Otherwise → target is `~/.claude/CLAUDE.md`
3. Resolve `~` per platform: `%USERPROFILE%\.claude\CLAUDE.md` on Windows, `$HOME/.claude/CLAUDE.md` on macOS/Linux

## Rule-block markers

The rule is delimited by exactly two lines:

```
<!-- rag-plugin:retrieval-rule:begin v=<VERSION> -->
...
<!-- rag-plugin:retrieval-rule:end -->
```

Commands must **never** edit inside the markers. Detect, splice, replace, or delete as a whole. The marker version string (`v=0.2.0`) is how upgrade detection works.

## `claude-md status`

1. Resolve the target CLAUDE.md path per the rules above.
2. If the file does not exist → print `CLAUDE.md rule: not installed (target file missing: <path>)`.
3. If the file exists → `grep -n 'rag-plugin:retrieval-rule:begin' <path>`:
   - No match → `CLAUDE.md rule: not installed (target file: <path>)`
   - Match → extract version from the begin-marker line, compare against bundled version in `${CLAUDE_PLUGIN_ROOT}/rules/claude-md-retrieval-rule.md`, report one of:
     - `CLAUDE.md rule: installed v<N> — up to date`
     - `CLAUDE.md rule: installed v<N> — outdated (bundled: v<M>) — run: /rag-config claude-md install`
4. Compact output: 1–3 lines plus the mode banner.

## `claude-md install [--yes] [--project]`

The install path is idempotent: running it twice on an already-installed rule produces no diff.

### Steps

1. **Load the bundled rule.** Read `${CLAUDE_PLUGIN_ROOT}/rules/claude-md-retrieval-rule.md` and extract the verbatim block between the code fence labeled `## The block (verbatim — this is what gets injected)` — i.e. everything between `<!-- rag-plugin:retrieval-rule:begin v=0.2.0 -->` and `<!-- rag-plugin:retrieval-rule:end -->` (inclusive).

2. **Resolve the target** per the resolution order above.

3. **Read the target file** (if it exists):
   ```bash
   test -f "<target>" && cat "<target>" || echo "NO_FILE"
   ```

4. **Decide the action:**
   - File missing → **create** with just the rule block + trailing newline
   - File present, no begin marker → **append** the rule block (prefixed by a blank line for separation)
   - File present, begin marker exists, version matches → **no-op** (print "already at v<N>")
   - File present, begin marker exists, version differs → **upgrade**: splice the begin→end range with the new block

5. **Show a diff summary** (always, even with `--yes`):
   ```
   target: ~/.claude/CLAUDE.md
   action: install | upgrade | no-op
   lines added: +<N>
   lines removed: -<M>
   lines unchanged: <...>
   ```

6. **Ask for confirmation** unless `--yes` is passed OR the command is invoked from `/rag-setup`'s first-install branch:
   ```
   proceed with install? (yes/no)
   ```

7. **Write the file.** Use the `Write` tool for creates, `Edit` tool for upgrades (splicing by markers). Never use a free-text find-and-replace.

8. **Verify** by re-reading the file and re-running `claude-md status` internally. Print the final state.

9. **Remind the user** that the rule takes effect in the **next** Claude Code session — the current session already loaded the old CLAUDE.md.

### Splice discipline

For upgrades, use `sed` or equivalent to locate the begin→end range and replace it. Conceptually:

```python
# Pseudocode
content = read(target)
begin = content.find("<!-- rag-plugin:retrieval-rule:begin")
end = content.find("<!-- rag-plugin:retrieval-rule:end -->")
end = content.find("\n", end) + 1  # include the end-marker line itself
new_content = content[:begin] + new_block + content[end:]
write(target, new_content)
```

**Never touch anything outside the begin→end range.**

## `claude-md remove [--yes] [--project]`

Removes the rule block cleanly, leaving the rest of the target CLAUDE.md intact.

### Steps

1. Resolve the target per the resolution order.
2. `grep -n 'rag-plugin:retrieval-rule:begin'` — if no match, print "rule is not installed" and stop.
3. **Confirm** unless `--yes`:
   ```
   about to remove the retrieval rule block from <target>.
   the rest of the file will be untouched.
   type REMOVE to confirm:
   ```
   (The user types the literal word `REMOVE` — same discipline as `/rag-reset`.)
4. Splice the begin→end range out of the file. Also strip **at most one** leading and **at most one** trailing blank line around the removed range, to avoid leaving a double-blank gap.
5. Write the file.
6. Verify via `claude-md status` — should report "not installed".

**The remove operation does not delete the source of truth file** (`${CLAUDE_PLUGIN_ROOT}/rules/claude-md-retrieval-rule.md`) — that stays bundled with the plugin and can be re-installed at any time.

---

# `mcp-dedupe` subcommand group

Scans `~/.claude.json` (top-level `mcpServers` and per-project `mcpServers` sub-objects) and `~/.claude/.mcp.json` for **duplicate** ragtools MCP registrations that would conflict with the plugin-level `.mcp.json` shipped by this plugin. Reports them with `status`, removes them with `clean`.

**Why this exists (D-015 cleanup):** before the plugin shipped plugin-level MCP auto-wiring, users manually added `ragtools` entries to `~/.claude.json` or `~/.claude/.mcp.json`. After the plugin is installed, those entries become duplicates — the same server name is registered twice. Claude Code's behavior with duplicates is implementation-defined and at minimum wasteful. This subcommand detects and cleans them up.

## `mcp-dedupe status`

1. Read `~/.claude.json`. Walk:
   - Top-level `mcpServers.ragtools`
   - Every `projects.<path>.mcpServers.ragtools`
2. Read `~/.claude/.mcp.json` (if it exists). Walk `mcpServers.ragtools`.
3. **Validate the plugin-level `.mcp.json`** at `${CLAUDE_PLUGIN_ROOT}/.mcp.json`. This is not just a count — the file must be **structurally valid** and **resolvable**. Run these assertions in order; each failure is reported as a distinct ERROR:
   - **EXISTS** — file is present and parseable as JSON. If not: `ERROR — plugin .mcp.json missing or malformed at <path>`.
   - **SCHEMA (flat shape)** — top-level object has a `ragtools` key directly (no `mcpServers` wrapper). **Plugin-level `.mcp.json` uses the flat shape**, unlike user-level `~/.claude/.mcp.json` or project-level `<repo>/.mcp.json` which use the `mcpServers` wrapper. Claude Code's plugin loader expects the flat shape for plugin-level registrations — verified empirically against every working plugin in `~/.claude/plugins/cache/` (`chrome-devtools`, `context7`, `playwright`, `azure-devops`, and rag v0.2.0/v0.3.0 all ship the flat shape). If the top-level `ragtools` key is missing: `ERROR — plugin .mcp.json missing top-level 'ragtools' key`. If a `mcpServers` wrapper is present instead: `ERROR — plugin .mcp.json uses wrapped shape (mcpServers); plugin-level files require the flat shape — unwrap it`.
   - **COMMAND RESOLVES ON PATH** — read `ragtools.command`. Run `shutil.which(command)` (or `where` on Windows / `which` on POSIX). If not found: `ERROR — plugin .mcp.json command '<cmd>' not on PATH`.
   - **LAUNCHER PRESENT** (only when command is the cross-mode launcher pattern) — if `command` is `python` / `python3` / `py` **and** any arg contains `rag_mcp_launcher.py`, resolve the arg against `${CLAUDE_PLUGIN_ROOT}` and assert the file exists and is readable. If not: `ERROR — launcher script <path> missing or unreadable`.
4. **Report** every location where a `ragtools` entry was found, with the plugin-level assertion result on its own line:
   ```
   mcp-dedupe status:
     plugin-level (canonical): python ${CLAUDE_PLUGIN_ROOT}/scripts/rag_mcp_launcher.py  [schema OK, launcher present, python on PATH]
     user top-level:            rag.exe serve                                              [source: ~/.claude.json → mcpServers.ragtools]
     project-level: C:/MY-WorkSpace/rag  → rag-mcp                                         [source: ~/.claude.json → projects.<...>.mcpServers.ragtools]
   
   duplicates found: 2
   recommendation: /rag-config mcp-dedupe clean
   ```
5. If no duplicates and plugin-level passes all four assertions: `mcp-dedupe status: 1 registration (plugin-level, canonical). schema OK. no duplicates found.`
6. If the plugin-level fails any assertion, **surface that first** — it is always more urgent than duplicates, because a broken plugin-level registration means Claude Code cannot load ragtools at all regardless of what's in user-level files.

## `mcp-dedupe clean [--yes]`

Removes all duplicate `ragtools` entries, leaving only the plugin-level one.

### Steps

1. Run `mcp-dedupe status` internally to find duplicates.
2. If none, print "nothing to clean" and stop.
3. **Show the list** of locations that will be modified:
   ```
   about to remove ragtools MCP registrations from:
     • ~/.claude.json → mcpServers.ragtools
     • ~/.claude.json → projects.C:/MY-WorkSpace/rag.mcpServers.ragtools
     • ~/.claude/.mcp.json → mcpServers.ragtools
   
   the plugin-level .mcp.json (plugin/rag-plugin/.mcp.json) will remain as the sole registration.
   ```
4. **Confirm** unless `--yes`:
   ```
   type CLEAN to confirm:
   ```
5. **Backup first** — copy each target file to `<target>.bak-pre-mcp-dedupe` (preserve permissions).
6. **Remove the entries** using a Python/jq-equivalent atomic edit:
   - Load JSON → delete the `ragtools` key from each location → write via tmp+rename (never in-place).
   - If a `mcpServers` object becomes empty after removal, **leave it as `{}`** rather than deleting the key entirely. This matches what was there before the dedupe.
7. **Verify** by re-running `mcp-dedupe status`. Should report 1 registration (plugin-level only).
8. **Remind the user** to restart Claude Code to pick up the cleaned state.

### Safety rules

- **Never remove the plugin-level `.mcp.json`.** That's the canonical registration.
- **Never touch non-ragtools MCP entries.** Only the `ragtools` key gets removed.
- **Always backup** before editing. The backup path is `<original>.bak-pre-mcp-dedupe`.
- **Atomic writes only.** Load → modify in memory → write to `.tmp` → rename. Never in-place edit.
- **Per-project entries are removed too** unless the user explicitly passes `--keep-project`. Default is: all duplicates go, plugin-level stays.

---

# `hook-observability` subcommand group

Controls the `~/.claude/rag-plugin/hook-decisions.log` file written by the `UserPromptSubmit` retrieval-reminder hook (`hooks/prompt_retrieval_reminder.py`). See **D-017** in `docs/decisions.md` and the README section "What we record".

**Default state:** **enabled.** Rationale: the log contains zero user content (decision metadata only — timestamp, shape_match, probe_match, probe_top_score, action tag, prompt_length, hook version). The user asked for observability to drive the Tier-2-vs-Tier-3 escalation decision, so the default must actually accumulate data.

**Opt-out marker:** `~/.claude/rag-plugin/.hook-observability-disabled` (empty file). Presence disables the hook's logging. Absence enables it.

**What the log contains:** one JSON object per hook invocation with these fields only:

| Field | Type | Example |
|---|---|---|
| `ts` | ISO 8601 UTC | `2026-04-14T15:11:35Z` |
| `shape_match` | bool | `true` |
| `probe_match` | bool | `true` |
| `probe_top_score` | float | `0.813` |
| `action` | string | `reminder-injected` / `silent-pass:<reason>` |
| `prompt_length` | int | `53` |
| `hook_version` | string | `0.3.0` |

**What the log does NOT contain:** prompt text, query text, result content, file paths, project IDs, machine identifiers, environment variables, or anything the user typed. D-012 aligned.

## `hook-observability status`

1. Resolve `~/.claude/rag-plugin/`. Check for the log file and the disable marker.
2. Render:
   ```
   hook-observability: ENABLED    (default)
     log file:  ~/.claude/rag-plugin/hook-decisions.log
     log size:  <N> lines, <B> bytes
     last entry ts: <ts or "empty">
   ```
   Or when disabled:
   ```
   hook-observability: DISABLED
     disable marker: ~/.claude/rag-plugin/.hook-observability-disabled
     log file (preserved): ~/.claude/rag-plugin/hook-decisions.log (<N> lines)
     to re-enable: /rag-config hook-observability on
   ```

## `hook-observability on`

Removes the disable marker. No-op if already enabled.

```bash
rm -f "$HOME/.claude/rag-plugin/.hook-observability-disabled"
```

Confirm: `hook-observability: ENABLED. future hook invocations will append to ~/.claude/rag-plugin/hook-decisions.log.`

## `hook-observability off`

Creates the disable marker. The existing log file is **preserved** — user can inspect it before deciding to delete.

```bash
mkdir -p "$HOME/.claude/rag-plugin"
touch "$HOME/.claude/rag-plugin/.hook-observability-disabled"
```

Confirm: `hook-observability: DISABLED. the hook will silent-pass without logging. existing log preserved at <path>. to delete: /rag-config hook-observability clear.`

## `hook-observability analyze`

Runs the bundled analyzer and prints aggregate stats:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/analyze_hook_decisions.py"
```

The analyzer produces:
- Total decisions
- Breakdown by action tag
- Probe-score histogram (only for decisions where the probe ran)
- Shape gate pass rate, reminder injection rate
- Hook version distribution
- Tuning hints (e.g., "injection rate is too high — raise the threshold")

**Read-only.** The analyzer never modifies the log or calls the MCP.

## `hook-observability clear`

Deletes the log file. Requires typed `CLEAR` confirmation (same discipline as `/rag-reset`).

### Steps

1. Resolve the log path.
2. If the file doesn't exist, print `log file not found — nothing to clear` and stop.
3. Print the current line count and last-entry timestamp so the user knows what they're about to delete:
   ```
   about to delete: ~/.claude/rag-plugin/hook-decisions.log
   current size: <N> lines (<B> bytes)
   last entry: <ts>
   
   this is irreversible. type CLEAR to confirm:
   ```
4. Wait for the user to type `CLEAR` verbatim.
5. Delete the file:
   ```bash
   rm "$HOME/.claude/rag-plugin/hook-decisions.log"
   ```
6. Confirm: `log cleared. future hook invocations will create a fresh log (assuming observability is enabled).`

**The clear operation does NOT touch the disable marker** — if observability is off, it stays off after clear. If on, it stays on.

---

# `status` — unified dashboard

The top-level `status` subcommand prints a compact summary of all four feature groups in ≤ 18 lines:

```
ragtools detected: <mode banner>

rag-plugin v0.3.0 configuration:
  telemetry:          OFF                                          (see /rag-config telemetry on)
  CLAUDE.md rule:     INSTALLED v0.2.0 at ~/.claude/CLAUDE.md
  MCP registrations:  1 (plugin-level, canonical)                  [OK]
  hook-observability: ENABLED                                      (247 decisions logged)

next:
  • /rag-config telemetry on           — enable local-only usage logging
  • /rag-config claude-md status       — detail the retrieval rule state
  • /rag-config mcp-dedupe status      — detail MCP registrations
  • /rag-config hook-observability analyze  — inspect hook decision stats
```

If any of the four is in a non-default state (telemetry on, rule outdated/missing, duplicates found, observability disabled), the corresponding row gets a `!` marker and the `next:` section surfaces the remediation command.

## Boundary reminders (whole command)

- **Read the rules file as the source of truth.** Never invent the rule content inline.
- **Splice by markers.** Never use find-and-replace on the rule body.
- **Always backup before editing user config files** (`~/.claude.json`, `~/.claude/.mcp.json`, `~/.claude/CLAUDE.md`). Backup extension: `.bak-pre-<operation>`.
- **Atomic writes only.** Load → modify → write tmp → rename.
- **Confirm by default**, with `--yes` opt-out for scripted use (and a silent pass when called from `/rag-setup`'s first-install flow).
- **Never touch non-ragtools MCP entries.** Other servers are off-limits.
- **Never delete the plugin-level `.mcp.json`.**
- **Never networked telemetry (D-012).** Unchanged by this update.
- **Hook-decisions log contains zero user content (D-017).** Only decision metadata: timestamp, shape_match, probe_match, probe_top_score, action tag, prompt_length, hook version. Never the prompt text, never the query, never the results.
- Compact-by-default per D-008.

## See also

- `rules/claude-md-retrieval-rule.md` — source of truth for the retrieval rule block
- `hooks/prompt_retrieval_reminder.py` — the UserPromptSubmit hook whose decisions `hook-observability` surfaces
- `scripts/analyze_hook_decisions.py` — aggregate analyzer invoked by `hook-observability analyze`
- `/rag-setup` — calls `claude-md install` and `mcp-dedupe clean` as part of Step C.2b / C.5
- `/rag-doctor` — surfaces retrieval-rule, MCP-dedupe, and hook-observability state in the diagnostic table
- `/rag-repair` — classifies plugin-behavior symptoms that route here
- `docs/decisions.md#d-015` — plugin-level `.mcp.json` auto-wiring
- `docs/decisions.md#d-016` — CLAUDE.md retrieval rule as a shipped plugin asset
- `docs/decisions.md#d-017` — Tier 2 guided-enforcement hook + observability-first escalation
