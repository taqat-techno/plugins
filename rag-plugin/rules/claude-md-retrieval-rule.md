---
title: CLAUDE.md Retrieval Rule
topic: rules
version: 0.3.0
target: ~/.claude/CLAUDE.md (user-level) or project-level CLAUDE.md
purpose: Teach Claude to reach for the ragtools MCP before saying "I don't have information" on domain questions.
managed-by: /config claude-md install
---

# CLAUDE.md Retrieval Rule

This file is the **single source of truth** for the instruction block that tells Claude to use the ragtools MCP server as a knowledge base. It is injected into the user's `~/.claude/CLAUDE.md` (or a project-level CLAUDE.md) by `/config claude-md install` and kept in sync by `/setup`, `/doctor`, and `/rag-repair`.

## How it is managed

The block is delimited by two machine-readable markers:

```
<!-- rag-plugin:retrieval-rule:begin v=0.3.0 -->
... content ...
<!-- rag-plugin:retrieval-rule:end -->
```

Commands use these markers to:
- **Detect** whether the rule is already present (grep for the begin marker)
- **Check version** by parsing `v=X.Y.Z` from the begin marker
- **Upgrade** by locating begin→end and replacing the enclosed block
- **Remove** by locating begin→end and deleting the enclosed block (plus the markers themselves, plus any surrounding whitespace run)

**Commands must never edit inside the markers by hand.** Always read this file as the source of truth and splice the whole block.

## The block (verbatim — this is what gets injected)

```
<!-- rag-plugin:retrieval-rule:begin v=0.3.0 -->
### 0. Knowledge Base Retrieval (ragtools MCP)

**If a `ragtools` MCP server is loaded in this session** (check for tools named `mcp__plugin_rag-plugin_ragtools__*` or `mcp__*__ragtools__*`), treat it as a **local knowledge base of my own docs, notes, code, and past decisions**.

**Hard rule: before answering "I don't have information about X" on any domain question, call `search_knowledge_base(query=...)` first.**

The MCP server is proxy-mode forwarded to a running local service at `127.0.0.1:21420`, so searches are cheap (milliseconds, no encoder cold-start) and never exfiltrate data.

**When to call the MCP:**

| Question shape | Action |
|---|---|
| "What is the process for X?" / "How do we handle Y?" | `search_knowledge_base("X process" or "Y handling")` before answering |
| "Where did we decide Z?" / "What's our convention for W?" | `search_knowledge_base("Z decision" or "W convention")` |
| "Is there a playbook / runbook / SOP for …?" | `search_knowledge_base("<topic> playbook")` |
| Any question that sounds like it has an answer in the user's own notes/docs/code and isn't in this turn's context | **Search first, then answer** |
| Question is clearly about public knowledge, general programming, or a library not in my workspace | Answer directly (no MCP call) |
| Question is about the **ragtools product itself** (install, diagnose, repair) | Use the `ragtools-ops` skill + `/rag-*` commands, not the MCP |

**Answering discipline:**
- If MCP returns HIGH-confidence (≥0.7) results → ground the answer in them and cite source files inline.
- If MCP returns MODERATE (0.5–0.7) results → use as context, label as "from my notes:" and suggest the user verify.
- If MCP returns LOW (<0.5) or empty results → then (and only then) say "I checked your knowledge base and didn't find information about X."
- Never say "I don't have information" for a domain question without first running a search — that's a retrieval failure, not an honest answer.

**Do NOT call the MCP for:**
- Questions about current context / recent messages (that's not retrieval).
- Questions about the ragtools product's own operations (use `/rag-status`, `/doctor`, etc.).
- Trivia, general programming questions, math, etc.

### 0a. Override: Operational / Inspection Questions Skip the MCP

This rule **overrides Section 0** for a specific class of questions. The retrieval-reminder hook fires on phrase similarity and cannot tell knowledge questions from operational ones — you must.

**Skip `search_knowledge_base` and the hook reminder when the question is about the user's own machine state**, including:

- "How do I start / stop / restart X?" (X is something installed locally)
- "Where is Y on my disk / in WSL / in this folder?"
- "What's running / listening / scheduled?"
- "Is Z installed? What version?"
- "Why is this process / service failing?"
- "Fix this on my system" / "set up auto-start" / "wire up systemd"
- Anything answerable by `ls`, `which`, `--help`, `Get-Process`, `Get-ScheduledTask`, `wsl -- ...`, reading a config file, or inspecting a folder

For these questions the **filesystem, processes, and tool `--help` output are the source of truth**, not the user's notes. Inspect first; only fall back to the MCP if the artifact isn't found and the question converts into "what did we decide" or "how do we usually do this".

If the retrieval-reminder hook fires on one of these prompts, treat it as a false positive and proceed with inspection. (rag-plugin v0.4.0 hook also classifies operational intent server-side and silent-passes — but the override here is the canonical rule.)

_Managed by rag-plugin. To update, run `/config claude-md install`. To remove, run `/config claude-md remove`._
<!-- rag-plugin:retrieval-rule:end -->
```

## Injection logic

Commands that install this block must follow these steps:

1. **Read the target file** (`~/.claude/CLAUDE.md` for user-level, `<cwd>/CLAUDE.md` for project-level).
2. **If the file does not exist**, create it with just this block + a trailing newline.
3. **If the file exists and already contains `<!-- rag-plugin:retrieval-rule:begin`**:
   - Parse the version from the begin marker
   - If version matches the bundled `0.3.0`, skip (no-op)
   - If version differs, locate the full begin→end range and replace with the new block
4. **If the file exists and does not contain the marker**:
   - Append a blank line + the block + a trailing newline
5. **Never use string-replace on the rule content itself** — always splice by markers.
6. **Show a diff summary** to the user before writing (lines added / removed / unchanged).
7. **Ask for confirmation** unless the command was invoked with `--yes` or from inside `/setup`'s first-install branch.

## Why this exists

The previous turn's incident: a user asked *"What is the process for emergency assistance requests?"*. The ragtools MCP was loaded and the answer was in `tq-workspace/planing/Alaqraboon/_Emergency_Assistance_Procedure_en.md` at confidence 0.80. But Claude never called `search_knowledge_base` — it scanned CLAUDE.md, memory, and recent messages, found nothing, and said *"I don't have information about an 'emergency assistance request' process"*.

The failure wasn't in the MCP. The failure was that **nothing told Claude when to reach for the MCP**. The MCP tool description said what the tool does (`"Search the local Markdown knowledge base"`), not when to use it. This rule fixes that by putting a workflow-level instruction in CLAUDE.md itself, which loads at the start of every session.

## See also

- `../ARCHITECTURE.md` — layer diagram including the new rules/ directory
- `../docs/decisions.md#d-016` — the binding decision behind this rule
- `../commands/rag-config.md` — the command that installs / upgrades / removes it
- `../commands/rag-setup.md` — the command that installs it as part of first-time setup
- `../commands/rag-doctor.md` — surfaces presence/version in the diagnostic table
