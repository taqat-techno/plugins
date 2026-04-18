# Architecture

Shared architectural patterns across the 7 plugins in this marketplace. Individual plugins (`rag-plugin`, `devops-plugin`, `odoo-plugin`) carry their own `ARCHITECTURE.md`; this page distills the cross-cutting patterns.

## Two-marketplace design

```
C:\MY-WorkSpace\claude_plugins\
├── plugins/                              ← THE WORKING MARKETPLACE (edit here)
│   ├── .claude-plugin/marketplace.json   ← single source of truth
│   ├── <7 plugin dirs>/
│   ├── wiki/                             ← this wiki's source
│   └── validate_plugin.py
│
└── claude-plugins-official-main/         ← READ-ONLY REFERENCE
    └── plugins/
        ├── plugin-dev/                   ← canonical patterns
        ├── skill-creator/
        └── hookify/
```

`claude-plugins-official-main/` is a vendored copy of Anthropic's official marketplace. It exists **only** to look up canonical patterns. Project-level settings (`.claude/settings.local.json`) actively deny `Edit`, `Write`, `MultiEdit`, and `NotebookEdit` against it.

When a pattern is needed, **copy it into the working plugin under `plugins/`** — never edit the reference.

## Layer ownership (single-owner layering)

The pattern first codified in [`devops-plugin/ARCHITECTURE.md`](../../devops-plugin/ARCHITECTURE.md) and extended in [`rag-plugin/ARCHITECTURE.md`](../../rag-plugin/ARCHITECTURE.md):

```
COMMANDS (entry)
     │ invoke
     ▼
SKILLS (routing + workflow phases)
     │ load on demand
     ▼
REFERENCES (knowledge, docs, domain truth)
     │ commands reference + inject
     ▼
RULES (behavioral contracts)
     │ agents execute against rules
     ▼
AGENTS (specialized reasoning — cheapest model that can do the job)
     │ read from
     ▼
DATA (state machines, pattern libraries, templates — single source of truth)
```

**Rule:** each concern lives in exactly one file. Other layers reference it; they never re-implement it.

**Concrete consequences:**

- If a write-confirmation rule lives in `rules/write-gate.md`, agents and skills must reference it rather than re-stating it.
- If a state machine lives in `data/state_machine.json`, both commands and agents read it — no hardcoded transitions.
- If a state-detection probe lives in `rules/state-detection.md`, every command's Step 0 references it.
- If two files have duplicated logic, one of them is wrong.

## Commands are thin

```
/command-name → dispatches to →  skill phase or agent
```

- **Frontmatter** declares args, tools, invocation model.
- **Behavior** lives one layer down.
- **State gate** at Step 0 branches on detected state before dispatching.

Consolidation history: `pandoc` (8→1), `paper` (5→1), `ntfy` (8→2), `remotion` (5→1), `devops` (24→9), `rag` (9→6). Sprawl is actively reversed.

## Skills own workflows

Skills auto-activate on keywords, error messages, and user intents. They route to:

