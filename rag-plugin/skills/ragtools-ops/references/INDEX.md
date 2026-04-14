---
title: References Index
topic: routing
relates-to: [_meta]
---

# rag-plugin references — INDEX

This is the routing table for the `ragtools-ops` skill. Given a user concern, find the column that matches and load only the listed file(s). Do **not** load every reference on every turn — that defeats the point of the references library.

## By concern

| If the user is asking about... | Load this file | And maybe also |
|---|---|---|
| "what is ragtools", "components", "architecture overview" | `overview.md` | — |
| install, install path, downloading the installer, dev install, source install | `install.md` | `paths-and-layout.md` |
| post-install verification, `rag doctor`, smoke test, "did it install correctly" | `post-install-verify.md` | `quick-checklist.md` |
| where is X file, `%LOCALAPPDATA%`, `~/Library/Application Support`, dev-mode paths, data dir, log dir | `paths-and-layout.md` | `configuration.md` |
| `config.toml`, env vars, `RAG_*` variables, `.ragignore`, ignore rules, project config schema | `configuration.md` | `paths-and-layout.md` |
| `.mcp.json`, MCP server, "wire to Claude Code", proxy mode, direct mode, `rag-mcp` | `mcp-wiring.md` | `runtime-flow.md` |
| service startup sequence, lifespan, `QdrantOwner`, indexing flow, search flow, watcher thread | `runtime-flow.md` | `risks-and-constraints.md` |
| supporting scripts (`build.py`, `launch.vbs`, `verify_setup.py`), `.claude/skills`, `.claude/agents` (in the rag repo) | `support-tooling.md` | — |
| logs, log location, `service.log`, log rotation, activity log, `/api/activity`, health endpoints | `logs-and-diagnostics.md` | `repair-playbooks.md` |
| an error message, a known failure, "I see X in my logs", "v2.4.1 bug", MPS OOM, Qdrant lock | `known-failures.md` | `repair-playbooks.md` |
| "how do I fix X", repair steps, troubleshooting, service won't start, port collision, watcher dead | `repair-playbooks.md` | `known-failures.md` |
| reset, rebuild, reinstall, recover from corrupted Qdrant, nuclear delete | `recovery-and-reset.md` | `repair-playbooks.md` |
| version, compatibility, semver, schema migration, what changed in 2.4.x | `versioning.md` | `gaps.md` |
| platform support, macOS limitations, Linux gaps, Syncthing risk, single-process constraint, MPS warning | `risks-and-constraints.md` | `versioning.md` |
| "what doesn't work yet", "is X supported", unverified behavior, roadmap items, signing, WinGet | `gaps.md` | `risks-and-constraints.md` |
| post-install validation checklist, support triage checklist | `quick-checklist.md` | `post-install-verify.md` |
| "how should rag-plugin format output", "compact mode", "verbose flag", "output budget" | `output-conventions.md` | — |
| "long-form setup walkthrough", "first-install full steps" | `setup-walkthrough.md` | `install.md` |
| "macOS", "Apple Silicon", "Gatekeeper", "xattr", "LaunchAgent", "Intel Mac", "no .app", "no .dmg" | `macos-specifics.md` | `gaps.md` |
| "Linux", "dev mode", "source install", "no Linux installer", "./ragtools.toml", "venv" | `linux-dev-mode.md` | `gaps.md` |
| "in-place upgrade", "portable replace", "tarball replace", "source pull upgrade" | `upgrade-paths.md` | `recovery-and-reset.md` |

## By failure ID

When `known-failures.md` classifies a symptom into a failure ID, jump to the named playbook in `repair-playbooks.md`:

| Failure ID | Playbook anchor |
|---|---|
| `F-001` v2.4.1 config-permission bug | `repair-playbooks.md#add-project-permission-denied` |
| `F-002` MPS OOM (macOS) | `known-failures.md#mps-out-of-memory` (no playbook — fixed in v2.4.2) |
| `F-003` Qdrant lock contention | `repair-playbooks.md#qdrant-already-accessed` |
| `F-004` Watcher silent death | `repair-playbooks.md#watcher-not-running` |
| `F-005` Service will not start | `repair-playbooks.md#service-will-not-start` |
| `F-006` Projects empty after restart | `repair-playbooks.md#projects-empty-after-restart` |
| `F-007` Indexing slow / stuck | `repair-playbooks.md#indexing-slow-or-stuck` |
| `F-008` Admin panel won't load / port in use | `repair-playbooks.md#admin-panel-port-collision` |
| `F-009` MCP server not connecting from Claude Code | `repair-playbooks.md#mcp-not-connecting` |
| `F-010` `Collection NOT FOUND` from `rag doctor` while service is up | `known-failures.md#collection-not-found-while-service-up` (not a bug) |

## Routing rules

1. **Default to the smallest viable load.** Most user questions need exactly one reference file.
2. **Never load `INDEX.md` itself for content** — it's only for routing. Load the target file directly.
3. **For unknown symptoms**, load `known-failures.md` first to attempt classification before walking any playbook.
4. **For destructive operations**, always load `recovery-and-reset.md` (it has the gating language) before walking the user through a delete.
5. **For "is X supported" questions**, load `gaps.md` first — the answer may be "no, this is unimplemented".

## File size budget

Every file in this directory is kept under **~400 lines** to stay skill-loadable. If a file grows past that, split it.
