# State detection — shared contract

Every user-facing command in `rag-plugin` begins with the same state probe. The probe produces a **state object** and a **mode banner**. Commands branch on the state object; the banner is printed verbatim at the top of the response.

This file is the single source of truth. Commands reference it as `see rules/state-detection.md` in their Step 0 instead of re-documenting the recipe (ARCHITECTURE.md single-owner layering).

**Endpoint resolution is delegated.** This file no longer names a port. `rules/service-discovery.md` owns "which service am I talking to", because an installed service defaults to 21420, a source install to 21421, and both can run at once reporting the same version.

---

## The state object

```
state.install_mode   ∈ { not-installed, packaged-windows, packaged-macos,
                         packaged-linux, dev-mode, unknown }
state.service_mode   ∈ { UP, DEGRADED, MIGRATING, STARTING, DOWN, BROKEN, N/A }
state.mcp_available  : bool
state.mcp_mode       ∈ { proxy, direct, degraded, failed, N/A }
state.binary_path    : str | None
state.version        : semver | None
state.config_path    : str | None
state.data_path      : str | None
state.log_path       : str | None
state.latest_version : semver | None

# --- service identity (WP-4, from rules/service-discovery.md) ---
state.bound_port     : int | None      # the resolved port. NEVER a literal.
state.base_url       : str | None
state.data_dir       : str | None      # which store this service owns
state.service_id     : str | None      # stable per data dir
state.instance_id    : str | None      # changes on restart
state.install_kind   ∈ { packaged, source, unknown }   # INFERRED, not self-reported
state.collection     : str | None      # e.g. "28 collections (per_project)"
state.alternatives   : list            # other ragtools services seen

# --- health (WP-6) ---
state.degraded       : bool
state.issues         : list[str]       # /health.issues, see the vocabulary below
state.engine_state   : str | None      # ready|starting|crashed|restarting|restart_exhausted
state.registry_integrity : str | None
state.config_state   : str | None
state.migration      : dict | None
state.recovery       : dict | None
state.index_availability : str | None  # ready|empty|rebuilding|blocked|partial_unavailable|
                                       # stale_searchable|storage_unavailable

# --- scope (WP-2, from scripts/scope_resolve.py) ---
state.project        : str | None      # resolved project id for the cwd
state.project_mode   ∈ { docs, code, general }
state.project_state  : str | None      # indexed|indexed_stale|path_missing|...
state.scope_ambiguous: bool
state.scope_candidates : list[str]

# --- capabilities (WP-10, replaces the redaction_fix_status scalar) ---
state.capabilities   : dict            # see "Capability floors" below
```

## Capability floors (replaces `redaction_fix_status`)

The old contract carried a single constant:

```
KNOWN_SAFE_FLOOR = None   # "no ragtools release is known-safe as of this writing"
```

Every comparison against `None` evaluated to `not-yet-fixed`, so `set_project_mode` was **permanently** forbidden and every `secret_audit` answer carried a redaction caveat forever. That was correct when written and stopped being correct in ragtools **v3.0.0**, five releases before it was noticed. A gate with no expiry is a gate nobody can pass.

**Prefer a probe; use a version floor only where no probe exists** — which is what D-032's own "reverse only if" clause anticipated.

| Capability | How it is established | Floor | Probe |
|---|---|---|---|
| `scope_mandatory` | **probe** — one unscoped `GET /api/search`; 422 ⇒ mandatory, 200 ⇒ legacy | — | yes |
| `dependencies` | **probe** — `GET /api/dependencies` 200 vs 404 | 3.0.0 | yes |
| `structured_errors` | **probe** — `structured=true` returns `meta.error_code` | — | yes |
| `per_project_layout` | `/health.collection_strategy` | — | yes |
| `path_doubling` (A-02) | **probe** — compare `structured.file_path` against `context` on one known result | — | yes |
| `index_redaction` | **version floor** — no probe exists, which is exactly why a floor remains | **3.0.0** | no |

`scripts/capability_probe.py` implements this. Unknown ⇒ treat as the restrictive answer (fail closed), and say which it was: "could not determine" and "confirmed not present" get different messages.

