# pandoc

## What it does

Teaches Claude to convert documents with [Pandoc](https://pandoc.org/):
Markdown, Word, HTML, LaTeX, reStructuredText, EPUB, PDF and slide decks, with
citations, batch conversion and Arabic/RTL PDF support. It checks the
installation first, asks before overwriting an existing output, and installs
Pandoc or LaTeX only with your consent.

For anyone who converts documents from Claude Code: writers, developers,
academics.

## Install

```
/plugin marketplace add taqat-techno/plugins
/plugin install pandoc@taqat-techno-plugins
```

## Requirements

| Requirement | Needed for | Check |
|---|---|---|
| Pandoc 3.0+ | every conversion | `pandoc --version` |
| A LaTeX engine (MiKTeX, TeX Live, MacTeX/BasicTeX) | PDF output via LaTeX only | `pdflatex --version` or `xelatex --version` |
| Windows PowerShell 5.1 + winget | the Windows installer | `winget --version` |
| bash + apt-get / dnf / pacman / brew | the Linux/macOS installer | `bash --version` |

`/pandoc:setup` checks all of these and prints the install commands.

## Commands

| Command | Description |
|---|---|
| `/pandoc:convert <file> <format> [opts]` | Convert a document. No arguments: usage guide and examples. |
| `/pandoc:setup [--skip-latex]` | Check-only run of the installer; shows install commands and sizes, installs only on your explicit request |
| `/pandoc:status` | Pandoc version and available PDF engines |
| `/pandoc:formats` | Input and output formats of the installed Pandoc |
| `/pandoc` | Deprecated alias that routes to the commands above; removed in the next minor version |

## Skills

| Skill | Loads when |
|---|---|
| `pandoc-conversion` | Converting between document formats, PDF/slides/EPUB output, citations, batch conversion, Arabic/RTL PDFs, "pdflatex not found" and other Pandoc/LaTeX setup errors. Model-invoked only (`user-invocable: false`). |

## Agents

None.

## Hooks

None. The plugin ships no hooks.

## Installers

| Script | Behaviour |
|---|---|
| `skills/pandoc-conversion/scripts/setup.ps1` | Windows. Flags: `-SkipLatex`, `-Quiet`, `-PrintOnly`, `-Install`, `-EnableAutoInstall`. |
| `skills/pandoc-conversion/scripts/setup.sh` | Linux/macOS (and prints winget commands under Git Bash). Flags: `--skip-latex`, `--quiet`, `--print-only`, `--install`. |

Both:

- check first, and when stdin is not a terminal (as when Claude runs them)
  only print the install commands, then exit 0;
- run package managers without `-y`, `--noconfirm` or winget `--accept-*`
  flags, so you accept licence terms and `sudo` prompts yourself;
- exit 1 when an install they ran did not complete: Pandoc, or LaTeX unless
  you passed `-SkipLatex` / `--skip-latex` (a check-only run exits 0).

On Windows the installer is started with `-ExecutionPolicy Bypass`, which applies
only to that one PowerShell process and leaves your execution policy unchanged.

`-EnableAutoInstall` (Windows) turns on MiKTeX's on-the-fly package downloads
(`[MPM]AutoInstall=1`, a persistent per-user MiKTeX setting) and pre-installs
about 30 common LaTeX packages. It is never enabled by default.

Approximate sizes: Pandoc tens of MB; MiKTeX basic about 140 MB; TeX Live with
the listed extras 0.5-1 GB; MacTeX about 5 GB (`setup.sh` suggests the ~100 MB
BasicTeX instead).

## Configuration

None. No userConfig, no environment variables. Templates and reference
documents are passed per conversion (`--template`, `--reference-doc`).

## Platform support

| Platform | Status |
|---|---|
| Windows | Supported. Installer covers x64 MiKTeX paths; ARM64 MiKTeX is not probed. |
| macOS | Supported via Homebrew. |
| Linux | Supported via apt-get, dnf or pacman. |
| WSL | Works as Linux. |
| Git Bash on Windows | `setup.sh` prints the winget commands and installs nothing. |

## Data & privacy

- Conversions run locally; the plugin sends nothing anywhere.
- Installing downloads Pandoc and LaTeX from your package manager's sources. With
  MiKTeX AutoInstall enabled, MiKTeX downloads LaTeX packages during later
  conversions.
- For documents from untrusted sources the skill adds `--sandbox`, so the
  document cannot make Pandoc read other local files or fetch URLs, and treats
  text inside documents as data, never as instructions.
- Output files are written where you ask; an existing output is not overwritten
  without your confirmation.

## Limitations

- No bundled templates or presets (PDC-P3-10, deferred); pass your own with
  `--template` / `--reference-doc`.
- PDF output needs a LaTeX engine (or another `--pdf-engine` you install).
- `--sandbox` needs Pandoc 2.15 or later.
- Installing from Claude's shell usually cannot answer licence or `sudo`
  prompts; run the printed commands in your own terminal.

## License

MIT (see `LICENSE`).

Third-party software the installers fetch has its own licences: Pandoc is
GPL-2.0-or-later; MiKTeX, TeX Live and MacTeX are collections of free-software
packages under various licences.

Credits: Pandoc by John MacFarlane, https://pandoc.org/. Plugin by TAQAT
Techno, https://www.taqatechno.com/.
