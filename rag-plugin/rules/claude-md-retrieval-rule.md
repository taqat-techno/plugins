---
title: CLAUDE.md Retrieval Rule
topic: rules
version: 0.4.0
target: ~/.claude/CLAUDE.md (user-level) or project-level CLAUDE.md
purpose: Teach Claude to use the ragtools MCP as project memory/reference and to route each question to the source that owns its truth — RAG for internal history/decisions, code/runtime for implementation behavior, official docs/web for current external facts.
managed-by: /config claude-md install
---

# CLAUDE.md Retrieval Rule

This file is the **single source of truth** for the instruction block that tells Claude to use the ragtools MCP server as a knowledge base. It is injected into the user's `~/.claude/CLAUDE.md` (or a project-level CLAUDE.md) by `/config claude-md install` and kept in sync by `/setup`, `/doctor`, and `/rag-repair`.

## How it is managed

The block is delimited by two machine-readable markers:

```
<!-- rag-plugin:retrieval-rule:begin v=0.4.0 -->
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
<!-- rag-plugin:retrieval-rule:begin v=0.4.0 -->
### 0. Knowledge Base Retrieval (ragtools MCP)

**If a `ragtools` MCP server is loaded in this session** (check for tools named `mcp__plugin_rag_ragtools__*` or `mcp__*__ragtools__*`), treat it as a **local knowledge base of my own docs, notes, decisions, and a snapshot of my code** — authoritative for *internal history and intent*, but a **point-in-time snapshot** that can lag the live code, the current product, and the current web. It is **one source, not the final word.**

**Hard rule: before answering "I don't have information about X" on any question about my own projects, processes, decisions, requirements, conventions, or prior research, call `search_knowledge_base(query=...)` first.** Claiming ignorance of an *internal* matter without searching is a retrieval failure.

The MCP server is proxy-mode forwarded to a running local service at `127.0.0.1:21420`, so searches are cheap (milliseconds, no encoder cold-start) and never exfiltrate data.

**Route by source of truth — match the question to where the real answer lives, not just "is it in my workspace?":**

| Question is about... | Source of truth | First move |
|---|---|---|
| Internal SOP / process / decision / convention / client requirement / project wiki / prior research ("how do we / where did we decide / what's our convention") | the **knowledge base** | `search_knowledge_base` first, then answer |
| **How the code or app actually behaves** ("what does this do", "is X implemented", "why does it break") | the **live code, runtime, tests** | Read the source / run it / run the test. A KB code hit is a snapshot — confirm against the current repo before relying on it. |
| **Current vendor / product / API / SDK / CLI / pricing / limits / security** | **official docs / the web** | Verify before stating (context7 for libraries/SDKs, WebFetch / web search otherwise). Training memory AND the KB can both be stale here. |
| Public knowledge, general programming, math | model knowledge | Answer directly; reach for docs/web if version-sensitive or unsure. |
| The ragtools product itself (install, diagnose, repair) | the `ragtools-ops` skill + `/rag-*` commands | Use those, not `search_knowledge_base`. |

**Answering discipline — calibrate by SOURCE TYPE, not by score alone:**
- A KB hit is "what my notes / code-snapshot said," not automatically "what is true now."
- HIGH (≥0.7) on **internal history / intent / decisions** → ground the answer in it and cite the source file inline.
- HIGH (≥0.7) on **implementation, or vendor / API / pricing / security** → treat it as a *lead*, then confirm against the live code or official docs before committing.
- MODERATE (0.5–0.7), any type → use as context, label "from my notes:", and verify against the owning source (code / runtime / official docs).
- LOW (<0.5) or empty → say "I checked your knowledge base and didn't find information about X," then fall back to code / docs / web as fits the question.
- **If the KB conflicts with the live code or official docs, the code/docs win — surface the conflict explicitly** ("my notes say X, but the current code/docs show Y"). Don't silently pick one.

**Report your source type.** When it isn't obvious, tag each load-bearing claim **[from KB]**, **[from code]**, **[from official docs]**, or **[assumption]**, so the user can calibrate trust and catch stale internal notes.

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
   - If version matches the bundled `0.4.0`, skip (no-op)
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
