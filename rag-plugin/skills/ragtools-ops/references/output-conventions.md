---
title: Output Conventions — Compact-by-Default
topic: output
relates-to: [_meta, INDEX, mcp-wiring, runtime-flow]
source-sections: [§18.7]
---

# Output Conventions

This file documents the **compact-by-default** output discipline that every rag-plugin command, skill, and agent must follow. It is the formal codification of decision **D-008** and the ragtools product's own MCP token-efficiency posture (`risks-and-constraints.md#mcp-token-consumption`).

## The principle

> The ragtools MCP server already cuts context cost by ~60–70% with sentence-boundary truncation and version-suffix dedup. Any plugin that re-formats its outputs in a verbose way undoes that work. **Compact-by-default is not a stylistic preference — it is a budget.**

## Hard rules

### 1. Mode banner first, every time

Every command that touches ragtools state prints a **mode banner** before any other output. The format is fixed at exactly 6 lines:

```
ragtools detected: <packaged-windows | packaged-macos | dev-mode | not-installed>
service mode: <UP (proxy) | DOWN | STARTING | BROKEN | N/A>
binary: <resolved path or "not found">
config:  <resolved path or "not found">
data:    <resolved path or "not found">
logs:    <resolved path or "not found">
```

Rules:
- Always 6 lines. Never expand the banner — extra detail goes in `--verbose`.
- Never invent a path. If something is missing, write `not found` literally.
- Reuse the same probe order (D-004) across every command. The banner is the **single source of truth** for install/runtime state.

### 2. Tables, not paragraphs

For any structured data (status, projects, doctor findings, repair playbook step lists), use markdown tables. Three or more comparable items → table. Two items → bullet list is fine. One item → inline.

| Use a... | When... |
|---|---|
| Markdown table | 3+ rows of comparable data |
| Bullet list | 2 items or non-comparable data |
| Inline value | 1 value |
| Paragraph | Never, except for one-line explanations |

**Bad** (verbose paragraph):
> The ragtools service is currently running on port 21420. There are three projects configured: docs (412 files), notes (89 files), and references (746 files). The watcher is running and watching three paths.

**Good** (compact table):
```
| Field         | Value                          |
|---------------|--------------------------------|
| Service       | UP on 127.0.0.1:21420          |
| Projects      | 3 (3 enabled)                  |
| Files indexed | 1,247                          |
| Watcher       | running, 3 paths               |
```

### 3. Compact-by-default line budgets

Every command has a **default-mode line budget**. Going over the budget requires `--verbose` from the user.

| Command | Default budget | Verbose? |
|---|---|---|
| `/rag-status` | ≤ 25 lines (banner + state table + per-project table + footer) | yes (`--verbose`) |
| `/rag-doctor` | ≤ 25 lines (banner + doctor summary table + findings + next-step) | yes (`--verbose`, `--logs`) |
| `/rag-setup` | conversational; each step ≤ 10 lines | no — the command is interactive |
| `/rag-repair` | one playbook step at a time; each step ≤ 12 lines | no — escalation is by walking, not by verbosity |
| `/rag-projects list` | ≤ 25 lines (banner + table capped at 10 rows + summary) | yes (`--verbose`) |
| `/rag-projects` (writes) | ≤ 15 lines per write op | no — writes are bounded by their nature |
| `/rag-upgrade` | ≤ 20 lines (banner + version diff + changelog highlights) | yes (`--verbose`) |
| `/rag-reset` | ≤ 15 lines (banner + escalation gate + confirmation) | no — destructive ops are tightly bounded |

**Skill (`ragtools-ops`):** loads exactly **one** reference file by default (per INDEX routing rules). Loading more requires the user's question to span multiple topics.

**Agent (`rag-log-scanner`):** returns a single JSON object. No prose. No markdown. The JSON is structured to be small — `findings` array sorted by confidence-then-line, capped at the line budget passed in (default 200).

### 4. `--verbose` is opt-in, never default

When a user passes `--verbose` to a command, the command appends:
- Raw HTTP API responses (collapsed under headings)
- Raw CLI output
- Full `RAG_*` env vars
- Platform info (`uname -a` / `ver`)
- Full log tails (when paired with `--logs`)

These never appear in default mode. The verbose section is **appended after** the compact section, never inside it. The user can stop reading at any time.

### 5. Drill-down on user request

If the compact mode shows `+N more — use --verbose`, that is a contract. The user knows there is more data; they choose whether to ask for it. Never silently truncate without showing the truncation marker.

### 6. Footer recommendations are short

Every command ends with a one-line footer pointing at the next likely action:
```
next: <recommended-action>
```

Examples:
- `service is healthy — nothing to do`
- `start the service: rag service start`
- `walk the playbook: see references/repair-playbooks.md#qdrant-already-accessed`
- `monitor indexing: /rag-status`
- `try a search from Claude Code by asking: "Search my knowledge base for <topic>"`

The footer is **never** more than one line. Never multi-paragraph next-steps. Never "you might also want to...".

### 7. Error output stays compact too

When something fails (HTTP 500, command not found, classification miss), the output is still compact:
- Banner
- One line stating what failed
- One line pointing at the next step (`/rag-doctor`, a playbook anchor, a reference)
- No stack traces in default mode — those go in `--verbose`

### 8. No emoji unless the user asks

Per the user-facing CLAUDE.md preferences for this workspace and the official-plugin convention. The mode banner is plain text. Tables are plain markdown. Status indicators use `✓` / `✗` / `INFO` / `WARN` / `ERROR` keywords, not emoji.

## Why this matters

The ragtools product already applies token-efficient compact mode to the MCP server's `search_knowledge_base` output (`risks-and-constraints.md#mcp-token-consumption`). That cut context consumption by 60–70% versus the verbose mode the admin panel uses.

If the rag-plugin plugin then dumps verbose output for status, doctor, or repair, the user pays both costs:
- The product was efficient on the way in (search results)
- The plugin was wasteful on the way out (operational responses)

Net result: the user's context window fills up with operational chatter and there's less room for actual work. Compact-by-default keeps the budget the product already worked to preserve.

## Boundary

This file describes **how to render** rag-plugin outputs. It does NOT change what gets rendered — the underlying data still comes from the HTTP API, the CLI, or the references. Output discipline is a presentation concern, not a behavior change.

## See also

- `_meta.md` — references library metadata
- `INDEX.md` — routing rules; defaults to one file per query
- `runtime-flow.md` — HTTP API surface (what the data looks like before it's rendered)
- `mcp-wiring.md` — the product's own compact-mode output, which sets the bar
- `risks-and-constraints.md#mcp-token-consumption` — why token efficiency matters
