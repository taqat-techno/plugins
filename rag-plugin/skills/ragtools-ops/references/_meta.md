---
title: References Library Metadata
topic: meta
relates-to: [INDEX]
---

# rag-plugin references — metadata

This directory is the bundled references library for the `ragtools-ops` skill. Files are loaded on demand by the skill router (Phase 2+).

## Source

| Field | Value |
|---|---|
| Source document | `ragtools_doc.md` (workspace root: `C:/MY-WorkSpace/claude_plugins/ragtools_doc.md`) |
| Source repo | `https://github.com/taqat-techno/rag` |
| Source repo path | `C:/MY-WorkSpace/rag` (workspace checkout) |
| ragtools version at split time | **2.4.2** |
| Plugin compatibility band | ragtools **2.4.x** (per decision D-011) |
| Split date | 2026-04-14 |
| Phase | 1 of 10 (rag-plugin roadmap) |

## What is in scope

These files are an **operational reference**, not a tutorial and not aspirational. They describe ragtools as it exists at v2.4.2:

- Install paths, config schema, MCP wiring
- Runtime flow, logs, health endpoints
- Known failure modes, repair playbooks, recovery
- Versioning, platform constraints, gaps
- Quick checklist and source-file index

## What is out of scope

- Tutorials for end users (ragtools ships its own `README.md`)
- Plugin-development guidance (this is for the support plugin, not for building MCP plugins generally)
- Anything not grounded in `ragtools_doc.md` or directly observable in the product source tree

## Update rules

When ragtools releases a new version:

1. Re-read upstream `ragtools_doc.md` and `C:/MY-WorkSpace/rag/CHANGELOG.md`.
2. Update only the files affected by the diff.
3. Bump the version row in this file (and the compatibility band in `plugin.json` if needed).
4. Add an entry to `../../../docs/decisions.md` if a behavioral assumption changes.
5. Run the doc-sync helper (Phase 9) to verify no orphaned references remain.

**Never invent behavior the source doc does not document.** When the doc is silent, mark it as a gap in `gaps.md` and add it to the decisions log as a known unknown.
