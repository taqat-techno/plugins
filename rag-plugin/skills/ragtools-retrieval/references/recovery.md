---
title: Retrieval recovery workflows
topic: retrieval
relates-to: [decision-tree, anti-patterns]
---

# Recovery — what to do when retrieval does not work

| Situation | How you know | What to do | Retry? |
|---|---|---|---|
| **Unscoped call refused** | 422 `SCOPE_UNRESOLVED` | You omitted `project=`. Re-issue **with** it. | **Once** — the only auto-retryable error on this surface |
| **Unknown project** | 404 `UNKNOWN_PROJECT` | `list_projects()`. Do not guess a second time. | No |
| **Ambiguous scope** | The injector names 2+ candidates | Name one, or search the union `projects=[…]`, or ask. Never pick silently. | — |
| **No project resolves** | Injector says so, or `list_projects()` lacks a match | Offer `add_project` with a path **the user supplies**. Meanwhile: filesystem. | No |
| **Empty result** | `count: 0` | **Not absence.** Check `mode` first; refine ≤3 times; then Grep. | Query change only |
| **All results LOW** | every score < 0.5 | Add domain nouns; try `find_definition`; then Grep. Say retrieval was weak. | ≤3 |
| **Index rebuilding** | `status: "migrating"`, 409 `MIGRATION_IN_PROGRESS` | Report `done/total`. **Empty ≠ absent** here. Filesystem meanwhile. Do **not** restart — the service resumes on a maintenance tick. | No |
| **Migration blocked** | `migration.blocked` | Report `blocked_reason_recorded` **as history** — the reconciler re-tests every 5 minutes. Escalate only if `stalled`. | No |
| **Storage unreachable** | 503 `STORAGE_UNAVAILABLE` + `Retry-After`; `issues: [storage_unreachable]` | Honour the header. `tail_logs(source="qdrant")` for the cause — **check `qdrant.log.1` too**. | After `Retry-After` |
| **Engine crashed** | `engine.state ∈ {crashed, restarting, restart_exhausted}` | Report pid, exit code, `restart_attempt/max_restarts`. `restart_exhausted` needs a human. | No |
| **Encoder unavailable** | 503 `MODEL_UNAVAILABLE` | Nothing can be embedded. Filesystem only. A rebuild is **CLI-only** — never attempt it via MCP. | No |
| **Index stale** | `project_status.stale`, `state: indexed_stale` | Answer, **verify against the working tree**, and say it was stale. Offer `run_index(project)`. | — |
| **Results contradict the files** | Cited content ≠ file content | **The filesystem wins.** The index is stale for that file. | — |
| **Citation will not resolve** | Strip + existence check both fail | Report project + heading + line span. **Do not invent a repair.** | — |
| **Service down** | `mode: degraded`, `SERVICE_DOWN` | Still available: `tail_logs`, `crash_history`, `get_config`, `get_paths`, `get_ignore_rules`, `list_indexed_paths`. Offer `rag service start`. | No |
| **MCP failed to start** | `STARTUP_FAILED` | Show verbatim — it names the cause. MCP → HTTP → CLI. Mode locks at startup, so recovery means reconnecting Claude Code. | No |
| **Tool not in the registry** | The tool simply is not there | The user opted it out. Name it and the toggle path (admin panel → "MCP Tool Access"). **Never** say the feature does not exist. | No |
| **Permission denied** | 403 `CAPABILITY_DENIED` / `UNAUTHORIZED` | State which capability is needed. **Do not work around it.** | **Never** |
| **Cooldown** | `COOLDOWN` + `retry_after_seconds` | Sleep exactly that long, retry once, then surface. | Once |
| **Two services running** | Discovery reports ambiguity | Compare `data_dir`, `collection`, project count. **Ask.** State the port you used. | — |
| **Embedding model changed** | `MODEL_UNAVAILABLE`, or the map excludes a collection for dimension mismatch | A model change requires a full rebuild — **CLI-only**. | No |

---

## Two rules that override the table

**1. Never let a retrieval failure trigger a mutation.**
Zero results, low confidence, and a stale index are all *read* problems. `reindex_project` is destructive per project and does not change relevance. The only failure a write fixes is staleness, and then the write is `run_index`, after the user asks.

**2. Say which failure it was.**
"I could not find anything" collapses six different situations into one useless sentence. The user's next action differs completely between *docs-mode*, *stale*, *migrating*, *storage down*, *unscoped*, and *genuinely absent*. Name it.

---

## Degraded is not unusable

A `degraded` service is still **the** service. Excluding it would leave the user with nothing to diagnose at exactly the moment they need diagnostics. Use it, and calibrate:

- `storage_unreachable`, `engine_crashed` → search results are **untrustworthy**; do not present them as evidence.
- `watcher_not_running` (undesired) → results are merely **old**; everything since it stopped is missing.
- `watcher` stopped by the user (`desired: "stopped"`) → not a fault. Mention it once.
- `registry_integrity_unresolved` → read-only. Pointer swaps and reaping are already refused server-side.
- `config_migration_failed` → the service is running on fallback defaults, not on what the config says.

Full mapping: `../../rules/trust-model.md`.
