# State detection — shared contract

Every user-facing command in `rag-plugin` begins with the same state probe. The probe produces a **state object** and a **mode banner**. Commands branch on the state object; the mode banner is printed verbatim at the top of the response.

This file is the single source of truth. Commands reference it as `see rules/state-detection.md` in their Step 0 instead of re-documenting the recipe — that is how we enforce single-owner layering (see `ARCHITECTURE.md`).

## The state object

```
state.install_mode   ∈ { not-installed, packaged-windows, packaged-macos, dev-mode, unknown }
state.service_mode   ∈ { UP, STARTING, DOWN, BROKEN, N/A }
state.binary_path    : str | None
state.version        : semver | None            # from `rag version`
state.config_path    : str | None
state.data_path      : str | None
state.log_path       : str | None
state.latest_version : semver | None            # only when a command explicitly fetched it
```

Cases a command can distinguish from the state object alone:

| Case | install_mode | service_mode | version |
|---|---|---|---|
| **not-installed** | `not-installed` | `N/A` | `None` |
| **installed, service down** | packaged-* / dev-mode | `DOWN` | parsed |
| **installed, service starting** | packaged-* / dev-mode | `STARTING` | parsed |
| **installed, service broken** | packaged-* / dev-mode | `BROKEN` | parsed (may be None if binary hangs) |
| **installed, healthy, old version** | packaged-* / dev-mode | `UP` | `< latest_version` |
| **installed, healthy, current version** | packaged-* / dev-mode | `UP` | `== latest_version` |
| **installed, healthy, dev/newer** | packaged-* / dev-mode | `UP` | `> latest_version` |

## The detection recipe (perform in order, stdlib + curl + rag CLI only)

### Step 1 — Resolve install mode (mirrors D-004)

1. **Env var check:** `printenv RAG_DATA_DIR RAG_CONFIG_PATH` (POSIX) / `echo %RAG_DATA_DIR% %RAG_CONFIG_PATH%` (Windows). If set, record them.
2. **Binary on PATH:** `where rag` (Windows) / `which rag` (macOS/Linux). If found, record `binary_path`.
3. **Platform default install paths:**
   - Windows: `test -f "$LOCALAPPDATA/Programs/RAGTools/rag.exe"`
   - macOS: common extract dirs like `~/Applications/rag/rag`
4. **Dev-mode detection:** `pyproject.toml` + `.venv` in CWD, with `ragtools` as the package name.
5. **None of the above →** `install_mode = not-installed`. Set every other path field to `None`. Stop detection here and return the state object — there is nothing else to probe.

Compose `install_mode`: `packaged-windows`, `packaged-macos`, `dev-mode`, or `not-installed`.

### Step 2 — Probe service health (1-second timeout, single curl)

```bash
curl --max-time 1 -s -w "\n%{http_code}" http://127.0.0.1:21420/health
```

| HTTP result | service_mode |
|---|---|
| `200` + `{"status":"ready",...}` | `UP` |
| `200` + `{"status":"starting",...}` | `STARTING` (re-probe once after 2s; if still starting, keep STARTING) |
| Connection refused / timeout / `000` | `DOWN` |
| `500` / hang past timeout | `BROKEN` |

### Step 3 — Parse version (only if `binary_path` resolved)

```bash
rag version 2>&1
```

Parse with a `(\d+\.\d+\.\d+)` regex. If the parse fails, set `state.version = None` and mark the install as suspect. Commands must treat unparseable versions as an error condition — do not assume a version.

### Step 4 — Resolve paths (only if service is UP)

When the service is UP, the authoritative source of all paths is:

```bash
curl --max-time 2 -s http://127.0.0.1:21420/api/status
```

Parse `config_path`, `data_path`, `log_path` from the response. Fall back to platform defaults if the service does not expose a path (older versions).

When the service is DOWN, resolve paths from the platform defaults in `references/paths-and-layout.md` — never hand-construct from scratch.

## The mode banner — verbatim format

Every command prints this at the top of its response. It is **exactly 6 lines**. Do not reformat, do not re-order, do not add decorations:

```
ragtools detected: <install_mode>
service mode: <UP (proxy) | DOWN (direct fallback) | STARTING | BROKEN | N/A>
binary: <binary_path or "not found">
config:  <config_path or "not found">
data:    <data_path or "not found">
logs:    <log_path or "not found">
```

When `install_mode == not-installed`, all five non-first lines are `N/A` or `not found`.

## Rules for commands consuming this contract

1. **Do not re-implement the recipe.** Reference this file. If the probe needs to change, update this file once; every command picks it up.
2. **Do not assume any state.** Every command must handle `not-installed` — the minimum behavior is a one-line refusal with a pointer at `/rag-setup`.
3. **Do not skip the probe to save time.** The probe is ~150–400ms total (one `where rag`, one `curl /health`, optionally one `curl /api/status`). That is cheap compared to the cost of a command acting on a false assumption.
4. **Do not let the banner be optional.** Users rely on it for at-a-glance orientation. Compact-by-default (D-008) does not allow dropping the banner — it allows dropping prose around the banner.

## See also

- `ARCHITECTURE.md` — single-owner layering rule
- `docs/decisions.md` — D-004 (install discovery order), D-005 (service-down behavior), D-008 (compact output)
- `references/paths-and-layout.md` — platform default paths when the service is down
- `references/runtime-flow.md` — HTTP API surface used by the UP-state path resolution
