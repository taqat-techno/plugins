---
description: Per-workspace ragtools knowledge-base focus. Default — focus is keyed by the current workspace (git root or cwd).
argument-hint: "[set|status|clear|<project-name>] [--auto] [--global] [--all]"
allowed-tools: Bash(python:*), Bash(python3:*), Bash(curl:*), Bash(git:*), Read, mcp__plugin_rag_ragtools__list_projects, mcp__plugin_rag_ragtools__index_status
disable-model-invocation: false
---

# /project-focus

Make Claude focus ragtools retrieval on **the current workspace's project**. After activation, every UserPromptSubmit inserts a reminder that scopes `search_knowledge_base` to the focused project — by passing a project filter parameter when supported, or by post-filtering results by project metadata when not. Cross-project retrieval is allowed **only when the user explicitly asks** (e.g. "compare across projects", "all projects").

**v0.13.0 model (D-028, supersedes D-025 §1):**

- Focus is **per-workspace** by default. The workspace key is the normalized git root (or cwd when no `.git/` is present).
- An **explicit global** focus is opt-in via `--global` and is **clearly labelled in every reminder** so Claude understands it applies because the user used `--global`, not because it matches the current cwd.
- Effective focus precedence: **workspace > global > none**.
- If focus exists for other workspaces but none applies to the current cwd AND no global is set, the hook emits a **neutral notice** that does NOT include the foreign project's name. Claude will not accidentally use unrelated focus.

## Subcommands

| Invocation | Behavior |
|---|---|
| `/project-focus` | Auto-detect: CWD → git root → match against `list_projects` → persist focus for the **current workspace**. |
| `/project-focus <project-name>` | Manual workspace focus: focus the **current workspace** on the named project. |
| `/project-focus --global <project-name>` | **Explicit global focus.** Applies whenever no workspace-specific focus exists. Requires a project name (auto-detection is meaningless globally). |
| `/project-focus status` | Show current workspace key, workspace focus, global focus, **effective focus**, and any drift signals. |
| `/project-focus clear` | Clear ONLY the current workspace's focus. Global, if any, is untouched. |
| `/project-focus clear --global` | Clear ONLY the global focus. Workspaces map untouched. |
| `/project-focus clear --all` | Clear all workspace focuses AND the global. |

## Step 0 — State detection

Follow `${CLAUDE_PLUGIN_ROOT}/rules/state-detection.md`. Print the 6-line mode banner. If `state.install_mode == not-installed`, the focus state is still settable (manual name only) but the auto-detection path will warn: with no service, `list_projects` cannot be enumerated. Proceed regardless — the state file is the single source of truth for the hook.

## Step 1 — Dispatch

Parse the first positional argument:

- empty / missing → **set (auto)**
- `set` → **set (auto)** unless followed by a name
- `status` → **status**
- `clear` → **clear**
- anything else → **set (manual)** with that argument as the project name

`--auto` forces the auto-matcher even if a name is given (for testing).

## Step 2 — Run the engine

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/project_focus.py" <subcommand> [<name>] [--auto]
```

The script returns a JSON object on stdout. Render the relevant fields to the user — never dump the raw JSON.

### set (auto)

The script:

1. Resolves CWD and the git root (via `.git/` traversal, with a `git rev-parse --show-toplevel` fallback).
2. Calls `GET /api/projects` on the local ragtools service to enumerate configured projects (no MCP call — the script is hook-style stdlib-only).
3. Matches the CWD/git_root against each configured project's path(s) using:
   - **exact-path** (highest score)
   - **ancestor-path** (project path is an ancestor of CWD or git_root)
   - **descendant-path** (project path is below CWD; lower score)
4. If a single best match exists, writes `~/.claude/rag-plugin/state/project-focus.json` and returns `{ok: true, set: {...}, alternatives: [...]}`.
5. If multiple candidates are equally specific, returns `{ok: false, reason: "ambiguous", candidates: [...]}` — the user must rerun with an explicit name.
6. If no match, returns `{ok: false, reason: "no-match", candidates: [...]}` — the user can pass an explicit name or run `/rag:projects add` first.

If `service_reachable: false` and a manual name was given, the script writes the state with `match_method: "manual-no-config"` and a `warning` field — the focus is set by name only, not cross-checked.

### set (manual `<name>`)

Same as auto, but skips the directory match and looks up the project by name (exact, then case-insensitive substring). If not found in `list_projects`, the script returns `no-match`. Render the candidate list.

### status

The script reads the state file and re-probes `list_projects` to flag staleness (`still_in_list_projects: true|false|null`). Render:

- focused project name + path
- match method
- created_at timestamp
- whether the project is still in `list_projects` (warn if no)

### clear

The script removes the state file. After this, the `project_focus_inject.py` UserPromptSubmit hook silent-passes — no more reminders. Cross-project retrieval is back to default.

## Step 3 — Confirm to the user (compact, per D-008)

After a successful `set`, print to chat:

```
project-focus: ON
  project: <name>
  path:    <path or "(by name only)">
  matched: <method>
  alternatives: <count> (run /project-focus status to see them)

