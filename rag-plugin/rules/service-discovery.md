# Service discovery — which ragtools am I talking to?

**Binding.** Every command, hook, and script that reaches a ragtools endpoint resolves it through this rule. No plugin artefact may contain a literal service port in a code path. Implementation: `scripts/service_discover.py`. Pinned by `tests/test_wp04_service_discovery.py`.

Amends **D-004** (install discovery order), which predates Linux packaging and the `/identity` endpoint.

---

## 1. Why a literal port is wrong

`config._default_service_port()` in ragtools:

```python
return 21420 if is_packaged() else 21421
```

So the **installed** service listens on 21420 and a **source** install on 21421 — and a developer working on ragtools itself is running the source one. Both can be up at the same time.

Measured on 2026-08-01, two services were live on one machine:

| | `:21420` | `:21455` |
|---|---|---|
| `version` | **3.5.1** | **3.5.1** |
| `collection` | `27 collections (per_project)` | `2 collections (per_project)` |
| `storage_backend` | managed | embedded |
| projects | 24 real | `alpha`, `beta` — this repo's test fixtures |

A probe that accepts the first responder had an even chance of presenting a four-chunk test fixture as the user's knowledge base.

> **Version is worth zero as a discriminator.** ragtools learned this at the engine layer in v3.2.0: two installations both shipped Qdrant 1.15.5, so the version matched, and one service adopted the other's store. `service/identity.py` already states the rule for the service layer — *"a port is deliberately not among them — a port number alone is never trusted."* This rule applies it to the plugin.

---

## 2. Signals, and what each is worth

| Signal | Weight | Why |
|---|---|---|
| `data_dir` covers / is covered by the workspace | **50** | Names the store the service owns. The strongest tie to *this* directory. |
| `install_kind` matches the context (inferred, §3) | 20 | Source-in-a-checkout vs packaged-elsewhere. |
| A registered project path matches the cwd | 15 | The service actually indexes what you are working on. |
| `collection` label present | 10 | The field that genuinely differed between the two live services. |
| Declares a storage target | 5 | Weak corroboration. |
| Healthy (`degraded == false`) | 5 | **Tie-break only** — see §5. |
| `bound_port` | 0 for selection | Read it to *report* identity and to catch a `:21422`-reports-`:21420` mismatch. |
| **`version`** | **0** | Both live services reported 3.5.1. |
| **Port number** | **0** | The whole point. |
| **Explicit override** | ∞ | Short-circuits scoring entirely (§4). |

Selection requires `score ≥ 40` **and** a lead of `≥ 15` over the runner-up. Anything else is **ambiguous** and the user is asked. Guessing between two services means answering from the wrong knowledge base.

---

## 3. Never trust a service's self-reported install mode

`/identity.install_mode` comes from:

```python
return "packaged" if "site-packages" in (ragtools.__file__ or "") else "source"
```

A **PyInstaller bundle** puts the package under `_internal/`, which contains no `site-packages`, so a genuinely packaged installation reports `source`. Measured: the installed service at `:21420`, running `…\Programs\RAGTools\rag.exe`, reports `install_mode: "source"`.

`profile` is unreliable in the opposite direction — it defaults to `"installed"` when `RAG_PROFILE` is unset, which is exactly how a developer runs from source.

**Neither self-report can be trusted alone.** `install_kind` is inferred from where the data actually lives: a packaged install keeps `data_dir` under the platform application-data directory; a source checkout keeps it beside the code. That is a property of the bytes, not of a string the process computed about itself.

Tracked upstream as **A-09**. `/doctor` shows the self-report beside the inferred value when they disagree.

---

## 4. The algorithm

```
1. OVERRIDE   RAG_SERVICE_PORT / RAG_PLUGIN_SERVICE_PORT set?
              -> probe it, use it, state it. Stop. Never override an override.
2. CACHE      context-cache.json fresh for this workspace key? -> use it (0 HTTP).
3. FAST PATH  probe 21420 and 21421.  One ragtools responder -> select it.
4. SCAN       only if the fast path found nothing: socket-scan 21400-21499,
              EXCLUDING 21500/21501 (the managed Qdrant engine).
5. IDENTIFY   GET /health on each open port. Require the ragtools marker —
              a body carrying `collection` AND `status`. A foreign 200 is
              never scored, never selected.  Then GET /identity.
6. SCORE      §2.
7. DECIDE     clears MIN_SCORE and leads by MIN_MARGIN -> select.
              otherwise -> ASK, showing data_dir / install_kind / collection /
              project count for each candidate.
8. RECORD     cache it; state the chosen bound_port in the first RAG answer.
```

**Portability.** Steps 3–5 use `socket.connect_ex` plus HTTP, which behave identically on Windows, Linux and macOS. There is no listener-table parsing in the selection path. OS-specific process lookup exists only in `owning_process()` for `/doctor` output and never gates selection — a platform whose command is missing degrades to "owner unknown", not to an unusable service.

---

## 5. Health is a tie-break, not a filter

A degraded service is still **the** service. Excluding it would leave the user with nothing to diagnose at exactly the moment they need diagnostics. Select it, then apply the trust model: storage/engine issues mean search results are untrustworthy; a stopped watcher means they are merely old.

---

## 6. Cache and invalidation

Cached under `~/.claude/rag-plugin/state/context-cache.json`, keyed by workspace key, TTL 15 minutes.

Invalidate on: cwd change · any connection failure · `instance_id` change (the service restarted — refresh, do **not** re-ask) · `service_id` change (a *different* data dir — re-select) · explicit `/doctor` or `/project-focus`.

The cache is **machine-local derived data**. Like the focus state (D-028 §9), `~/.claude/rag-plugin/state/` should be excluded from Syncthing / iCloud / OneDrive / Dropbox; workspace keys are absolute local paths and cross-machine sync produces ghost entries. Deleting the file is always safe.

---

## 7. Degenerate cases

| Situation | Response |
|---|---|
| Zero responders | "No RAG service found." Say it once; filesystem only; offer `rag service start`. |
| One responder | Select it, state the port. |
| Two+, evidence separates them | Select, and state *why*. |
| Two+, tied | **Ask.** Show `data_dir`, `install_kind`, `collection`, project count. |
| Responder is not ragtools-shaped | Excluded at step 5. Never scored. |
| Selected service later 503s | Invalidate, re-run once, then degrade to filesystem. |
| `bound_port` ≠ the port that answered | Report both — this is the mismatch `/identity` exists to catch. |

---

## 8. What callers use

```
state.bound_port        the resolved port — use this, never a literal
state.base_url          http://127.0.0.1:<bound_port>
state.data_dir          which store this service owns
state.service_id        stable per data dir
state.instance_id       changes on restart
state.install_kind      inferred (§3), NOT the self-report
state.collection        the discriminator worth printing
state.degraded/.issues  the trust model's input
```

## See also

- `rules/state-detection.md` — the state object this feeds
- `rules/mcp-envelope.md` §5 — the MCP → HTTP → CLI fallback chain
- `docs/decisions.md` D-004 (amended here), D-036
- `scripts/service_discover.py` · `tests/test_wp04_service_discovery.py`
