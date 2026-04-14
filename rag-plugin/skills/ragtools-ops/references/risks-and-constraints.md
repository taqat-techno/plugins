---
title: Operational Risks, Constraints, and Hard Rules
topic: risks
relates-to: [runtime-flow, mcp-wiring, known-failures, gaps]
source-sections: [§18]
---

# Operational Risks, Constraints, and Hard Rules

These are not bugs — they are **design facts** the plugin must honor.

## Single-process constraint (HARD)

Qdrant local mode takes an **exclusive file lock**. Running two processes against the same data directory is **not possible**. This is the central design constraint (`docs/decisions.md` → Decision 1 in the upstream rag repo).

**Implication:** users must understand that `rag index` / `rag watch` / `rag service` / Claude Code MCP cannot all independently hold Qdrant. **The service is designed to be the one owner.**

This is the rule the Phase 6 PreToolUse hook exists to enforce. Any CLI command that would open Qdrant in direct mode while the service is up is wrong.

## macOS limitations (v2.4.2)

- ❌ No `.app` bundle — tarball only (Phase 1 of the macOS rollout)
- ❌ No `.dmg` — user must `tar -xzf` manually
- ❌ No Gatekeeper signing — user must `xattr -cr rag/` on first use
- ❌ No LaunchAgent auto-start — user must start the service manually each time
- ❌ Intel Macs are not built — `macos-14` runner only builds arm64

These are documented roadmap items in the upstream repo. See `gaps.md` for full list.

## macOS MPS — must stay disabled

The encoder is **explicitly forced to `device="cpu"`** in `src/ragtools/embedding/encoder.py` to prevent MPS (Apple Metal) memory exhaustion.

**Do NOT "optimize" this.** Letting PyTorch auto-select the device will break CI and real user installations on Apple Silicon. This is a permanent rule, not a temporary workaround.

The rag-plugin plugin should never recommend setting `PYTORCH_ENABLE_MPS_FALLBACK` or modifying device selection. If a user asks why CPU and not GPU, point them at this section.

## Bundle size

~1 GB after extraction. ~488 MB Windows installer / ~423 MB macOS tarball compressed. Dominated by PyTorch + the bundled model. **Not reducible** without removing the model (which would require a first-run download).

The rag-plugin plugin should warn users about the download size before pointing them at the installer URL.

## Windows Startup folder auto-start

Uses a VBScript in `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\RAGTools.vbs`. This works without elevation but has limitations:

- If the user moves or deletes the install directory, the VBScript breaks until the service runs and re-registers itself.
- The VBScript CWD was a bug source — see the v2.4.1 fix in `known-failures.md#f-001`.
- `schtasks /sc onlogon` was abandoned because it requires elevation even with `/it`.

## Syncthing / cloud-synced config directory

If the config file is in a Syncthing-managed (or iCloud, OneDrive, Dropbox) directory, **another device's state can overwrite local changes**.

**Symptom:** projects reappear after removal, or removed projects come back after a sync.

**Mitigation:**
- Store `config.toml` outside the synced directory, OR
- Add `config.toml` (or the entire `RAGTools/` directory) to `.stignore` (Syncthing) or the equivalent ignore mechanism for your sync tool.

The plugin should detect this scenario and warn — see Phase 5 (`/rag-projects`).

## MCP token consumption

The MCP output format is **compact by default** (sentence-boundary truncation, version-suffix deduplication) to reduce Claude's context consumption by ~60–70%.

**The compact mode is the default; full mode is only used for the admin panel search.**

This is why the rag-plugin plugin **never** wraps `search_knowledge_base` itself — it would undo the product's own token-efficiency work. Per decision D-001, search stays inside the MCP server.

## Re-ranking is not implemented

Retrieval is **pure bi-encoder** (no cross-encoder re-ranking). Score threshold is `0.3`. Confidence labels:

- **HIGH** — score ≥ 0.7
- **MODERATE** — 0.5 ≤ score < 0.7
- **LOW** — score < 0.5

Re-ranking is listed as a post-MVP enhancement in the upstream decision record. The rag-plugin plugin should not promise re-ranking until the product ships it.

## Plugin boundary reminder

The forbidden-list in `../../../ARCHITECTURE.md` is the binding rule. The risks here are **why** the boundaries exist:

- Single-process lock → plugin must never open Qdrant directly
- MPS rule → plugin must never recommend GPU
- v2.4.1 bug → plugin must never write `config.toml` from CWD
- MCP compact mode → plugin must never re-wrap search

## See also

- `runtime-flow.md` — how the service enforces the single-process model
- `mcp-wiring.md` — proxy vs direct mode and the Qdrant lock interaction
- `known-failures.md` — what happens when these constraints are violated
- `gaps.md` — risks that are currently unmitigated
