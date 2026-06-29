<!-- Curated GitHub issue draft (enhancement). File to: taqat-techno/plugins.
Companion to docs/issues/P-013-advisory-hook-blocking.md (the hook-blocking bug,
which supersedes the auto-generated P-012). This one tracks the report engine's
adoption of ragtools' structured diagnostics contract. -->

# [rag-plugin] Report engine: consume ragtools' structured diagnostics (`/api/system-health` + `rag doctor --json`) — PL1

**Target repo:** `taqat-techno/plugins`
**Type:** enhancement
**Labels:** `enhancement`, `diagnostics`, `source:rag-plugin`
**Status:** implemented in **v0.16.0** (PR); new signals activate once the ragtools structured contract reaches users.

## Problem

The behavior/diagnostics report inferred app-side health from `/health` + `/api/status` + `/api/watcher/status` only. Two gaps:

1. **Stale heuristic.** It bool-parsed the watcher `running` flag, so a *deliberately user-stopped* watcher was reported as a fault (`A-007`, medium) — a false alarm once ragtools distinguishes "stopped by the user" from "failed".
2. **No machine-readable path.** When ragtools added an enriched `/api/system-health` (watcher `state`, `index_freshness`) and a `rag doctor --json`, the plugin didn't consume them, so it kept relying on heuristics even when the service exposed an authoritative structured contract.

## Change (v0.16.0)

- **Consume the structured contract when available:** `/api/system-health` when the service is UP, `rag doctor --json` when it is not — via capability-detected probes that **no-op on older ragtools** (graceful fallback to the legacy signals; full back-compat).
- **`app_health_signals()`** — a normalized extractor (`/api/system-health` → `rag doctor --json` → legacy) so finding logic is contract-agnostic.
- **`A-007` refined** to consume the watcher `state`: `stopped` → info (intentional, no auto-fix nag); `autostart_failed` → medium; `crashed` / `gave_up` → high (with the specific cause); `running` / `ok` → no finding; **absent `state` (old ragtools) → original running-bool behavior preserved.**
- **`A-015`** ("index is stale") gated on the structured `index_freshness` level.
- **Do not re-raise a stale heuristic** when the structured contract reports a healthy or intentional state.

## Dependency

The enriched `/api/system-health` (watcher `state` + `index_freshness`) and `rag doctor --json` come from ragtools PR **`taqat-techno/rag#3`** (`feat/app-diagnostics-observability`). The plugin change is backward-compatible and ships independently; the new signals light up once that ragtools work reaches users.

## Tests

26 new tests in `scripts/test_rag_report.py` (probes with/without the new endpoint/flag, signal resolution order, A-007 across running/stopped/autostart_failed, A-015 stale/fresh, healthy-system-no-noise). Full plugin suite: **134 passed**. Redaction preserved on all new evidence strings.
