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
| Source document | `ragtools_doc.md` (at the marketplace workspace root) |
| Source repo | `https://github.com/taqat-techno/rag` |
| Source repo path | local ragtools checkout (path varies by machine) |
| ragtools version at split time | 2.4.2 |
| **ragtools version last verified against** | **3.5.1** (2026-08-02) |
| **Plugin compatibility band** | **supported 2.5.0 – 3.5.x · target 3.5.1 · degraded 2.5.0–2.6.x · unsupported < 2.5.0** (D-011) |
| Split date | 2026-04-14 |
| Phase | 1 of 10 (rag-plugin roadmap) + post-roadmap amendments through D-037 |

> **Band correction (2026-08-02).** This file said `2.4.x` while `README.md` said "production-ready for ragtools 2.5.x" and the live application was **3.5.1** — three different claims in one plugin. D-011 makes this table the band's single home; the other two now point here rather than restating it.

### What "degraded" means for 2.5.0–2.6.x

Scoped search still works (`project` has existed since 2.x), and the ops tools work. Absent below 3.0.0: `/identity` (fall back to `/health` + `/api/mcp-config`), the shared-dependency tools, per-project collections, and the `state` vocabulary. `set_project_mode` is **blocked** below 3.0.0 by the redaction floor (D-033). Below 2.5.0 the plugin warns once and degrades to documentation only.

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

1. Re-read upstream `ragtools_doc.md` and the ragtools checkout's `CHANGELOG.md`.
2. Update only the files affected by the diff.
3. Bump the version row in this file (and the compatibility band in `plugin.json` if needed).
4. Add an entry to `../../../docs/decisions.md` if a behavioral assumption changes.
5. Run the doc-sync helper (Phase 9) to verify no orphaned references remain.

**Never invent behavior the source doc does not document.** When the doc is silent, mark it as a gap in `gaps.md` and add it to the decisions log as a known unknown.
