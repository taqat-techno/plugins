# rag-plugin — Delivery Report (B-track)

**Repo:** `taqat-techno/plugins` · plugin dir `rag-plugin/` · version **0.15.1 → 0.16.0**
**Date:** 2026-06-29 · Part of the coordinated RAG delivery (companion to ragtools PR `taqat-techno/rag#3`).

## Executive summary

Three of the four B-track items were **already shipped in v0.15.1** and are **validated here** (not duplicated); the one genuinely-open item (**PL1**) is **implemented in v0.16.0** with full backward-compatibility. No release published, no merge, no force-push.

| Item | State | Evidence |
|---|---|---|
| **B2 — advisory hook fail-open** | ✅ shipped v0.15.1 (D-031) — validated | `hooks/hooks.json` inline `-c` bootstrap + `hooks/hook_launcher.py` (advisory normalizes every exit to 0); `hooks/test_hook_launcher.py` 24 tests pass |
| **B3 — P-013 detector** | ✅ shipped v0.15.1 — validated | `scripts/rag_report.py` `analyze_advisory_hook_safety()` + P-013 (High→Critical on `hook-path-fatal`); tests pass |
| **B5 — issue draft (supersede P-012)** | ✅ exists — confirmed + extended | `docs/issues/P-013-advisory-hook-blocking.md` (supersedes P-012); new `docs/issues/PL1-structured-diagnostics-consumption.md` |
| **B4 — PL1 structured-diagnostics consumption** | ✅ implemented v0.16.0 | `scripts/rag_report.py` + `scripts/test_rag_report.py` (+26 tests) |

## B1 — current state (verified by reading the live v0.15.1 code)

The prompt assumed the hook-blocking fix and P-013 detector still needed implementation. **The live code shows they shipped in v0.15.1** (CHANGELOG `[0.15.1]`, D-031). Per the "validate, don't duplicate" instruction, B2/B3/B5 were validated by running their tests; only B4/PL1 was implemented.

## B2 — advisory hook fail-open (validated)

`hooks/hooks.json` runs every command as an inline `python3 -c … || python -c … || py -3 -c …` bootstrap that resolves `CLAUDE_PLUGIN_ROOT` and runs `hooks/hook_launcher.py` only if present. The launcher (advisory mode) normalizes **every** exit — even `sys.exit(2)` — to `0`; a missing script / unresolved `${CLAUDE_PLUGIN_ROOT}` / missing Python / target exception / malformed payload all fail open above the script layer. **`hooks/test_hook_launcher.py` — 24 tests pass.**

## B3 — P-013 detector (validated)

`analyze_advisory_hook_safety()` flags any advisory `hooks.json` command lacking a fail-open wrapper; `P-013` is **High** on static evidence, **Critical** when runtime signatures (`[Errno 2]`, literal `${CLAUDE_PLUGIN_ROOT}`, exit 2) confirm via the `hook-path-fatal` session signal. It supersedes the generic `P-012`. Covered by `scripts/test_rag_report.py`.

## B4 — PL1 (implemented, v0.16.0)

`scripts/rag_report.py` (+254) and `scripts/test_rag_report.py` (+368):

- **`probe_system_health()`** — `GET /api/system-health` when UP; capability-gated, no-op on 404/absent.
- **`probe_doctor_json()`** — `rag doctor --json` when not UP; no-op on old ragtools (non-zero / unparseable). Never raises.
- **`app_health_signals()`** — pure layered extractor (`/api/system-health` → `rag doctor --json` → legacy bodies).
- **`A-007` refined** — consumes watcher `state`: `running`/`ok` → none; `stopped` → info (intentional); `autostart_failed` → medium; `crashed`/`gave_up` → high (with cause); **absent → legacy running-bool preserved**.
- **`A-015`** — stale-index finding gated on structured `index_freshness == "stale"`.
- **Back-compat:** every new probe degrades gracefully; existing tests pass unchanged; no re-raising of a stale heuristic when the structured contract says healthy/intentional.

## Tests

`python -m pytest hooks/test_hook_launcher.py scripts/test_rag_report.py scripts/test_project_focus.py` → **134 passed** (108 pre-existing + 26 new PL1). No linter gate in the repo.

## Backward compatibility

PL1 is additive: against older ragtools (no `/api/system-health` enrichment, no `rag doctor --json`) the plugin falls back to the legacy `/health` + `/api/status` + `/api/watcher/status` signals and the original A-007 running-bool. The new signals activate only when the ragtools structured contract (PR `taqat-techno/rag#3`) is present.

## Known risks / manual validation

- **End-to-end against a live ragtools build that exposes the new contract** — the PL1 tests mock HTTP/subprocess; a real `/api/system-health` (enriched) + `rag doctor --json` run on a Windows packaged install would confirm the wiring end-to-end.
- The new contract is **unreleased** (on ragtools branch `feat/app-diagnostics-observability`); until it ships, PL1 stays on the legacy fallback in the field — correct by design.

## Out of scope (intentional)

- No hook changes (B2 already shipped). No version of the structured contract is rendered into the human Markdown report (kept additive — only the redacted JSON artifact carries the new `State` fields). No release/tag/merge.
