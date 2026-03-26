---
name: pandoc
description: |
  Universal document conversion skill powered by Pandoc - Convert between 50+ input formats and 60+ output formats. Professional document transformation with templates, citations, math rendering, and batch processing for PDF, Word, HTML, EPUB, LaTeX, and presentations.


  <example>
  Context: User wants to convert a Markdown file to PDF
  user: "Convert my README.md to a professional PDF document"
  assistant: "I will use the pandoc skill to convert the Markdown file to PDF via LaTeX, applying a clean template with proper fonts, margins, and code block formatting."
  <commentary>Core trigger - Markdown to PDF conversion.</commentary>
  </example>

  <example>
  Context: User wants to convert a Word document
  user: "Convert this Word document to clean Markdown"
  assistant: "I will use the pandoc skill to convert the .docx file to Markdown, preserving headings, lists, tables, and images while stripping Word-specific formatting."
  <commentary>Format migration trigger - docx to Markdown.</commentary>
  </example>

  <example>
  Context: User wants to create a presentation
  user: "Create a reveal.js slide presentation from my Markdown outline"
  assistant: "I will use the pandoc skill to convert the Markdown outline to a reveal.js HTML presentation with section separators, speaker notes, and a clean theme."
  <commentary>Presentation trigger - Markdown to slides conversion.</commentary>
  </example>

  <example>
  Context: User needs to install Pandoc or fix PDF generation
  user: "I keep getting pdflatex not found when converting to PDF"
  assistant: "I will use the pandoc skill's setup workflow to install MiKTeX, enable auto-install for LaTeX packages, and pre-install all required packages so PDF generation works without popups."
  <commentary>Setup trigger - installation and configuration.</commentary>
  </example>

  <example>
  Context: User wants batch conversion
  user: "Convert all the .docx files in this folder to Markdown"
  assistant: "I will use the pandoc skill to batch-convert every .docx file in the directory to Markdown, extracting images into a media folder."
  <commentary>Batch processing trigger - multiple file conversion.</commentary>
  </example>
license: "MIT"
metadata:
  mode: "cli-tool"
  pandoc-min-version: "3.0.0"
  model: sonnet
---
<!-- Last updated: 2026-03-26 -->

# Pandoc - Universal Document Converter

## When to Use

Activate when the user needs to:
- **Convert documents** between formats (Markdown → PDF, Word → HTML, etc.)
- **Generate PDFs** from Markdown, HTML, or LaTeX sources
- **Create eBooks** (EPUB) from Markdown or other sources
- **Build presentations** (reveal.js, Beamer, PowerPoint) from Markdown
- **Process citations** with bibliography files
- **Batch convert** multiple files at once
- **Install/configure** Pandoc and LaTeX

---

## Core Workflow

Follow these steps for every conversion request:

### Step 1: Verify Installation

```bash
pandoc --version 2>/dev/null | head -1 || echo "NOT INSTALLED"
```

If not installed, direct the user to run `/pandoc setup`.

For PDF output, also check LaTeX:
```bash
pdflatex --version 2>/dev/null | head -1 || echo "NOT INSTALLED"
```

### Step 2: Detect Formats

Determine the input format from the file extension and the target format from the user's request.

### Step 3: Build and Execute Command

```bash
pandoc [INPUT_FILES] -o OUTPUT_FILE [OPTIONS]
```

### Step 4: Report Result

Show the output file path, size, and the exact command used.

---

## Format Quick Reference

| Target | Extension | Key Flags |
|--------|-----------|-----------|
| PDF | `.pdf` | `--pdf-engine=xelatex` for Unicode/fonts |
| Word | `.docx` | `--reference-doc=template.docx` for styling |
| HTML | `.html` | `-s` (standalone), `--embed-resources` for single-file |
| EPUB | `.epub` | `--epub-cover-image=cover.jpg`, `-t epub3` |
| reveal.js | `.html` | `-t revealjs -s -V theme=moon` |
| Beamer | `.pdf` | `-t beamer -V theme:Warsaw -V aspectratio=169` |
| PowerPoint | `.pptx` | `--reference-doc=template.pptx` |
| LaTeX | `.tex` | `-s` (standalone) |
| Markdown | `.md` | `-t gfm` for GitHub Flavored |
| Plain text | `.txt` | `-t plain` |

### Common Options

| Option | Purpose |
|--------|---------|
| `--toc` | Table of contents |
| `-N` | Number section headings |
| `--citeproc` | Process citations |
| `--bibliography=FILE` | Bibliography source |
| `-V geometry:margin=1in` | Page margins (PDF) |
| `-V fontsize=12pt` | Font size (PDF) |
| `-V mainfont="Font"` | Custom font (requires xelatex) |
| `--highlight-style=tango` | Code syntax highlighting |
| `--extract-media=./media` | Extract images from docx/epub |
| `--wrap=none` | Disable line wrapping |

---

## Setup Flow

When the user needs to install Pandoc, use the `/pandoc setup` command or run the platform-specific installer:

- **Windows**: `powershell -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/pandoc/scripts/setup.ps1"`
- **Linux/macOS**: `bash "${CLAUDE_PLUGIN_ROOT}/pandoc/scripts/setup.sh"`

The setup scripts handle:
1. Installing Pandoc (winget/apt/brew)
2. Installing LaTeX (MiKTeX on Windows, TeX Live on Linux, MacTeX on macOS)
3. Enabling MiKTeX auto-install (Windows) to prevent popup dialogs
4. Pre-installing 30+ required LaTeX packages

---

## Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| `pandoc: command not found` | Not installed | Run `/pandoc setup` |
| `pdflatex not found` | LaTeX missing | Run `/pandoc setup` |
| `*.sty not found` | Missing LaTeX package | `miktex packages install <pkg>` (Windows) or `tlmgr install <pkg>` (Linux) |
| File not found | Wrong path | Check `pwd` and file path |
| Encoding errors | Non-UTF-8 source | Save source as UTF-8 |

---

## Arabic/RTL Essentials

Arabic and RTL content requires XeLaTeX:

```bash
pandoc arabic.md -o output.pdf \
  --pdf-engine=xelatex \
  -V mainfont="Amiri" \
  -V lang=ar \
  -V dir=rtl \
  -V geometry:margin=1in
```

Recommended Arabic fonts: **Amiri** (formal), **Cairo** (modern), **Arial** (fallback).

For HTML RTL output, add `--metadata=lang:ar -V dir=rtl` and include an RTL stylesheet.

---

## Best Practices

1. **Always use `-s`** (standalone) for HTML output to get a complete document
2. **Use `--extract-media=./media`** when converting FROM Word to preserve images
3. **Use `--pdf-engine=xelatex`** for any non-ASCII content or custom fonts
4. **Add `--toc`** for documents longer than 5 pages
5. **Use YAML front matter** in Markdown for title, author, date metadata
6. **Use `--reference-doc`** for consistent Word/PowerPoint styling
7. **Use `--embed-resources`** for portable single-file HTML
8. **Batch convert** with shell loops: `for f in *.md; do pandoc "$f" -o "${f%.md}.pdf"; done`

---

## Additional Reference

For detailed format-specific best practices (PDF presets, EPUB specs, Arabic templates, etc.), see the reference guide at `${CLAUDE_PLUGIN_ROOT}/reference/format_guide.md`.

For complete Pandoc documentation: https://pandoc.org/MANUAL.html
