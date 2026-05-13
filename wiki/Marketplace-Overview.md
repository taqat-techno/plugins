# Marketplace Overview

## What a Claude Code marketplace is

A Claude Code marketplace is a Git repository that ships one or more **plugins**. Users add the marketplace URL in Claude Code (`/plugins` → **Add Marketplace** → enter URL), Claude Code clones it into `~/.claude/plugins/cache/<marketplace-name>/`, and exposes every plugin's commands, agents, skills, hooks, and MCP servers to the running session.

This repo is the **taqat-techno-plugins** marketplace — 7 plugins targeting real operational workflows at TAQAT Techno.

Some plugins are operator consoles for external products. The `rag` plugin, in particular, is the operations console for the upstream **[ragtools](https://github.com/taqat-techno/rag)** application — installers, product source, CHANGELOG, and release history all live in that separate repo. See [[Rag Plugin|Rag-Plugin]] for the relationship and cross-links.

## Repository layout

```
plugins/                              ← the working marketplace (what you edit)
├── .claude-plugin/
│   └── marketplace.json             ← single source of truth for the plugin list
├── odoo-plugin/
├── devops-plugin/
├── rag-plugin/
├── paper-plugin/
├── pandoc-plugin/
├── remotion-plugin/
├── ntfy-plugin/
├── wiki/                            ← this wiki (source files, synced to GitHub Wiki)
├── CLAUDE_CODE_PLUGIN_DEVELOPMENT_GUIDE.md
├── agent_skills_spec.md
├── CONTRIBUTING.md
├── validate_plugin.py
├── validate_plugin_simple.py
├── README.md                        ← marketplace-level overview
└── LICENSE

claude-plugins-official/         ← READ-ONLY vendored reference from Anthropic
                                     ← Never modify. Consult for canonical patterns only.
```

A second directory, `claude-plugins-official/`, is a vendored read-only copy of Anthropic's official marketplace. It exists purely as a reference library for canonical patterns (hook JSON shape, MCP config, skill frontmatter, etc.). Project-level settings actively deny `Edit`/`Write`/`NotebookEdit` operations against it — copy patterns into `plugins/<your-plugin>/` instead.

## Plugin registration

Every plugin must be registered in `plugins/.claude-plugin/marketplace.json`:

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "taqat-techno-plugins",
  "description": "...",
  "owner": {"name": "TAQAT Techno", "email": "info@taqatechno.com"},
  "plugins": [
    {
      "name": "rag",
      "description": "...",
      "author": {"name": "TaqaTechno", "email": "info@taqatechno.com"},
      "source": "./rag-plugin",
      "category": "productivity",
      "homepage": "https://github.com/taqat-techno/plugins/tree/main/rag-plugin"
    },
    ...
  ]
}
```

Adding a plugin directory without a corresponding `marketplace.json` entry makes it invisible — Claude Code never loads it. The `validate_plugin.py` script does **not** catch this; it validates one plugin at a time against its own manifest, not against the marketplace.

## Plugin structure (standard layout)

Not every plugin uses every directory, but the shape is stable:

```
<plugin-name>/
├── .claude-plugin/
│   └── plugin.json                  ← manifest: name, version, description, author, license, keywords
├── commands/                        ← /slash commands (markdown with YAML frontmatter)
│   └── <name>.md
├── agents/                          ← sub-agent definitions (markdown)
│   └── <name>.md
├── skills/                          ← SKILL.md files + references, examples, scripts
│   └── <skill-name>/
│       ├── SKILL.md
│       ├── references/              ← long-form companion docs loaded on demand
│       ├── examples/
│       └── scripts/
├── hooks/                           ← PreToolUse / PostToolUse / UserPromptSubmit / SessionStart hooks
│   ├── hooks.json
│   └── <script>.py / <script>.sh
├── rules/                           ← behavioral contracts referenced by skills/agents/commands
├── data/                            ← JSON/MD state machines, templates (devops-plugin, odoo-plugin)
├── templates/
├── tests/
├── .mcp.json                        ← plugin-level MCP server registration (flat shape)
├── ARCHITECTURE.md                  ← layer diagram + forbidden list (rag-plugin, devops-plugin)
├── CHANGELOG.md                     ← per-version release notes (mature plugins)
├── LICENSE / LICENSE.md / LICENSES.md
└── README.md                        ← plugin landing doc
```

### Which plugins use which directories

| Plugin | commands | agents | skills | hooks | .mcp.json | rules | data | templates |
|---|---|---|---|---|---|---|---|---|
| odoo | ✓ (17) | ✓ (4) | ✓ (8 sub-skills) | ✓ | — | ✓ | ✓ | ✓ |
| devops | ✓ (9) | ✓ (3) | — | ✓ | ✓ | ✓ | ✓ | — |
| rag | ✓ (6) | ✓ (1) | ✓ (1) | ✓ | ✓ | ✓ | — | — |
| paper | ✓ (1) | ✓ (2) | ✓ (2) | ✓ | — | — | — | — |
| pandoc | ✓ (1) | — | — | ✓ | — | — | — | — |
| remotion | ✓ (1) | — | — | ✓ | — | — | — | ✓ |
| ntfy | ✓ (2) | — | — | ✓ | — | — | — | — |

## House engineering conventions

Distilled from the repo's history, three audit reports (`HOOK_AUDIT_REPORT.md`, `HOOK_STABILIZATION_REPORT.md`, `PLUGIN_ENHANCEMENT_REPORT_FEB_2026.md`), and the binding-decisions logs of mature plugins:

1. **Consolidate aggressively.** Every mature plugin has gone through at least one "N narrow commands → 1 smart command" pass. `pandoc` (8→1), `paper` (5→1), `ntfy` (8→2), `remotion` (5→1), `devops` (24→9), and 8 Odoo plugins merged into one `odoo-plugin` with sub-skills. Sprawl is a regression.
2. **Commands are thin dispatchers.** Behavior lives in skills, rules, agents, and data files. Commands route to those layers and expose flags.
3. **Single-owner layering.** Each concern lives in exactly one file. If two files have the same logic, one of them is wrong. Documented in `rag-plugin/ARCHITECTURE.md` and `devops-plugin/ARCHITECTURE.md`.
4. **Hooks enforce, they don't reason.** Hooks are command-type bash/python, fail fast, return structured JSON. No prompt-type hooks (they trigger Claude Code's prompt-injection detection). Minimal SessionStart output.
5. **Binding decisions (D-NNN).** Load-bearing choices go into `docs/decisions.md` with date, status, rationale, and a "Reverse only if:" exit clause. Supersede with new dated entries; never rewrite earlier ones.
6. **Validator discipline.** `python validate_plugin.py <plugin-dir>` runs before commits. Documented false positives live in CHANGELOGs, not silenced.
7. **Cross-platform parity.** Windows is the primary dev environment, but every command has macOS and Linux branches. `os.execvp` stdio semantics, `cp1252` codec, CRLF vs LF, `where` vs `which`, `%LOCALAPPDATA%` are first-class concerns.
8. **Local-first posture.** No network egress unless explicit and opt-in. Telemetry is local-only JSONL; the user can always `cat` it. No plugin phones home.
9. **Typed confirmation for every destructive step.** `DELETE` / actual PID / project ID verbatim — never `yes/no` for destruction.
10. **Permission-first for pushes.** `taqat-techno/*` repos use the `a-lakosha` gh account; push is always on explicit user approval, then account switches back.

## Documentation discipline

- **Marketplace README** is manually maintained — when plugins are added/removed/renamed, update `plugins/README.md` in the same commit. Stale READMEs with broken links have been a recurring regression.
- **Plugin READMEs** follow a minimum contract: H1 title + description paragraph + Quick Start / Installation section + Commands / Components section + license note.
- **Changelogs** exist for the mature plugins (`rag-plugin`, `devops-plugin`, `remotion-plugin`). Not required for all plugins but strongly recommended after the first version bump.
- **ARCHITECTURE.md** in `rag-plugin/` and `devops-plugin/` documents the layer ownership and forbidden-list patterns.

## See also

- [[Plugin Catalog|Plugin-Catalog]] — all 7 plugins at a glance
- [[Plugin Development Guide|Plugin-Development-Guide]] — authoring conventions
- [[Architecture]] — shared layering patterns across plugins
- [[Contribution Guide|Contribution-Guide]] — PR workflow, account switching, permission-first