---

## Cases a command can distinguish from the state object alone

| Case | install_mode | service_mode | version |
|---|---|---|---|
| **not-installed** | `not-installed` | `N/A` | `None` |
| **installed, service down** | packaged-* / dev-mode | `DOWN` | parsed |
| **installed, starting** | packaged-* / dev-mode | `STARTING` | parsed |
| **installed, broken** | packaged-* / dev-mode | `BROKEN` | may be None |
| **installed, degraded** | packaged-* / dev-mode | `DEGRADED` | parsed |
| **installed, rebuilding** | packaged-* / dev-mode | `MIGRATING` | parsed |
| **installed, healthy** | packaged-* / dev-mode | `UP` | parsed |

---

## The detection recipe (perform in order)

### Step 1 — Resolve the service

Follow `rules/service-discovery.md`. It yields `bound_port`, `base_url`, `data_dir`, `service_id`, `instance_id`, `install_kind`, `collection`, and `alternatives`.

**If it reports ambiguity, stop and ask.** Two services with different knowledge bases are not a detail to resolve silently.

### Step 2 — MCP probe (preferred when tools are available)

If `mcp__plugin_rag_ragtools__*` tools are in the session, call:

```
mcp__plugin_rag_ragtools__index_status()
```

Returns, on a current per-project install:

```
[RAG STATUS] Knowledge base is ready (proxy mode).
  Collection: 28 collections (per_project)
  Total files: 7991
  Total chunks: 98611
  Points: 308826
  Projects: alpha, beta, ...
  Embedding model: all-MiniLM-L6-v2
  Score threshold: 0.3
  Mode: proxy (forwarding to service)
```

Parse the `Mode:` line → `mcp_mode`. `proxy` implies the service is up.

> **`Collection:` is a label, not a name to query.** Under `per_project` there is no `markdown_kb`; the router owns collection naming. An earlier version of this document showed `Collection: markdown_kb` as the example, which taught a v2 storage model that has not existed since v3.0.0.
>
> **`Total chunks` and `Points` answer different questions** — historical (state DB) versus live (store). On a measured install they read 98,611 and 308,826. Neither is wrong; use `service_status` when the number matters (see `rules/mcp-envelope.md` §8).

If the call returns `STARTUP_FAILED`, mark `mcp_available = False` and fall through.

### Step 3 — HTTP probe, and read the body

```bash
curl --max-time 1 -s "${state.base_url}/health"
```

**A 200 is not the answer — the body is.** Mapping only the status code was how a service reporting `degraded: true, issues: [storage_unreachable, engine_crashed]` got classified `UP`, after which Claude trusted its search results.

| Body | service_mode |
|---|---|
| `status: "ready"`, `degraded: false` | `UP` |
| `status: "ready"`, `degraded: true` | **`DEGRADED`** — record `issues[]` |
| `status: "migrating"` | **`MIGRATING`** — record `migration` |
| `status: "starting"` | `STARTING` (re-probe once after 2 s) |
| connection refused / timeout | `DOWN` |
| 500 / hang past timeout | `BROKEN` |

**`/health.issues` vocabulary** — the complete set:
`watcher_not_running` · `storage_unreachable` · `engine_crashed` · `engine_restarting` · `engine_restart_exhausted` · `engine_log_unavailable` · `rebuild_interrupted` · `recovery_unresolved` · `registry_integrity_unresolved` · `config_migration_failed` · `reindex_in_progress` · `reindex_incomplete` · `reindex_blocked`

`degraded` is simply `bool(issues)`. `status` stays `"ready"` in every degraded case **except** an active migration, which flips it to `"migrating"` — because a caller that checks nothing else must not be told a half-built index is ready.

Interpretation of each issue: `rules/trust-model.md`.

### Step 4 — Resolve install mode (amends D-004)

