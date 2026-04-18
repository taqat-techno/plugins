---
title: Installation Sources, Platforms, Prerequisites, Procedures
topic: install
relates-to: [post-install-verify, paths-and-layout, configuration, risks-and-constraints]
source-sections: [§3, §4, §5, §6]
---

# Installation

## Sources and distribution

`ragtools` ships from a single source: the **upstream product GitHub Releases page** at **[github.com/taqat-techno/rag/releases](https://github.com/taqat-techno/rag/releases)**.

The CI/CD pipeline (`.github/workflows/release.yml`) builds packaged artifacts in parallel on tag push:

| Artifact | Platform | Type | Approx. size |
|----------|----------|------|--------------|
| `RAGTools-Setup-{version}.exe` | Windows x64 | Inno Setup installer (recommended) | ~488 MB |
| `RAGTools-{version}-portable.zip` | Windows x64 | Portable bundle (no install) | ~564 MB |
| `RAGTools-{version}-macos-arm64.tar.gz` | macOS Apple Silicon | PyInstaller tarball | ~423 MB |
| `RAGTools-{version}-linux-arm64.tar.gz` | Linux ARM64 (v2.5.1+) | PyInstaller tarball | ~423 MB |

Bundle size is dominated by the bundled SentenceTransformer model (`all-MiniLM-L6-v2`, ~175 MB) and the full PyTorch runtime (~600 MB). Not reducible without removing the model.

**Source install** is also supported for every platform (see "Development install" below). This is the universal fallback — macOS Intel, Linux x86_64, Windows ARM, and any other platform.

WinGet manifests exist under `winget/` but are **not yet published** to the official WinGet repository — see `gaps.md`.

## Supported platforms

| OS / arch | Support | Install artifact | Notes |
|---|---|---|---|
| **Windows 10/11 (x64)** | ✅ Full | `RAGTools-Setup-{version}.exe` or portable `.zip` | Primary platform. Includes auto-start on login via VBScript in Windows Startup folder. |
| **Windows ARM** | ⚠ Source-only | — | No packaged Windows-ARM artifact. Use dev install via `pip install -e ".[dev]"`. |
| **macOS 14+ (Apple Silicon / arm64)** | ✅ Phase 1 | `RAGTools-{version}-macos-arm64.tar.gz` | Built on GitHub `macos-14` runners. No `.app` bundle or `.dmg` yet. No login auto-start (G-002). |
| **macOS Intel (x86_64)** | ⚠ Source-only | — | Not produced by CI (G-004). Dev install from source works. |
| **Linux ARM64 (aarch64)** | ✅ v2.5.1+ | `RAGTools-{version}-linux-arm64.tar.gz` | New in ragtools v2.5.1. Follows the same replaceable-app vs persistent-user-data model as macOS. No systemd unit yet. |
| **Linux x86_64** | ⚠ Source-only | — | No packaged x86_64 Linux artifact yet (G-001). Dev install from source works. |

Key platform differences are covered in `paths-and-layout.md` and `risks-and-constraints.md`.

## Prerequisites

### End-user (installer path)
- **Windows installer:** none. Self-contained.
- **macOS tarball:** none, but first launch may require `xattr -cr rag/` to bypass Gatekeeper.

### Developer (source install)
- **Python ≥ 3.10** (Python 3.12 is the tested CI version)
- **Git**
- **pip** (bundled with Python)

### Runtime Python dependencies (from `pyproject.toml`)

| Package | Role |
|---------|------|
| `qdrant-client>=1.12.0` | Embedded vector database |
| `sentence-transformers>=3.0.0` | Embedding model wrapper |
| `typer[all]>=0.12.0` | CLI framework |
| `pydantic>=2.0.0`, `pydantic-settings>=2.0.0` | Config and data models |
| `python-frontmatter>=1.0.0`, `markdown-it-py>=3.0.0` | Markdown parsing |
| `rich>=13.0.0` | CLI output |
| `mcp>=1.26.0` | Claude Code MCP protocol |
| `watchfiles>=1.0.0` | Rust-based file watcher |
| `pathspec>=0.12.0` | gitignore-style pattern matching |
| `tomli-w>=1.0.0` | TOML writing |
| `fastapi>=0.111.0`, `uvicorn[standard]>=0.30.0` | Admin panel service |
| `httpx>=0.27.0` | Service proxy client |
| `jinja2>=3.1.0` | Template rendering |

### Build dependencies
- `pyinstaller>=6.0.0` (`pip install -e ".[build]"`)
- **Inno Setup 6+** for Windows installer compilation (`winget install JRSoftware.InnoSetup`)
- macOS: `tar` for the release tarball. No `create-dmg` yet.

### Test dependencies
`pip install -e ".[dev]"` adds `pytest`, `pytest-cov`, `pytest-asyncio`.

## Installation procedures

### Windows — installer (recommended for end users)

1. Download `RAGTools-Setup-{version}.exe` from the releases page.
2. Double-click. The installer is **user-level** — no admin required.
3. The installer:
   - Copies files to `%LOCALAPPDATA%\Programs\RAGTools\` (default per-user install).
   - Adds the install directory to `HKCU\Environment\Path` if "Add to PATH" is selected.
   - Creates the data directory structure under `%LOCALAPPDATA%\RAGTools\` (`data/`, `logs/`).
   - Installs the smart launcher VBScript (`scripts/launch.vbs`).
   - Registers the Windows Startup folder auto-start task if selected.
   - Optionally starts the service and opens the admin panel immediately.
4. On first run, the service takes ~5–10 seconds to load the embedding model, then the admin panel opens at `http://127.0.0.1:21420`.

### Windows — portable zip

1. Download `RAGTools-{version}-portable.zip`.
2. Extract anywhere (e.g., `C:\Tools\RAGTools\`).
3. Verify: `rag.exe version`.
4. Start manually: `rag.exe service start` (or `rag.exe service run` for foreground).

**Note:** the portable zip does not register startup auto-start or the PATH entry. Manual setup if desired.

### macOS — tarball

1. Download `RAGTools-{version}-macos-arm64.tar.gz` (Apple Silicon required).
2. Extract: `tar -xzf RAGTools-{version}-macos-arm64.tar.gz`
3. Remove Gatekeeper quarantine: `xattr -cr rag/`
4. Verify: `cd rag && ./rag version`
5. Start: `./rag service start` or `./rag service run` for foreground.
6. Open browser to `http://127.0.0.1:21420`.

**macOS login auto-start is not implemented.** See `risks-and-constraints.md` and the gap entry in `gaps.md`.

### Development install from source (all platforms)

```bash
git clone https://github.com/taqat-techno/rag.git
cd rag

python -m venv .venv
# Windows (Git Bash):  source .venv/Scripts/activate
# Windows (CMD):       .venv\Scripts\activate
# macOS / Linux:       source .venv/bin/activate

pip install -e ".[dev]"

rag version
rag doctor

pytest
```

In dev mode, the config file is `./ragtools.toml` (CWD-relative) and data is stored in `./data/`.

### Linux

No pre-built artifact. Use the developer install above. The core code is cross-platform, but startup auto-registration is only implemented for Windows.

## See also

- `post-install-verify.md` — verification checklist after any install
- `paths-and-layout.md` — exactly where files land per platform
- `risks-and-constraints.md` — single-process constraint, MPS rule, bundle size, Syncthing risk
- `gaps.md` — WinGet, signing, Intel macOS, Linux installer gaps
