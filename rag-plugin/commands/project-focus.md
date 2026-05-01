---
description: Restrict ragtools knowledge-base retrieval to the current working project so Claude does not pull context from unrelated indexed projects. Auto-detects the project from CWD + git root, matches against ragtools list_projects, and persists state at ~/.claude/rag-plugin/state/project-focus.json. A bundled UserPromptSubmit hook injects scope-this-to-X reminders into every subsequent prompt while focus is active. Subcommands — set / status / clear — plus optional manual project name argument.
argument-hint: "[set|status|clear|<project-name>] [--auto]"
allowed-tools: Bash(python:*), Bash(python3:*), Bash(curl:*), Bash(git:*), Read, mcp__plugin_rag_ragtools__list_projects, mcp__plugin_rag_ragtools__index_status
disable-model-invocation: false
author: TaqaTechno
version: 0.9.0
---

# /project-focus

Make Claude focus ragtools retrieval on **only the current project**. After activation, every UserPromptSubmit inserts a reminder that scopes `search_knowledge_base` to the focused project — by passing a project filter parameter when supported, or by post-filtering results by project metadata when not. Cross-project retrieval is allowed **only when the user explicitly asks** (e.g. "compare across projects", "all projects").

## Subcommands

| Invocation | Behavior |
|---|---|
| `/project-focus` | Auto-detect: CWD → git root → match against `list_projects` → persist focus state. |
| `/project-focus <project-name>` | Manual: focus on the named project. The name must appear in `list_projects` (case-insensitive). |
| `/project-focus status` | Print the current focus state, match method, and whether the project still exists in `list_projects`. |
| `/project-focus clear` | Remove the focus state file; subsequent prompts get no project-focus reminder. |

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
6. If no match, returns `{ok: false, reason: "no-match", candidates: [...]}` — the user can pass an explicit name or run `/rag:rag-projects add` first.

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

## What if `search_knowledge_base` doesn't support a project filter?

This is the v0.9.0 reality: the tool may or may not accept a `project=...` parameter depending on the ragtools version. The hook reminder asks Claude to:

1. **Try the parameter first.** If it works, great.
2. **Otherwise, post-filter.** Result entries usually carry `source`, `path`, or `project` metadata that lets Claude keep only matching results.
3. **Warn when filtering cannot be guaranteed.** If the result shape doesn't expose project metadata, surface the limitation in the response — do not pretend to enforce strict focus when you can't.

The v0.10.0 plan (D-025 reverse criteria) is to wire a wrapper through the plugin once ragtools exposes a stable `project` parameter.

## When the focused project isn't indexed

Tell the user what to run (do not run it):

- Project not in `list_projects` at all → `/rag:rag-projects add <path>` then `/rag:rag-projects rebuild <name>`
- Project in `list_projects` but no chunks → `/rag:rag-projects rebuild <name>` or `mcp__plugin_rag_ragtools__reindex_project`
- Project disabled → `/rag:rag-projects enable <name>`

## Manual validation checklist

1. `python scripts/project_focus.py self-test` → all checks pass.
2. From inside a known-indexed project: `/project-focus` → state file appears, `project-focus: ON` confirmation prints.
3. `/project-focus status` → prints the focused project + match method.
4. From an unrelated directory with `/project-focus` active: a domain question retrieves only focused-project results (verify via Claude's response citing only the focused project's source files).
5. `/project-focus clear` → state file removed; subsequent prompts get no focus reminder.
6. `/project-focus nonexistent-name` → `no-match` with candidate list.

## See also

- `/rag-projects` — list / add / remove / rebuild ragtools projects
- `/rag-doctor` — service + index status before activating focus
- `hooks/project_focus_inject.py` — the UserPromptSubmit hook that injects focus context
- `scripts/project_focus.py` — the matcher + state engine
- `docs/decisions.md` — D-025 (focus contract + filter fallback policy)
