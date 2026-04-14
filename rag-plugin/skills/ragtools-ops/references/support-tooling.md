---
title: Supporting Scripts, Skills, Agents, and Helpers
topic: support-tooling
relates-to: [install, runtime-flow]
source-sections: [§12]
---

# Supporting Scripts, Skills, and Helpers

These are **upstream-repo** tooling for the ragtools product itself (under `C:/MY-WorkSpace/rag/`). The rag-plugin plugin does not own them; they are documented here so the support skill can answer "what does `build.py` do" without re-reading source.

## Scripts (`scripts/`)

| Script | Purpose |
|--------|---------|
| `build.py` | Orchestrates PyInstaller build + model cache + verification. Flags: `--no-model`, `--installer` |
| `launch.vbs` | Smart Windows launcher: checks health → starts service if needed → opens admin panel. Bundled into the installer. |
| `verify_setup.py` | Dev-mode environment check (Python version, imports, etc.) — semantics not fully re-verified, see `gaps.md` |
| `eval_retrieval.py` | Retrieval quality benchmark (MRR, Recall@K) against a question set |

## `.claude/skills/` (development-time skills, in the upstream rag repo)

| Skill | Purpose |
|-------|---------|
| `windows_app_actions/` | Windows app integration patterns (startup folder, VBScript, process management) |
| `macos_app_actions/` | macOS equivalent patterns (LaunchAgents, .app bundles) |
| `cross_platform_app_launch/` | Shared launch patterns across Windows/macOS |
| `macos_release/` | macOS release playbook (Phase 2 / Phase 3 signing) |

These are development aids in the upstream repo, **not runtime components** of ragtools. They do not ship with the installer.

## `.claude/agents/` (development-time agents, in the upstream rag repo)

| Agent | Purpose |
|-------|---------|
| `rag-builder.md` | Mechanical implementation tasks for the rag project |
| `rag-investigator.md` | Research and technical verification for rag decisions |
| `rag-log-monitor.md` | Automated log inspection during testing |

## Key configuration files at the upstream repo root

| File | Purpose |
|------|---------|
| `pyproject.toml` | Python package metadata + dependencies |
| `ragtools.toml` | Dev-mode user config (projects, startup) |
| `installer.iss` | Inno Setup Windows installer script |
| `rag.spec` | PyInstaller spec file |
| `CLAUDE.md` | Development-time instructions for Claude Code working on the rag repo |
| `.mcp.json` | (If present) MCP server config for the rag repo itself |

## Boundary note

These tools are **not part of rag-plugin**. The plugin will never invoke `build.py` or modify `installer.iss`. If a user is debugging the upstream build, point them at the upstream repo and step out of the way.

## See also

- `install.md` — how the installer flow uses `build.py` and `installer.iss` to produce artifacts
- `runtime-flow.md` — how `launch.vbs` triggers service startup
- `gaps.md` — items not fully verified, including `verify_setup.py` semantics
