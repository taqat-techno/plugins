---
title: Frameworks and shared dependencies
topic: retrieval
relates-to: [decision-tree, anti-patterns]
---

# Framework corpora and shared dependencies

## Why this matters more than it looks

On a measured install, three `fw_odoo_*` corpora held **210,215 points — 68 % of every vector on the machine**. Two-thirds of what a search can return belongs to no project at all. A plugin unaware of that will describe a vendored framework's code as the user's own.

## The model

A **shared dependency** is a vendored framework folder declared once in a catalog and *selected* by any number of projects. It is indexed **once** into its own collection (`fw_<slug>_<digest>`), not copied per project.

Consequences you must hold:

- It is **not a project**. It has no entry in `list_projects()`.
- It is reachable **only** by searching a project that links it.
- Its hits arrive tagged `scope: "framework"` with a `scope_source` naming the corpus.
- It requires `collection_strategy = "per_project"`. Under `shared` the whole feature is a no-op.
- It is **not watcher-refreshed**. Framework corpora update on the next `sync_frameworks` — so the largest part of the index has no freshness signal at all.

## Routing

| Question | Route |
|---|---|
| "How does Odoo enforce record rules on portal requests?" | `list_dependencies()` → find the corpus and a linking project → `search_project_context(query, project=<linking project>)` → keep `scope: framework` hits |
| "How does *our* code override that?" | Same project, keep only `scope: project` hits |
| "Is this file ours or vendored?" | Read **both** `scope` and `source_class` — they answer different questions |

## `scope` vs `source_class`

They are orthogonal and both matter:

- **`scope`** — *which collection answered*. `project` = this project's own collection; `framework` = a shared corpus.
- **`source_class`** — *what kind of file it is*: `owned` / `dependency` / `generated` / `secret`. Computed from the path, and it applies **within** a project too. A project that vendors a library without declaring it as a shared dependency will show `source_class: dependency` on `scope: project` hits.

The reranker already penalises non-owned content (`dependency −0.12`, `generated −0.10`, `secret −0.20`), so a vendored hit that still ranks high is genuinely relevant — and a marginal one is noise you should discount rather than cite.

## Provenance in text output vs structured output

The text formatter tags **only framework hits**. An untagged line therefore means *project*, not *unknown* — do not read the absence of a tag as missing information.

Structured mode (`search_knowledge_base(query, project, structured=True)`) carries `scope` and `scope_source` on **every** result. That is another reason to prefer it when provenance matters to the answer.

## Writes

`list_dependencies` is read-only and safe to call. The other three are user-authorised writes:

- `add_dependency(id, path)` — registers a catalog entry. **Indexes nothing on its own**; the corpus is built when the first project links it.
- `set_project_dependencies(project, [ids])` — **REPLACES the entire list.** A partial list silently unlinks everything omitted. Always echo the full resulting list and have the user confirm it.
- `remove_dependency(id, confirm_token, cascade)` — refused while any project still links it unless `cascade`. It affects **every** project that links it, not just the one in front of you.

Linking or unlinking triggers real indexing work: declaring is a three-part move (exclude from the project scan, index into its own collection, purge from the project's), and un-declaring reconciles in reverse. Neither is instant, and neither should be proposed casually.

## What "indexed once" means for an answer

If two projects both link `odoo-18`, a hit from that corpus is the *same bytes* for both. Do not describe it as belonging to whichever project you happened to search — name the corpus via `scope_source`.