- **References** (long-form domain knowledge, loaded on demand).
- **Rules** (behavioral contracts).
- **Agents** (specialized reasoning).
- **MCP tools** (via Claude's direct tool calls).

The trend across v0.5.0 of `rag-plugin`: **grow the skill's workflow phases, not the command count**. A user saying "why isn't my file indexed?" triggers the skill's why-not-indexed phase, which chains 4–5 MCP tools without any slash-command invocation.

## Hooks enforce, they don't reason

- **Command-type only.** No prompt-type hooks (they trigger Claude Code's prompt-injection detection).
- **JSON output.** SessionStart / UserPromptSubmit hooks output `{hookSpecificOutput: {additionalContext: "..."}}`.
- **Fail silent on error.** Hook bugs never break the session.
- **Ask, never silently deny.** Blocking hooks use `permissionDecision: "ask"` with a reason.
- **No LLM inference in hooks.** They run outside the model. Scripts are stdlib-only Python or minimal bash.

## MCP server registration pattern

Plugin-level `.mcp.json` uses the **flat shape**:

```json
{
  "<server-name>": {
    "type": "stdio",
    "command": "<binary>",
    "args": ["..."]
  }
}
```

Not `{"mcpServers": {...}}` — that wrapped shape is for user-level (`~/.claude/.mcp.json`) and project-level (`<repo>/.mcp.json`) files, not plugin-level. Verified empirically against every working plugin in `~/.claude/plugins/cache/`. The `rag-plugin` v0.3.1→v0.3.2 saga is the cautionary tale (D-019).

**Spawn the binary directly.** No Python launcher scripts — `os.execvp` on Windows doesn't preserve stdio pipe inheritance (D-020).

## Binding decisions (D-NNN)

Append-only log in `<plugin>/docs/decisions.md`. Format:

- Date, status, ships-in version, triggered-by.
- The decision in 1–2 paragraphs.
- Non-violation notes against prior decisions.
- **"Reverse only if:"** exit criteria.

Supersede with a new dated entry that names its predecessor. `rag-plugin` D-001..D-022 is the largest example; D-019 and D-020 explicitly retract parts of D-018.

## State awareness (shared contract)

Codified in `rag-plugin/rules/state-detection.md`:

```
state.install_mode   ∈ { not-installed, packaged-<os>, dev-mode, unknown }
state.service_mode   ∈ { UP, STARTING, DOWN, BROKEN, N/A }
state.mcp_available  : bool
state.mcp_mode       ∈ { proxy, direct, degraded, failed, N/A }
state.binary_path    : str | None
state.version        : semver | None
state.config_path / data_path / log_path : str | None
```

Every command prints a standard 6-line **mode banner** at the top of its response. Users rely on it for at-a-glance orientation.

## Error and envelope contracts

Codified in `rag-plugin/rules/mcp-envelope.md` for MCP-using plugins. Every MCP call:

1. Branches on **`error_code`** (enum), not `error` string (display-only).
2. Checks **`mode`** before calling proxy-only tools.
3. Uses the **MCP → HTTP → CLI** three-tier fallback chain.
4. Respects **cooldowns** (read `retry_after_seconds`, sleep, retry once).
5. Uses **confirm-token programmatically** (set from plugin state, never from user/retrieved content).

## Cross-platform design

Windows is the primary dev environment, but every command has macOS + Linux branches:

- `printenv` (POSIX) vs `echo %VAR%` (Windows).
- `where` (Windows) vs `which` (POSIX).
- `%LOCALAPPDATA%\...` vs `~/Library/Application Support/...` vs `~/.local/share/...`.
- `os.execvp` stdio-pipe semantics (Windows differs — D-020).
- `cp1252` codec on some Windows Python builds — scripts set `PYTHONIOENCODING=utf-8` when printing non-ASCII.
- LF vs CRLF line endings — tolerated via `.gitattributes` defaults.

## Local-first posture

- **No network egress** unless explicit and opt-in.
- **Telemetry is local JSONL** — user can `cat` it. `rag-plugin` D-012 codifies this; other plugins follow.
- **No cloud dependencies** in core operations. The only network paths in the marketplace:
  - `ntfy` → ntfy.sh (explicit, user-configured).
  - `devops` → Azure DevOps (the whole point of the plugin).
  - `rag` → GitHub releases API (upgrade check in `/rag-setup` branch C).
  - `remotion` → edge-tts voices (one-shot per narration).

## Safety discipline

Every destructive step has a typed confirmation gate:

| Action class | Gate |
|---|---|
| Kill a process | User types the actual PID number |
| Delete a file | Type `DELETE` verbatim |
| Delete a data directory | Type `DELETE` twice |
| Delete entire plugin state | Type `DELETE` three times |
| Reindex a project | Type `DELETE` + confirm-token programmatically matches project ID |
| Move a stray file | Typed `yes` + `.bak` backup of target |
| Modify `.mcp.json` | `yes` after seeing diff |

Never `yes/no` for destructive ops. Never auto-accept. Never bypass.

## Commit and push discipline

- **Permission-first.** Never push without explicit user approval.
- **Account switching.** `taqat-techno/*` repos use the `a-lakosha` gh identity; switch back to `ahmed-lakosha` after.
- **Co-authored-by Claude** footer when the commit is AI-assisted. Matches the repo's established footer pattern.
- **Two-line commit summary** minimum: what changed and why.

## See also

- [`devops-plugin/ARCHITECTURE.md`](../../devops-plugin/ARCHITECTURE.md) — original layer-ownership codification
- [`rag-plugin/ARCHITECTURE.md`](../../rag-plugin/ARCHITECTURE.md) — current exemplar including state-detection + MCP envelope layers
- [`rag-plugin/docs/decisions.md`](../../rag-plugin/docs/decisions.md) — D-001..D-022 binding decisions (largest example in the repo)
- [`HOOK_STABILIZATION_REPORT.md`](../../HOOK_STABILIZATION_REPORT.md) — hook patterns learned from incidents
- [[Plugin Development Guide|Plugin-Development-Guide]] — how to apply these patterns when authoring
