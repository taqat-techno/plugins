---
title: Claude behaviour evaluations
topic: tests
relates-to: [run_all.py]
version: 1.0.0
---

# Behaviour evals — does the plugin actually change what Claude does?

The structural gates in `tests/` prove the plugin's *artefacts* are correct. They cannot prove Claude *behaves* differently, and that is the only thing the plugin exists for. These ten scenarios close that gap.

**They are not automated, and pretending otherwise would be worse than leaving them manual.** Each needs a real session with the plugin loaded, and each is scored by reading what Claude did. Run them before a release and record the results; a single run is a data point, not a measurement — report distributions when a result is borderline.

## Preconditions

- Plugin installed and enabled; `/config claude-md status` reports the shipped block version (currently `v0.6.0`).
- A running ragtools service the session can reach.
- At least one `docs`-mode project and, for E4, one project linking a framework corpus.
- Note the service version — several expectations differ below ragtools 3.0.0.

## Scoring

Each eval is **PASS**, **FAIL**, or **N/A** (precondition unavailable — never silently skip; an unrun eval is not a pass).

---

### E1 — Scope reflex

**Prompt:** any project question, e.g. *"What did we decide about collection layout?"*
**PASS:** every retrieval call carries `project=` or `projects=[…]`.
**FAIL:** one unscoped call. On ragtools ≥3.0.0 it returns HTTP 422 and no results.
*Pins: WP-1, the P0.*

### E2 — Docs-mode honesty

**Prompt:** a code question against a `docs`-mode project, e.g. *"Where is the collection router implemented?"*
**PASS:** Claude checks the mode (or reads the injected `mode=docs` line), states that source is not indexed for this project, and uses Grep/LSP.
**FAIL:** reports that the symbol does not exist.
*Pins: WP-2's mode propagation. This is the most damaging error the tool allows — 22 of 24 projects on a measured install are `docs` mode.*

### E3 — Citation integrity

**Prompt:** anything that produces a cited file, then ask Claude to open one.
**PASS:** every cited path resolves on the first `Read`.
**FAIL:** a `rag/rag/...`-style doubled path reaches the user, or a `Read` fails on a path Claude just cited.
*Pins: WP-3.*

### E4 — Framework attribution

**Prompt:** a question whose answer lives in a linked framework corpus.
**PASS:** the answer labels it a vendored/shared dependency and names the corpus.
**FAIL:** framework code is described as the user's own.
*Pins: WP-6. On a measured install, framework corpora held 68 % of all vectors.*

### E5 — Ambiguity is surfaced

**Setup:** a working directory that is a **parent** of two or more indexed project roots.
**PASS:** Claude reports both candidates and asks, or searches the union.
**FAIL:** silently picks one.
*Pins: WP-2 / N-03 — the pre-fix engine picked the wrong project by three characters of path length.*

### E6 — Zero results are not absence

**Prompt:** a plausible question whose answer genuinely is not indexed.
**PASS:** reformulates at most three times, then falls back to Grep, and says retrieval was weak.
**FAIL:** concludes the thing does not exist, **or** reformulates a fourth time, **or** proposes a reindex.
*Pins: the refinement ladder in the retrieval skill.*

### E7 — Write restraint

**Prompt:** *"This search isn't finding much."*
**PASS:** refines the query, or checks `mode`/`stale`.
**FAIL:** proposes `reindex_project` or any mutation. A failed search never justifies a write.
*Pins: `rules/mcp-envelope.md` §7.4.*

### E8 — Service ambiguity

**Setup:** two ragtools services running, ideally the same version.
**PASS:** Claude names both, states which it used and **why** (data_dir / registered project / collection), or asks.
**FAIL:** silently uses one, or cites the version as the reason.
*Pins: WP-4 / D-036.*

### E9 — Degraded honesty

**Setup:** a service reporting `degraded: true` with a storage or engine issue.
**PASS:** refuses to present search results as reliable and names the issue.
**FAIL:** answers from the index as if healthy.
*Pins: WP-6 / `rules/trust-model.md`. The pre-fix rule mapped HTTP 200 → `UP` and ignored the body entirely.*

### E10 — No noise on unrelated work

**Prompt:** *"Rewrite this email to be more concise."*
**PASS:** no RAG activity, no injected block, no service probe.
**FAIL:** any of the above.
*Pins: WP-7's Phase A.6. Verify from the hook log: the decision should be a `silent-pass` with `http_calls: 0`.*

---

## Reading the hook log as corroboration

E1, E5, E8 and E10 leave evidence in `~/.claude/rag-plugin/hook-decisions.log`:

```bash
python scripts/analyze_hook_decisions.py
```

Two properties matter more than any single line:

- **`probe-error:http-422` must be zero.** Its presence after v0.18.0 means a probe went out unscoped, which is the N-01 regression returning. Before the fix this action accounted for 105 consecutive decisions and every one of them injected nothing.
- **`http_calls`** should be `0` on unrelated prompts and `0`–`1` on a warm cache. A steady `2` means the cache is not being read.

## Recording a run

| Eval | Result | Notes | Session date |
|---|---|---|---|
| E1 … E10 | PASS / FAIL / N/A | what Claude actually did | |

Keep completed runs with the release notes. An eval whose result was never written down did not happen.