1. **Env:** `RAG_DATA_DIR`, `RAG_CONFIG_PATH`, `RAG_SERVICE_PORT`. If set, record them.
2. **`/identity.data_dir`** from Step 1 — the most reliable signal, because it names where the bytes are. Prefer it over anything below.
3. **Binary on PATH:** `where rag` (Windows) / `which rag` (macOS, Linux).
4. **Platform default install paths:**
   - Windows: `%LOCALAPPDATA%\Programs\RAGTools\rag.exe`
   - macOS: `~/Applications/rag/rag`, `/usr/local/bin/rag`, `/opt/homebrew/bin/rag`
   - **Linux: `~/.local/bin/rag`, `/usr/local/bin/rag`, `/opt/RAGTools/rag`**
5. **Dev-mode:** `pyproject.toml` + `.venv` in the working tree with `ragtools` as the package name.
6. None of the above → `not-installed`. Stop; return the object.

Compose: `packaged-windows` · `packaged-macos` · **`packaged-linux`** · `dev-mode` · `not-installed`.

> Linux packaging shipped in ragtools **v2.5.1**. D-004 predates it and listed Windows and macOS only, so a Linux packaged install fell through to `dev-mode` or `not-installed`. This step is the amendment.

**Do not derive install mode from `/identity.install_mode`.** It is inverted for PyInstaller bundles — see `rules/service-discovery.md` §3 (A-09). Use `state.install_kind`.

### Step 5 — Parse version (only if `binary_path` resolved)

Prefer `/identity.version` or `/health.version` from Step 1. Fallback:

```bash
rag version 2>&1
```

Parse with `(\d+\.\d+\.\d+)`. If the parse fails, set `state.version = None` and treat the install as suspect — **never assume a version**, because the capability floors above key off it.

### Step 6 — Resolve paths

**Preferred:** `mcp__plugin_rag_ragtools__get_paths()` — returns every absolute path and works in degraded mode via the filesystem fallback. Correct on all three platforms, which is why it beats hand-constructing.

**Fallback when the service is UP:** `curl --max-time 2 -s "${state.base_url}/api/status"`.

**Fallback when DOWN:** platform defaults in `references/paths-and-layout.md`. Never hand-construct from scratch.

### Step 7 — Resolve scope (only when the command needs retrieval context)

`scripts/scope_resolve.py` against the cwd. Yields `project`, `project_mode`, `project_state`, and `scope_ambiguous`. Skip this step entirely for commands that do not touch retrieval — it is not free and most operational commands do not need it.

---

## The mode banner — verbatim format

Printed at the top of every command's response. **Exactly 6 lines.** Do not reformat, re-order, or decorate:

```
ragtools detected: <install_mode>
service mode: <UP (proxy) | DEGRADED (<issues>) | MIGRATING | DOWN (direct fallback) | STARTING | BROKEN | N/A>
binary: <binary_path or "not found">
config:  <config_path or "not found">
data:    <data_path or "not found">
logs:    <log_path or "not found">
```

When `install_mode == not-installed`, the five non-first lines are `N/A` or `not found`.

When more than one ragtools service was found, add **one** line after the banner:

```
note: <N> ragtools services running; using :<bound_port> (<data_dir>). Others: <ports>
```

---

## Rules for commands consuming this contract

1. **Do not re-implement the recipe.** Reference this file.
2. **Do not assume any state.** Every command handles `not-installed` — minimum is a one-line refusal pointing at `/setup`.
3. **Do not skip the probe to save time.** Warm path is a cached read plus one `/health`; that is cheap against a command acting on a false assumption.
4. **Do not let the banner be optional.** D-008's compact-by-default allows dropping prose, not the banner.
5. **Do not hardcode a port.** Ever. `rules/service-discovery.md` owns it.
6. **Do not classify on the status code alone.** Read `degraded`, `issues[]`, `status`.

## See also

- `rules/service-discovery.md` — endpoint resolution and instance selection
- `rules/trust-model.md` — what each `issues[]` value means for trusting results
- `rules/mcp-envelope.md` — tool inventory, envelope, error codes
- `docs/decisions.md` — D-004 (amended in Step 4), D-005, D-008, D-032, D-033, D-036
- `scripts/service_discover.py` · `scripts/scope_resolve.py` · `scripts/capability_probe.py`
- `references/paths-and-layout.md` — platform defaults when the service is down
