---
title: Versioning and Compatibility
topic: versioning
relates-to: [_meta, install, known-failures, recovery-and-reset]
source-sections: [§17]
---

# Versioning and Compatibility

## Current state

| Field | Value |
|---|---|
| Current version | **2.4.2** |
| Source-of-truth files | `src/ragtools/__init__.py`, `pyproject.toml`, `installer.iss` (must stay in sync per upstream `RELEASING.md`) |
| Versioning scheme | **Semantic versioning** — `X.Y.Z` (X=major/breaking, Y=minor/features, Z=patch/fixes) |
| Python | ≥ 3.10, tested on 3.12 |
| Embedding model | `all-MiniLM-L6-v2` (384 dims). Changing this requires a full rebuild — collection dimensions are baked in. |
| Qdrant collection | `markdown_kb`. One collection, project isolation via payload. |
| Config schema | Currently version 2. Version 1 auto-migrated on load. |
| State DB schema | Single table `file_state (file_path PK, project_id, file_hash, chunk_count, last_indexed)`. Index on `project_id` added in v2.4.0. |

## rag-plugin compatibility band

Per decision **D-011**, the rag-plugin plugin declares **compatibility with ragtools 2.4.x**. The plugin will be re-validated on:

- ragtools 2.5.x (minor — likely safe but check failure modes)
- ragtools 3.0.x (major — assume breaking)
- Any HTTP API or CLI surface change

The compatibility band lives in `_meta.md` and is updated as part of the doc-sync flow (Phase 9).

## Breaking change history

| Version | Change |
|---|---|
| **v2.0.0** | Introduced the multi-project model. Replaced `content_root` with `[[projects]]`. |
| **v2.4.0** | Split-lock indexing (search no longer blocked during full index). Watcher auto-restart. Duplicate path validation. `_get_ignore_rules` helper. State DB index on `project_id`. |
| **v2.4.1** | Critical fix: config write path resolution (data-loss bug). VBScript CWD fix. Startup-sync empty-projects guard. **Not a breaking change**, but mandatory upgrade. |
| **v2.4.2** | macOS Phase 1 platform support. Encoder forced to `device="cpu"` (MPS OOM fix). MCP server 2-second proxy retry. Compact MCP output mode. **No Windows breaking changes.** |

## Pre-v2.4.1 versions are unsafe

Per decision **D-011** and the v2.4.1 failure mode (`F-001` in `known-failures.md`), the plugin should:

- **Warn** users running pre-v2.4.1 that their config writes can be silently lost.
- **Block destructive operations** (`/rag-reset`, project removal) on pre-v2.4.1 unless the user explicitly confirms they understand the risk.
- **Recommend immediate upgrade** to ≥ v2.4.1 as the first step in any repair flow on those versions.

This is implemented in Phase 7 (`/rag-upgrade`).

## Detecting the installed version

```bash
rag version
# Expected: "ragtools v<X.Y.Z>"
```

The plugin parses this output to drive version-gated behavior. If `rag version` is unavailable (binary not on PATH), the plugin treats this as "not installed" and routes to `/rag-setup`.

## Schema migration

Config schema v1 → v2 is automatic on first load (`migrate_v1_to_v2()` in `src/ragtools/config.py`). Users do not need to migrate manually. The plugin should not attempt to migrate config — that's the product's job.

## See also

- `_meta.md` — current rag-plugin compatibility band
- `install.md` — how to upgrade the binary
- `known-failures.md` — version-specific failures and their fix versions
- `recovery-and-reset.md` — when to upgrade as part of recovery
