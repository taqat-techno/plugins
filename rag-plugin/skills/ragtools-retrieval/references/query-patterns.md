---
title: Query patterns
topic: retrieval
relates-to: [decision-tree, anti-patterns]
---

# Query patterns

The index is **semantic only** — `all-MiniLM-L6-v2`, 384 dimensions, cosine, `score_threshold=0.3`. No BM25, no hybrid, no reranking model. Every pattern below follows from that.

Queries are embedded together with a context header (`language file_name > heading path`), which is why heading vocabulary influences a match even when the user never typed it.

---

## By intent

| Intent | ✅ Effective | ❌ Ineffective | Why |
|---|---|---|---|
| **Broad orientation** | `search_knowledge_base("system architecture components data flow storage", project="rag")` | `"architecture"` | One word matches everything and therefore ranks nothing |
| **Exact symbol** | `find_definition(symbol="CollectionRouter", project="rag")` | `search_knowledge_base("CollectionRouter", project="rag")` | Identifiers embed poorly in prose; `find_definition` matches indexed symbol metadata instead |
| **Natural-language feature** | `search_project_context("how a search request is scoped to one project", project="rag")` | `"scope"` | Describe the behaviour, not the noun |
| **Error message** | **Grep** for `WinError 10048` | semantic search for the literal | No lexical mode — the string competes against every networking chunk |
| **Architecture / decision** | `search_knowledge_base("why per-project collections instead of payload filtering", project="rag")` | `"collections"` | The *why* phrasing lands on decision records |
| **Bug investigation** | `search_project_context("managed engine crashes on startup while the service keeps reporting ready", project="rag")` | `"crash"` | Symptom + subsystem + observed behaviour |
| **Test discovery** | `search_knowledge_base("tests for scope enforcement client profile", project="rag")` **plus** `Glob "tests/**/*scope*"` | either alone | Semantic finds intent; glob finds files |
| **Git history** | `git log -S "<symbol>"` / `git blame` | any RAG call | Not indexed. Nothing in the KB knows about commits |
| **Framework behaviour** | `list_dependencies()` → `search_project_context("record rules on portal requests", project="<linking project>")` | searching the framework id as a project | Corpora are reachable only through a project that links them |
<!-- unscoped-example-ok: the ✗ column is deliberately what NOT to type -->
| **Configuration** | `get_config()` + `get_project_ignore_rules(project)` | `search_knowledge_base("config")` | Config is a tool call, not a search |
| **Release / installer** | `search_knowledge_base("installer upgrade quiescence file in use", project="rag")` | `"installer"` | — |
| **Cross-project** | `search_knowledge_base("authentication flow", projects=["a","b"], structured=True)` | two sequential searches | One union call; `project_id` per hit separates them |

---

## Worked example

Task: *"How does ragtools decide which Qdrant collection to query?"* — run against a real install.

```
1. list_projects()                       → "rag" exists
2. project_status(project="rag")         → mode="docs", state="indexed", stale=false
                                         → GATE: code is NOT indexed for this project
3. search_knowledge_base(
       query="collection router per-project layout decision",
       project="rag", structured=True)   → docs/decisions.md, MODERATE (0.53)
4. Read <project_root>\docs\decisions.md
        (NOT rag/rag/docs/decisions.md — strip the duplicated segment)
5. Grep "class CollectionRouter" src/    → because mode=docs, the code is not indexed
6. Answer: [from KB] the decision record + [from code] collection_router.py
```

Step 2 is what makes step 5 necessary. A Claude that skipped it would run `find_definition`, get nothing, and conclude the router does not exist.

---

## Composing a good query

**Include:** domain nouns from the project's own vocabulary · the subsystem name · what the thing *does* · for decisions, the word *why*.

**Exclude:** single generic words · pronouns · "the code that" · file extensions · anything you would type into Grep.

**Vocabulary source:** `project_summary(project, top_files=15)`. The top files by chunk count tell you what the corpus actually calls things, which is usually not what you called them.

**`top_k`:** default 10. Raise to 20 when the topic is right but the files are wrong — it is cheap, and because there is **no cross-chunk dedup**, one large file can legitimately occupy several slots.

**`structured=True`:** prefer it on `search_knowledge_base`. It is the only surface with a correct `file_path`, a machine-readable `meta.error_code`, and per-result `scope` / `scope_source` / `source_class` / `line_start` / `line_end`. The other three retrieval tools have no structured mode at all.

---

## Multi-query decomposition

Decompose only when the question genuinely spans layers (UI → API → storage), and then issue **one scoped call per layer**.

Do **not** fire several near-synonymous queries at the same project in parallel: the results overlap, there is no dedup, and the context budget pays for each copy. Two phrasings of one question is noise, not recall.
