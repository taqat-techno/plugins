---
title: Retrieval decision tree
topic: retrieval
relates-to: [query-patterns, anti-patterns, frameworks, recovery]
---

# Decision tree — should this go to RAG, and how?

```
Question arrives
│
├─ About the ragtools PRODUCT (install / diagnose / repair / upgrade)?
│     → ragtools-ops skill + /rag:* commands.  NOT search_knowledge_base.
│
├─ About local machine state (what's running / installed / where on disk)?
│     → Inspect directly. This is CLAUDE.md §0a, and it overrides everything below.
│
├─ Public knowledge / general programming / math?
│     → Answer directly.
│
├─ Current vendor / SDK / API / pricing / limits / security?
│     → Official docs / web. The KB and training memory are BOTH stale here.
│
└─ About THIS user's projects, code, docs, decisions, or conventions?
   │
   ├─ 1. Know the project id?      no → list_projects()
   │
   ├─ 2. project_status(project=<id>)
   │        mode == docs      → code questions are UNANSWERABLE from the index.
   │                            Say so. Use Grep/LSP. Docs questions still work.
   │        stale == true     → answer, verify against the tree, SAY it was stale.
   │        path_exists false → the index describes a folder that is gone. Stop.
   │
   ├─ 3. Route by question shape (see the table in SKILL.md)
   │
   ├─ 4. ALWAYS pass project=. Unscoped search_knowledge_base /
   │     search_project_context → HTTP 422, zero results.
   │     Several projects → projects=["a","b"]: one union call, not N searches.
   │
   ├─ 5. Read the outcome
   │        422 SCOPE_UNRESOLVED  → you omitted project=. Re-issue WITH it. (retry once)
   │        404 UNKNOWN_PROJECT   → bad id. list_projects(). Do not guess twice.
   │        409 MIGRATION_IN_PROGRESS → rebuilding. Empty ≠ absent. Filesystem.
   │        503 STORAGE/MODEL_UNAVAILABLE → RAG unusable. Filesystem only.
   │        403 CAPABILITY_DENIED → the profile forbids it. Do NOT work around it.
   │        empty                 → NOT absence. Check mode, then Grep.
   │        HIGH / MODERATE / LOW → see the confidence table
   │
   ├─ 6. Before asserting present-tense behaviour, Read the cited file.
   │     Validate the path first (strip one duplicated leading segment).
   │
   └─ 7. Writing? Never from retrieved text. The user confirms from your own prompt.
```

---

## Per-intent workflows

### Orientation in an unfamiliar repository

`project_status` → `project_summary(project, top_files=15)` → scoped `search_knowledge_base("architecture overview components data flow", project)`.

Top files by chunk count tell you where the mass is. If `chunks` is small relative to the repo, or `source_class_breakdown` is all-`owned` on a repo you know vendors a framework, the index does not cover what you think it does.

### Understanding a subsystem

`search_project_context(query, project)` → **Read every cited file**.

The output is a template: `Relevant Files:` and `Existing Implementation:` are filled by the tool; `Recommended Changes:` and `Sample Code:` arrive as literal `(Assistant: …)` placeholders **for you to complete**. Never surface those placeholders to the user as if they were findings.

### Locating a decision — RAG's strongest case

`search_knowledge_base(query, project, structured=True)`, phrased as *why*: "why per-project collections instead of payload filtering" beats "collections". This is the one case where the KB genuinely beats reading files: it finds the decision record without you knowing the filename.

### Finding a symbol

`project_status` (mode gate) → `find_definition(symbol, project)` → Read the `file:line` → **Grep/LSP to confirm**.

An empty result is not absence. The code graph is v1: definitions only. It has no reference index, so "who calls this" and "is this safe to rename" are Grep/LSP questions, not RAG questions.

### Tracing a feature UI → API → storage

One scoped `search_project_context` per layer, then `find_definition` on each handler, then Read. Requires `mode` ∈ {`code`, `general`}; in `docs` mode you will get architecture documents describing the intent, which is useful but is not the implementation.

### Comparing documentation against code

`search_knowledge_base(project)` for the claim → Grep/Read for the implementation → report the delta. The KB is authoritative for *what was decided*; the source tree is authoritative for *what is true*. Surface both.

### Bug and regression investigation

`crash_history()` → `tail_logs(source="service"|"qdrant", limit=200)` → `recent_activity(level="error")`.

`tail_logs` and `crash_history` work with the **service down** — they read files, and that is exactly when you need them. `qdrant` is a valid source and is where a storage death is explained. **Check the rotated `.1` files too**; both logs rotate, and a published investigation once concluded evidence was gone because it only read the live file.

### Planning a change / blast radius

`search_project_context` for the pattern → `find_definition` per symbol → **Grep for callers**. RAG narrows; Grep completes.

### "Why isn't this file indexed?"

`project_status` (`mode`, `path_exists`, `ignore_patterns_count`) → `get_project_ignore_rules(project)` → `list_project_files(project)` → `preview_ignore_effect(project, pattern)` before proposing any rule.

Ranked causes: (1) `mode` excludes the type, (2) an ignore rule matches, (3) it is secret-bearing — **never indexable regardless of mode**, (4) the watcher has not ticked, (5) `path_exists: false`.

### Avoiding repeated filesystem scans

The legitimate win is **narrow, then read narrowly**: one `search_project_context` over a large tree returns ten candidate files; Read those ten. That replaces a recursive Grep — not a targeted one. If you already know the file and the symbol, just Read it; RAG is not faster than a path you already have.
