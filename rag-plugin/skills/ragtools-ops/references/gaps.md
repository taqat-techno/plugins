---
title: Gaps, Unknowns, and Unverified Items
topic: gaps
relates-to: [risks-and-constraints, versioning, install]
source-sections: [§19]
---

# Gaps, Unknowns, and Unverified Items

This file is the **honest "what we don't promise" list**. The rag-plugin plugin must:

- **Never claim** a feature listed here works.
- **Refuse cleanly** when asked to do something in this list, with a clear "this is not implemented" message.
- **Update this file** when an item is verified or implemented.

## Confirmed gaps

### G-001 — Linux packaged artifact

**Status:** Code is cross-platform but **no CI build or installer exists**. Dev-mode install via `pip install -e ".[dev]"` works; packaged install is unverified.

**Plugin behavior:** `/rag-setup` on Linux must say "no packaged Linux artifact yet — use the dev install from source" and link to `install.md`.

---

### G-002 — macOS login auto-start

**Status:** Not implemented. Confirmed unimplemented in upstream `src/ragtools/service/startup.py`: `_check_windows()` returns `False` on other platforms.

**Plugin behavior:** `/rag-setup` on macOS must NOT promise auto-start. The status banner must show "auto-start: not supported on macOS".

---

### G-003 — WinGet submission

**Status:** `winget/` manifests exist but have **not been submitted** to the official WinGet repository. Upstream `RELEASING.md` describes the intended flow but it is not automated.

**Plugin behavior:** Never tell users to install via `winget install ragtools`. Always link to GitHub releases.

---

### G-004 — Intel macOS support

**Status:** The `macos-14` runner only builds arm64. An x86_64 build would require adding `macos-13` (or similar) to the matrix. **Not implemented.**

**Plugin behavior:** Detect arch on macOS. If `x86_64`, refuse `/rag-setup` with "Intel Macs are not supported by ragtools — Apple Silicon required". Do not let users download an arm64 tarball that won't run.

---

### G-005 — Code signing / notarization

**Status:** **Not implemented** on either platform.

- Windows users may see SmartScreen warnings on first install.
- macOS users must bypass Gatekeeper manually with `xattr -cr rag/`.

**Plugin behavior:** `/rag-setup` must warn about SmartScreen / Gatekeeper friction up front. Do not pretend the install is friction-free.

---

### G-006 — Persistent activity log

**Status:** Currently in-memory only (500-entry ring buffer in `src/ragtools/service/activity.py`). Lost on service restart.

**Plugin behavior:** For historical diagnostics, fall back to `service.log` files. Do not promise that activity is queryable across restarts.

---

### G-007 — Structured request logging in FastAPI

**Status:** No middleware yet. uvicorn logs are at WARNING level, suppressing HTTP access traces.

**Plugin behavior:** Cannot give users a clean per-request log. Diagnostic flows that need request traces must accept this limitation.

---

### G-008 — `scripts/verify_setup.py` semantics

**Status:** Exists but **not fully re-verified** for this documentation cycle. Treat it as a general dev-mode sanity script. Recheck when updating `_meta.md`.

**Plugin behavior:** Do not invoke `verify_setup.py` programmatically. Defer to `rag doctor` instead.

---

### G-009 — `rag ignore check` edge cases

**Status:** Documented in CLI help but full edge-case semantics should be **re-verified against `src/ragtools/cli.py`** for the support doc.

**Plugin behavior:** If a user asks about `rag ignore check` behavior, recommend testing against their own files rather than asserting specific edge cases.

---

### G-010 — Project disk unmount behavior

**Status:** The service validates paths at startup and logs a warning when a configured project path doesn't exist. Runtime behavior when a drive disappears **during** watcher operation is **not explicitly documented**.

**Plugin behavior:** If a user reports "my project went missing after I unplugged my external drive", document the symptom and route to `repair-playbooks.md#watcher-not-running`. Do not invent specific behavior.

## Update protocol

When a gap is closed (e.g., macOS LaunchAgent ships):

1. Remove the entry from this file.
2. Add the new behavior to the relevant reference (e.g., `install.md` for installer changes).
3. Update `_meta.md` with the new ragtools version.
4. Add a decision-log entry in `../../../docs/decisions.md` if the plugin's behavior changes.

## See also

- `risks-and-constraints.md` — known constraints (vs unknowns)
- `versioning.md` — version history of fixes
- `install.md` — what install paths are actually supported today
