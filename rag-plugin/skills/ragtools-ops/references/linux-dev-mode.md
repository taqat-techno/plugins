---
title: Linux and Dev-Mode Behavior, Limitations
topic: linux-dev
relates-to: [install, paths-and-layout, gaps, configuration, repair-playbooks]
source-sections: [§4, §6.4, §6.5, §8, §19]
---

# Linux and Dev Mode

ragtools has **no packaged Linux artifact** (G-001). The codebase is cross-platform — `pip install -e ".[dev]"` works on Linux — but the CI/CD pipeline at `.github/workflows/release.yml` does not produce a Linux binary. This file documents what works, what doesn't, and what rag-plugin does on Linux.

## The honest picture

| Aspect | Status | Reference |
|---|---|---|
| Linux dev install (`pip install -e .`) | ✅ Works | `install.md` §6.4–6.5 |
| Linux packaged installer | ❌ Not built | `gaps.md#g-001` |
| Linux service auto-start | ❌ Not implemented | (no startup infra at all on Linux) |
| Linux installer release artifact | ❌ Not produced by CI | `gaps.md#g-001` |
| `rag` CLI commands | ✅ Work in dev mode |
| HTTP API on `127.0.0.1:21420` | ✅ Works in dev mode |
| MCP server | ✅ Works in dev mode |
| Embedded Qdrant + SentenceTransformers | ✅ Work in dev mode |

**The plugin's `/rag-setup` refuses the packaged install path on Linux** with a clear "no packaged Linux artifact" message and offers the dev-install flow as an alternative (Phase 3 already implemented this).

## Dev-mode detection

Dev mode is detected by the presence of `.venv/` and `pyproject.toml` containing `name = "ragtools"` in the current working directory:

```bash
test -f pyproject.toml && grep -q "name = \"ragtools\"" pyproject.toml && test -d .venv && echo dev-mode
```

If the env vars `RAG_DATA_DIR` or `RAG_CONFIG_PATH` are set, those override CWD detection (per the install discovery order in D-004).

## Paths in dev mode

Dev mode uses **CWD-relative** paths, not platform-conventional ones:

| Purpose | Path |
|---|---|
| Config file | `./ragtools.toml` (CWD-relative) |
| Data directory | `./data/` (CWD-relative) |
| Qdrant storage | `./data/qdrant/` |
| State DB | `./data/index_state.db` |
| Service log | `./data/logs/service.log` |
| PID file | `./data/service.pid` (varies — see config.py) |
| Binary | `rag` from the active venv's `bin/` (Linux/macOS) or `Scripts/` (Windows Git Bash) |

**Critical:** dev mode requires the user to run commands from the **same directory** as the original `pip install -e .`. Running `rag service start` from a different directory creates a new `./data/` and a new `./ragtools.toml`, which looks like F-006 ("projects empty") even though nothing is actually wrong.

The plugin's mode banner shows `dev-mode` explicitly when this is detected, so the user knows their paths are relative.

## Install procedure (Linux)

The dev install from `install.md` §6.4 works on Linux as-is:

```bash
git clone https://github.com/taqat-techno/rag.git
cd rag

python -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"

rag version
rag doctor

# Run the test suite (optional)
pytest

# Start the service
rag service start

# Verify
curl http://127.0.0.1:21420/health
```

**No startup auto-registration.** There is no `systemd` unit file, no `.desktop` entry, no shell-rc hook. The user must start the service manually each session, or write their own systemd/`init` integration.

## Linux dev-mode prerequisites

Same as the dev-mode prerequisites in `install.md`:

- **Python ≥ 3.10** (Python 3.12 is the tested CI version)
- **Git**
- **pip** (bundled with Python)
- A C compiler may be needed for some sub-dependencies (most have prebuilt wheels, but `qdrant-client` and `sentence-transformers` occasionally need build tools on uncommon distros)

## What rag-plugin does differently on Linux

### `/rag-setup`
- Detects platform via `uname -s` (or absence of Windows env vars)
- **Refuses** the packaged install path with a clear "no packaged Linux artifact yet (G-001)" message
- Offers to walk the dev install from source as the only supported path
- Loudly notes:
  - Config lives at `./ragtools.toml` (CWD-relative)
  - Data lives at `./data/` (CWD-relative)
  - No startup auto-registration
  - User must start the service manually each session

