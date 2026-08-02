# Trust model — when may a retrieval result be believed?

**Binding.** Every command and skill that presents retrieved content, and every path that reads `/health`, uses this mapping. Consumes `state.degraded` / `state.issues[]` / `state.project_mode` / `state.project_state` from `rules/state-detection.md`.

The rule this replaces mapped **HTTP 200 → `UP`** and ignored the body. A service answering `200` with `degraded: true, issues: [storage_unreachable, engine_crashed]` was therefore classified healthy, and its search results were presented as reliable.

---

## 1. The trust matrix

| Runtime / index state | How you detect it | Can search? | Can trust results? | Can mutate? | Required response |
|---|---|---|---|---|---|
| **Healthy** | `degraded: false`, `issues: []`, `index_availability: ready` | ✅ | ✅ within the confidence bands | ✅ with consent | Normal operation; still Read cited files before editing |
| **Project is `docs` mode** | `project_status.mode == "docs"` | ✅ docs only | ✅ for docs; **code absence means nothing** | ✅ | State the limitation; Grep/LSP for code |
| **Project stale** | `project_status.stale`, `state: indexed_stale` | ✅ | ⚠️ describes an older tree | ✅ (`run_index` fixes it) | Answer, verify against the tree, **say it was stale** |
| **Collection fresh, project stale** | `/api/status.freshness: fresh` **and** `project_status.stale: true` | ✅ | ⚠️ | ✅ | **Per-project wins.** Never quote collection freshness for one project |
| **Migrating** | `status: "migrating"`; 409; `index_availability: rebuilding` | ❌ refused by design | ❌ | ❌ | Report `done/total/blocked`. **Empty ≠ absent.** Filesystem |
| **Migration blocked** | `migration.blocked` + `blocked_reason_recorded` | ❌ | ❌ | ❌ | The recorded reason is **history**; the reconciler re-tests every 5 min |
| **Storage unreachable** | `storage_reachable: false`; `issues: [storage_unreachable]`; 503 | ❌ | ❌ | ❌ | Filesystem only. `tail_logs(source="qdrant")`, incl. `qdrant.log.1` |
| **Engine crashed / restarting** | `engine.state ∈ {crashed, restarting, restart_exhausted}` | ❌ / ⚠️ | ❌ | ❌ | Report pid + exit code + `restart_attempt`. `restart_exhausted` needs a human |
| **Silently degraded to embedded** | `storage_backend: "embedded"` + non-empty `storage_degraded_reason` | ✅ slow | ✅ | ✅ | Surface the reason — the config says `managed` and the runtime is not |
| **Rebuild interrupted** | `issues: [rebuild_interrupted]`; `recovery` non-null | ⚠️ partial | ⚠️ per project | ❌ | Read `recovery.precondition` (re-tested), not the recorded reason |
| **Registry integrity unresolved** | `registry_integrity ∉ {ok, extended, repointed}` | ✅ | ⚠️ ownership unproven | ❌ swaps/reaping already refused | Report; do not mutate |
| **Watcher down (undesired)** | `issues: [watcher_not_running]`, `watcher.desired == "run"` | ✅ | ⚠️ drifting from now | ✅ | Everything since it stopped is missing; offer `run_index` |
| **Watcher stopped by user** | `watcher.state == "stopped"`, `desired == "stopped"` | ✅ | ⚠️ intentional | ✅ | Not a fault. Mention once |
| **Config migration failed** | `issues: [config_migration_failed]` | ⚠️ | ⚠️ running on fallback defaults | ❌ | Route to `rag upgrade` |
| **Service down (MCP direct)** | envelope `mode: "degraded"`; `SERVICE_DOWN` | ✅ core retrieval only | ✅ | ❌ | Only the filesystem-fallback diagnostics work |
| **MCP startup failed** | `STARTUP_FAILED` | ❌ | ❌ | ❌ | Show verbatim; HTTP → CLI |
| **Points 0, state DB non-zero** | collection `points: 0` with `historical_chunks > 0` | ❌ | ❌ | ❌ | **Data loss or an unfinished rebuild.** Never report "0 chunks" as fact |
| **Count unavailable** | `points_count: null` | ⚠️ | — | ❌ | Render "unknown". **Never 0** |

---

## 2. The `/health.issues` vocabulary

The complete set, and what each one costs you:

| Issue | Search still works? | What it means for trust |
|---|---|---|
| `watcher_not_running` | yes | Results are **old**, not wrong |
| `storage_unreachable` | no | Nothing can be trusted |
| `engine_crashed` | no | Nothing can be trusted |
| `engine_restarting` | intermittently | Wait; do not conclude from an empty result |
| `engine_restart_exhausted` | no | Needs a human |
| `engine_log_unavailable` | yes | Diagnostics are degraded, retrieval is not |
| `rebuild_interrupted` | partially | Per-project; check `recovery` |
| `recovery_unresolved` | partially | A plan is being re-driven |
| `registry_integrity_unresolved` | yes | Collections hold vectors but ownership is unproven |
| `config_migration_failed` | yes | Running on fallback defaults, not the config file |
| `reindex_in_progress` | **refused** | Empty ≠ absent |
| `reindex_incomplete` | partially | Some units failed |
| `reindex_blocked` | partially | Read the re-tested precondition, not the record |

`degraded` is simply `bool(issues)`. `status` stays `"ready"` in every degraded case **except** an active migration, which flips it to `"migrating"` — so a caller that checks nothing else still learns the one fact that would otherwise produce a convincing lie.

---

## 3. Freshness, stated once

> **Per-project `stale` beats collection freshness. The server's `age_seconds` beats your own arithmetic. Framework corpora have neither.**

`/api/status.freshness` reports the newest index across **all** projects, so it can read `fresh` while the project you are answering about is weeks out of date.

**Never subtract timestamps yourself.** `last_indexed` is emitted as **naive local time** while the MCP envelope's `as_of` is **UTC**; subtracting them can yield a negative age — "indexed in the future". Use `freshness.age_seconds` / `level`, or `project_status.state`. Tracked upstream as A-08.

---

## 4. Unknown is not zero

A count that could not be taken is `null`. Rendering it as `0` is how a dead engine reads as a confidently empty index beside a state DB reporting 145,906 chunks — which is a real incident from this product's history, not a hypothetical.

The same distinction applies to capability detection (`rules/state-detection.md`): *could not determine* and *confirmed absent* both fail closed, but they tell the user to do different things.

## See also

- `rules/state-detection.md` — where these fields come from
- `rules/service-discovery.md` — which service is being trusted
- `skills/ragtools-retrieval/references/recovery.md` — what to do about each state
- `rules/mcp-envelope.md` §3, §8 — error codes and count semantics
