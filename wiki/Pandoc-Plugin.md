# Pandoc Plugin

**Package:** `pandoc` · **Version:** `2.1.0` · **Category:** productivity · **License:** MIT · **Source:** [`pandoc-plugin/`](../../pandoc-plugin/)

## Purpose

Universal document conversion powered by [Pandoc](https://pandoc.org/). Convert between **50+ input formats and 60+ output formats** with intelligent automation. Handles PDF, Word, HTML, EPUB, presentations (reveal.js / Beamer / PowerPoint), citations, academic papers, and Arabic / RTL documents.

## What it does

- **Auto-detect** Pandoc + LaTeX installation status; run setup if missing.
- **One-shot conversion** from natural-language descriptions ("Convert my thesis to PDF with TOC and bibliography").
- **Format catalog** — list every supported input/output combination Pandoc exposes on the current install.
- **Academic features** — citations, bibliographies, CSL styles, DOI extraction.
- **Presentation generation** — reveal.js with themes (moon, night, black, etc.), Beamer for LaTeX slides, PowerPoint.
- **RTL / Arabic support** — typography and direction-aware output.

## How it works

- **One command** (`/pandoc`) with subcommands — dispatcher model.
- **Natural-language first.** Users describe what they want; the skill figures out Pandoc invocation.
- **Hooks** — advisory only, no blocking behavior.
- **Reference library** — `reference/` holds format compatibility tables, preset configs (academic, report, book), RTL recipes.

## Command

One command with subcommands (consolidated from 8 narrow commands in v2.0):

| Subcommand | Purpose |
|---|---|
| `/pandoc setup` | Install and configure Pandoc + LaTeX (one-time) |
| `/pandoc status` | Check installation, engines, Pandoc version |
| `/pandoc convert` | Convert files between any supported formats |
| `/pandoc formats` | List all supported input/output formats |
| `/pandoc help` | Show usage guide and examples |

All five subcommands share a single `.md` file under `commands/`. The subcommand parser dispatches internally.

## Inputs and outputs

**Inputs:**
- Source file path(s) — single or batch.
- Output format (inferred from target path or stated by user).
- Optional: preset (academic, report, book), theme (reveal.js themes), template, citation style.

**Outputs:**
- Converted document at the specified path.
- PDF with LaTeX-rendered typography (when TeX is installed).
- Structured reveal.js HTML presentations.
- EPUB with cover image + metadata.
- Native Word .docx or .odt.

## Configuration

- **Pandoc** — auto-installed by `/pandoc setup` if missing.
- **LaTeX** — installed by setup (MiKTeX on Windows, MacTeX on macOS, TeX Live on Linux). Required for PDF output; not required for HTML/EPUB/DOCX.
- **Default presets** live in `reference/`; users can override per conversion.

## Dependencies

- **Pandoc 3.0+** (auto-installed).
- **LaTeX distribution** (auto-installed for PDF output).
- **System package manager access** for the auto-install path (Chocolatey/winget on Windows, Homebrew on macOS, apt/dnf on Linux). Manual install is fine too.
- No network egress at runtime — all conversion is local.

## Usage examples

```
"Convert report.md to PDF with TOC"
→ /pandoc convert  (understands the intent)

"Turn these markdown files into a Word document"
→ /pandoc convert  (batch mode)

"Make reveal.js slides from outline.md with the moon theme"
→ /pandoc convert  (reveal.js output + theme)

"Create an EPUB from ch1.md, ch2.md, and ch3.md with a cover image"
→ /pandoc convert  (EPUB + metadata)

"Convert this HTML page to clean Markdown"
→ /pandoc convert  (inverse direction)

"Is Pandoc set up?"
→ /pandoc status
```

## Known limitations

- **PDF requires LaTeX.** No native PDF engine without TeX. Setup handles this but it's a ~1 GB install.
- **Output fidelity depends on Pandoc's format support.** Edge cases (complex .docx formatting, advanced math in reveal.js) may need post-processing.
- **RTL support is pandoc-limited.** Arabic in .docx works well; RTL-in-PDF requires specific XeLaTeX configuration. The skill documents the recipe; Pandoc does the heavy lifting.
- **No live preview.** Conversion is one-shot; interactive preview loops are out of scope.

## Related plugins and integrations

- **paper** — export design docs (Markdown spec + design system) to PDF / Word / HTML using the same `/pandoc convert` workflow.
- **odoo** — convert QWeb reports or email templates between formats during migration.
- Any Markdown-heavy workflow — Pandoc is the universal conversion hub.

## See also

- Source: [`pandoc-plugin/README.md`](../../pandoc-plugin/README.md)
- [Pandoc official documentation](https://pandoc.org/MANUAL.html)
- `pandoc-plugin/reference/` — preset configs, format compatibility tables, RTL recipes