### `/rag-status`
- Mode banner shows `dev-mode` explicitly
- Paths shown are absolute (resolved from the dev-mode CWD)
- Service mode probe is identical (HTTP API on `127.0.0.1:21420`)

### `/rag-doctor`
- Wraps `rag doctor` identically; the doctor command is platform-agnostic
- Log scan path resolves to `./data/logs/service.log`

### `/rag-repair`
- Process discovery: `ps aux | grep rag` (same as macOS)
- Port collision: `lsof -i :21420` (or `ss -tlnp | grep 21420` if `lsof` missing)
- **P-empty stale-CWD rescue** is more relevant on Linux dev mode than on Windows packaged — the bug class (CWD-relative config write going to the wrong directory) is still possible if the user runs `rag service start` from a directory that is not the original install dir

### `/rag-projects`
- HTTP API surface is identical
- Cloud-sync detection on Linux includes Syncthing (`~/.config/syncthing/`) and Dropbox/OneDrive desktop sync clients if installed

### `/rag-upgrade`
- Detects dev mode and skips the GitHub releases download flow entirely
- Walks the source-pull flow from `upgrade-paths.md#source-pull-dev-mode`:
  ```bash
  rag service stop
  cd /path/to/rag
  git pull
  pip install -e ".[dev]"
  rag service start
  ```
- Pre-v2.4.1 warning still applies — `git checkout v2.4.1 || git checkout main` if needed

### `/rag-reset`
- `--soft` is identical (HTTP API)
- `--data` shows `rm -rf ./data` (CWD-relative — only run from the dev install directory!)
- `--nuclear` shows `rm -rf ./data ./ragtools.toml` (also CWD-relative — same warning)
- Pre-v2.4.1 block applies regardless

## What's missing on Linux that exists on Windows

| Feature | Windows | Linux dev | Workaround |
|---|---|---|---|
| Packaged installer | `.exe` + Inno Setup | ❌ Not produced (G-001) | Source install from `git clone` |
| Login auto-start | Startup folder VBScript | ❌ No infra | Write your own systemd unit or shell-rc entry |
| Code signing | Unsigned (SmartScreen friction) | N/A — running from source | None needed |
| WinGet | ❌ Not submitted (G-003) | N/A | Manual `git clone` |

## Could a Linux installer be added?

Yes, in theory. The codebase is cross-platform. Adding a Linux build would require:
1. Adding `ubuntu-latest` (or similar) to the `release.yml` matrix
2. Producing a PyInstaller bundle for Linux
3. Deciding on a packaging format (`.AppImage`, `.deb`/`.rpm`, or `.tar.gz`)
4. Optionally adding a systemd unit file

This is documented as G-001 in `gaps.md`. The rag-plugin plugin will not promise it until ragtools ships it.

## Why dev-mode users should run from the install directory

The dev-mode CWD-relative path resolution means:

```bash
cd /home/user/rag
source .venv/bin/activate
rag service start    # uses ./data and ./ragtools.toml correctly

# vs

cd /home/user
source rag/.venv/bin/activate
rag service start    # creates new ./data and ./ragtools.toml in /home/user — wrong!
```

Symptom of this footgun: F-006 ("projects empty after restart"), but the root cause is wrong CWD, not a real config-load failure. The plugin's `/rag-status` banner shows the resolved paths so the user can spot this immediately.

## See also

- `install.md` — §6.4 source install procedure
- `paths-and-layout.md` — dev-mode path resolution
- `gaps.md#g-001` — no Linux packaged artifact
- `configuration.md` — config schema (`./ragtools.toml` in dev mode)
- `repair-playbooks.md#projects-empty-after-restart` — F-006 (often a wrong-CWD symptom in dev mode)
- `setup-walkthrough.md#branch-a--linux-dev-install-only` — long-form setup walkthrough Linux branch
- `upgrade-paths.md#source-pull-dev-mode` — upgrade flow for dev installs
- `macos-specifics.md` — the other non-Windows reference (sibling to this one)