ragtools retrieval is now scoped to <name>.
Cross-project search requires an explicit phrase like "across all projects".
Clear with /project-focus clear.
```

For `status`: same shape, plus the staleness flag if false.
For `clear`: one line — `project-focus: cleared. cross-project retrieval restored.`

## Behavior contract while focus is active

The bundled UserPromptSubmit hook (`hooks/project_focus_inject.py`) injects this reminder on every prompt:

> /project-focus is ACTIVE — strict mode. Focused project: `<name>` at `<path>`.
>
> When calling `search_knowledge_base` for project-specific questions:
> 1. If the tool supports a project filter parameter, pass it: `project="<name>"`.
> 2. If not, post-filter the results by project metadata (source / path / name) and keep only entries that match `<name>` or are under `<path>`.
> 3. If filtering cannot be guaranteed from the response shape, WARN the user that strict focus could not be technically enforced for this query.
>
> If no focused-project results are found, say so. Do NOT silently fall back to other projects. Cross-project retrieval is allowed only when the user explicitly asks.

Claude must follow this reminder in every subsequent turn until `/project-focus clear` runs.

## Safety invariants (binding)

1. **Never auto-mutate ragtools project config.** This command does not call `add_project`, `reindex_project`, `run_index`, `add_project_ignore_rule`, or any project-mutating MCP tool. If the focused project is missing from `list_projects`, the command tells the user what to run; it does not run it.
2. **Never persist user prompts.** The hook reads the state file only; it never reads or logs the prompt.
3. **Atomic state writes.** The script uses `tmp + os.replace`. The state file is never partially written.
4. **State file is the single source of truth.** The hook reads only this file. No environment variables, no second config location.
5. **Hook silent-passes on any error.** Missing file, malformed JSON, or unreadable state → no output, exit 0. The retrieval-reminder hook still fires independently.
6. **Cross-project retrieval requires an explicit user phrase.** "across all projects", "global knowledge", "compare projects", "all of them" — anything weaker keeps focus.

## Per-workspace focus model (v0.13.0 — closes the v0.9 leak)

In v0.9.x, focus was a single global record. Setting focus in workspace A meant every other workspace silently inherited it. v0.13.0 fixes this by storing focus as a **map keyed by normalized workspace root** plus an optional explicit **global** record.

**State file shape (v2 schema):**

```json
{
  "schema_version": 2,
  "engine_version": "0.13.0",
  "workspaces": {
    "<normalized-workspace-key>": { "<focus-record>", "scope": "workspace" }
  },
  "global": null | { "<focus-record>", "scope": "global" }
}
```

**Hook behavior — strict by default:**

| Situation | Hook output |
|---|---|
| Workspace record matches current cwd (enabled) | Inject the focused project; standard reminder. |
| No workspace record; explicit global is set | Inject the global project, **labelled as `EXPLICIT GLOBAL FOCUS`** — Claude is told this applies because the user ran `--global`, not because it matches cwd. |
| Other workspaces have focus but neither this workspace nor a global applies | Inject a **neutral notice** that focus exists elsewhere but is **NOT applied here**. The other project's name is **never included** so Claude cannot accidentally use it. |
| Nothing applies | Silent-pass. |

**State migration from v0.9 → v0.13:**

- v1 state files are auto-migrated on first read.
- Migration key = `_norm(git_root_at_set)` → fallback `_norm(cwd_at_set)`.
- If neither is usable (empty or non-existent), focus is **disabled** and the user is asked to rerun `/rag:project-focus`.
- v1 records are NEVER auto-promoted to global.
- Before migration, the original v1 file is copied once to `~/.claude/rag-plugin/state/project-focus.v1.bak.json` for manual rollback.

## Machine-local state (do not Syncthing this directory)

The state file lives at `~/.claude/rag-plugin/state/project-focus.json`. It encodes per-machine workspace paths (e.g. `c:/my-workspace/...` on Windows, `/home/.../workspace/...` on WSL) which **do not normalize to the same key across machines**. Add the directory to Syncthing's `.stignore` (or your sync tool's equivalent) so machine-A's workspace keys do not appear on machine-B as ghost entries that the hook silent-passes on.

If you do hit ghost entries from another machine after a sync, list them with `/rag:project-focus status` (the `all_workspaces` field) and remove specific stale keys with `/rag:project-focus clear --all` — there is no `clear --workspace <key>` in v0.13.0; that is potential Phase 2 work.

## What if `search_knowledge_base` doesn't support a project filter?

This is the v0.9.0 reality: the tool may or may not accept a `project=...` parameter depending on the ragtools version. The hook reminder asks Claude to:

1. **Try the parameter first.** If it works, great.
2. **Otherwise, post-filter.** Result entries usually carry `source`, `path`, or `project` metadata that lets Claude keep only matching results.
3. **Warn when filtering cannot be guaranteed.** If the result shape doesn't expose project metadata, surface the limitation in the response — do not pretend to enforce strict focus when you can't.

The v0.10.0 plan (D-025 reverse criteria) is to wire a wrapper through the plugin once ragtools exposes a stable `project` parameter.

## When the focused project isn't indexed

Tell the user what to run (do not run it):

- Project not in `list_projects` at all → `/rag:projects add <path>` then `/rag:projects rebuild <name>`
- Project in `list_projects` but no chunks → `/rag:projects rebuild <name>` or `mcp__plugin_rag_ragtools__reindex_project`
- Project disabled → `/rag:projects enable <name>`

## Manual validation checklist

1. `python scripts/project_focus.py self-test` → all checks pass.
2. `python scripts/test_project_focus.py` → all 30 tests green (covers v1→v2 migration, workspace-keyed CRUD, hook injection paths).
3. From inside a known-indexed project: `/project-focus` → status shows `effective_source: workspace`.
4. **Leak regression:** open a Claude Code session in a different workspace. Status should show `effective_source: none` or `other-workspace-only` (NOT a workspace value carried over from the previous session). The hook either silent-passes or injects only the neutral notice — no project name leaks.
5. **Explicit global:** `/project-focus --global royal-preps`. From any workspace without its own focus, status shows `effective_source: global`, and the injected reminder contains the literal phrase `EXPLICIT GLOBAL FOCUS`.
6. `/project-focus clear` → only the current workspace's record is removed; global, if set, remains.
7. `/project-focus clear --global` → global removed; workspaces map remains.
8. `/project-focus clear --all` → both removed.
9. `/project-focus nonexistent-name` → `no-match` with candidate list.
10. **v1 migration smoke:** with the live state file backed up, manually write a v1 single-record file and run `/project-focus status` — confirm v2 schema, `migrated_from_v1_at` populated, `~/.claude/rag-plugin/state/project-focus.v1.bak.json` exists.

## See also

- `/projects` — list / add / remove / rebuild ragtools projects
- `/doctor` — service + index status before activating focus
- `hooks/project_focus_inject.py` — the UserPromptSubmit hook that injects focus context
- `scripts/project_focus.py` — the matcher + state engine
- `docs/decisions.md` — D-025 (focus contract + filter fallback policy)
