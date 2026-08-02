---
name: ragtools-retrieval
description: Use when searching a local ragtools knowledge base for project code or documentation — "where is X implemented", "what did we decide about Y", "find the definition of Z", "search my notes / docs / codebase", "how does this module work", "why isn't this file indexed", or when a ragtools search returned nothing, low-confidence, or conflicting results. Covers scope resolution (searches are refused without a project), docs-vs-code mode, query construction and refinement, framework/shared-dependency routing, citation-path validation, confidence and verification, and recovery when the index is stale, migrating, or degraded.
version: 1.0.0
last_reviewed: 2026-08-02
---

# ragtools-retrieval

Guidance for **using** the ragtools knowledge base well. This skill never calls a retrieval tool — Claude does that directly. The skill tells Claude *when*, *how*, and *how much to trust the answer*.

> **Boundary (D-001 / D-032 §1 / D-034).** The plugin never calls, wraps, mediates, or reformats `search_knowledge_base`, `search_project_context`, or `find_definition`. Guidance is not invocation. If you find yourself writing a workflow that *performs* a search on the user's behalf, stop — that is the line.

---

## The two facts that cause most failures

**1. Every search is scoped, or it fails.**

ragtools ≥3.0.0 refuses an unscoped retrieval call:

```
HTTP 422  {"error_code": "SCOPE_UNRESOLVED",
           "error": "no project scope resolved; refusing to search globally."}
```

`search_knowledge_base` and `search_project_context` **both** require `project="<id>"` or `projects=["a","b"]`. Get ids from `list_projects()` — never guess one; an unknown id is a hard **404 `UNKNOWN_PROJECT`**, because the collection router refuses to fall back to a shared collection rather than read another project's data.

`find_definition` and `secret_audit` are the exceptions: they accept an unscoped call and will span **every project and every framework corpus**. Scope them anyway, for relevance.

**2. Most projects index no code.**

`project_status(project=<id>)` returns `mode`:

| mode | What is indexed |
|---|---|
| **`docs`** (the default) | documentation / Markdown / text **only** |
| `code` | source + config only |
| `general` | both |

On a measured install, **22 of 24 projects were `docs`**. In `docs` mode an empty `find_definition` or `search_project_context` result means **nothing at all** — it is the expected outcome, not evidence the symbol is absent. Saying "that does not exist" there is the single most damaging error available with this tool.

---

## Before the first search

```
1. list_projects()                 → valid ids (once per session)
2. project_status(project=<id>)    → mode · state · stale · path_exists
3. index_status()                  → is the KB up at all
```

The plugin's context injector usually supplies steps 1–2 for the current directory, so read the injected `RAG scope:` line before spending calls on them.

**Gates from step 2:**

- `mode == "docs"` and the question is about code → **say so and use Grep/LSP.** Do not search for code.
- `state == "indexed_stale"` → answer, then verify against the working tree, and **say it was stale**.
- `path_exists == false` → the index describes a folder that is gone. Stop and report it.

---

## Routing

| The question is about… | Call | Then |
|---|---|---|
| A decision, convention, SOP, requirement, prior research | `search_knowledge_base(query, project, structured=True)` | cite file + heading |
| Where code lives / what patterns exist / how a subsystem works | `search_project_context(query, project)` | **Read every cited file** |
| Where a symbol is defined | `find_definition(symbol, project)` | Read the `file:line`, then Grep/LSP to confirm |
| **All references / rename safety / call sites** | **Grep or LSP** | — the code graph is definitions-only, v1 |
| An exact string or error message | **Grep** | — there is no lexical mode, see below |
| What a project contains | `project_summary(project)` | — |
| Whether a file got indexed | `list_project_files(project)` | — |
| Framework / vendored code | `list_dependencies()` → search the **linking project** | read `scope_source` |
| Whether anything secret is indexed | `secret_audit(project)` | leads only — confirm in the file |
| Git history | **`git log` / `git blame`** | — not indexed |

**Semantic-only.** There is no BM25, no hybrid search, no reranking model. Consequences: an exact identifier or error string is better found with Grep; scores are not comparable across queries; and a file the semantic search never surfaced cannot be rescued by a category bonus.

---

## Reading the answer

| Signal | Meaning |
|---|---|
| `HIGH ≥0.7` | Ground the answer. Still Read before editing. |
| `MODERATE 0.5–0.7` | Label it "from the knowledge base"; verify against the owning source. |
| `LOW <0.5` | A lead. Say retrieval was weak. |
| **empty** | **Never absence.** Check `mode` first, then Grep. |
| `scope: "framework"` | Vendored dependency — never describe it as the user's code. |
| `source_class` ≠ `owned` | Vendored/generated; already down-ranked by the reranker. |

**Citations need care.** Prefer `structured=True`: its `file_path` is correct. Default text output repeats the project id as the first segment — `rag/rag/docs/x.md` for `rag/docs/x.md`. Strip **one** duplicate, verify the file exists, and never show the doubled form. Full rule: `rules/mcp-envelope.md` §6.

**Conflicts.** When the knowledge base disagrees with live code or official docs, the code/docs win — and say so explicitly rather than silently picking one (D-029).

---

## Refining a weak query — bounded at 3 attempts

```
1. All LOW?      add domain nouns (project_summary's top files are a vocabulary source)
2. Still weak?   rephrase what-it-does -> what-it-is-called; then find_definition
3. Zero results? CHECK project_status.mode FIRST. docs -> stop, this is expected.
4. Wrong files?  raise top_k 10 -> 20 (cheap; there is no cross-chunk dedup, so one
                 file can occupy several slots)
5. After 3 reformulations -> Grep. Say retrieval was weak. Do not try a fourth.
```

**A failed search never justifies a mutation.** Reindexing does not change relevance. Zero results is a query problem or a `mode` problem.

---

## Reference files

Load the smallest set that answers the question — usually one.

| Concern | Load |
|---|---|
| Full decision tree, per-intent workflows | `references/decision-tree.md` |
| Effective query shapes per intent, worked examples | `references/query-patterns.md` |
| What not to do, and why each one bites | `references/anti-patterns.md` |
| Framework corpora, shared dependencies, provenance | `references/frameworks.md` |
| Empty / stale / migrating / degraded / ambiguous / permission-denied | `references/recovery.md` |
| What each `/health` issue means for trust | `../../rules/trust-model.md` |
| Tool inventory, envelope, error codes, cooldowns | `../../rules/mcp-envelope.md` |

---

## Presenting evidence

Every load-bearing claim carries: project · validated path · line span · `scope` (project vs framework) · source tag — `[from KB]` / `[from code]` / `[from official docs]` / `[assumption]` — and the freshness caveat when the project was stale.

## See also

- `../../rules/claude-md-retrieval-rule.md` — the always-loaded contract this skill deepens
- `../ragtools-ops/SKILL.md` — operating the product (install, diagnose, repair); a different job
- `../../docs/decisions.md` — D-001, D-029, D-032, D-034
