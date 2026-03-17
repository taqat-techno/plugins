---
description: 'Universal document converter — setup, convert, status, and help for 50+ formats'
argument-hint: '[setup|status|convert|formats|help] [args...]'
---

# /pandoc - Universal Document Converter

Single entry point for all Pandoc operations: setup, conversion, status checks, and help.

---

## Routing

Parse `$ARGUMENTS` and dispatch:

| Input | Sub-command |
|-------|-------------|
| *(empty)* | [help](#no-args--help) |
| `help [topic]` | [help](#no-args--help) |
| `setup` | [setup](#setup) |
| `status` | [status](#status) |
| `convert <file> <fmt> [opts]` | [convert](#convert) |
| `formats` | [formats](#formats) |

---

## No args / help

When the user runs `/pandoc` or `/pandoc help [topic]`, do the following:

### Step 1: Quick status probe

```bash
pandoc --version 2>/dev/null | head -1 || echo "NOT INSTALLED"
pdflatex --version 2>/dev/null | head -1 || echo "NOT INSTALLED"
```

### Step 2: Display overview

```
==========================================================
          PANDOC - UNIVERSAL DOCUMENT CONVERTER
==========================================================

Status:  Pandoc ............. {version or NOT INSTALLED}
         LaTeX .............. {version or NOT INSTALLED}

SUB-COMMANDS:
  /pandoc setup            Install & configure Pandoc + LaTeX
  /pandoc status           Detailed installation report
  /pandoc convert F FMT    Convert file F to format FMT
  /pandoc formats          List all supported formats
  /pandoc help <topic>     Deep-dive on a topic

POPULAR CONVERSIONS:
  /pandoc convert report.md pdf
  /pandoc convert report.md docx
  /pandoc convert doc.docx md
  /pandoc convert slides.md revealjs --theme=moon
  /pandoc convert book.md epub --cover=cover.jpg

COMMON OPTIONS:
  --toc                    Table of contents
  -N, --number-sections    Numbered headings
  --citeproc               Process citations
  --bibliography=refs.bib  Bibliography file
  --template=FILE          Custom template
  --highlight-style=NAME   Code highlighting (tango, kate, ...)
  --mathjax / --katex      Math rendering

HELP TOPICS (/pandoc help <topic>):
  pdf        PDF generation & LaTeX engines
  docx       Word document options
  html       Standalone HTML pages
  epub       eBook creation
  slides     Reveal.js, Beamer, PPTX presentations
  citations  Bibliography & citeproc
  batch      Converting multiple files at once
  arabic     RTL / Arabic document tips
==========================================================
```

### Step 3: Topic-specific help

If a topic is given (`/pandoc help pdf`, etc.), provide focused guidance:

**pdf** - Engines (`--pdf-engine=xelatex|lualatex|pdflatex`), margins (`-V geometry:margin=1in`), fonts (`-V mainfont="..."`), TOC, page breaks.

**docx** - Reference doc (`--reference-doc=template.docx`), styles, metadata (`-M title="..."`).

**html** - Standalone (`-s`), CSS (`--css=style.css`), self-contained (`--embed-resources --standalone`), math.

**epub** - Cover image (`--epub-cover-image=cover.jpg`), metadata (`--epub-metadata=meta.xml`), CSS, chapters.

**slides** - Reveal.js (`-t revealjs -V theme=moon`), Beamer (`-t beamer`), PPTX (`-o slides.pptx`), slide level (`--slide-level=2`).

**citations** - `--citeproc --bibliography=refs.bib --csl=style.csl`, inline `[@cite]` syntax.

**batch** - Shell loops, glob patterns, Makefile examples for multi-file projects.

**arabic** - XeLaTeX engine required, `polyglossia` or `babel-arabic`, RTL with `\setmainlanguage{arabic}`, font selection (`-V mainfont="Amiri"`).

---

## setup

Full automated installation of Pandoc and LaTeX.

### Step 1: Detect platform

```bash
uname -s 2>/dev/null || echo "Windows"
```

### Step 2: Check what is already installed

```bash
pandoc --version 2>/dev/null | head -1
pdflatex --version 2>/dev/null | head -1
```

### Step 3: Run platform-specific installer

#### Windows

Run the setup PowerShell script:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\TQ-WorkSpace\odoo\tmp\plugins\pandoc-plugin\pandoc\scripts\setup.ps1"
```

The script handles:
1. Install Pandoc via winget (fallback: Chocolatey)
2. Install MiKTeX for PDF support
3. **Enable MiKTeX auto-install** (`AutoInstall=1`) so LaTeX packages install silently -- no popup dialogs
4. Pre-install 30+ required LaTeX packages (parskip, geometry, fancyvrb, framed, booktabs, longtable, hyperref, listings, amsmath, xcolor, graphicx, etc.)
5. Configure PATH

If the script is unavailable, fall back to manual commands:

```powershell
# 1. Pandoc
winget install JohnMacFarlane.Pandoc --accept-package-agreements --accept-source-agreements

# 2. MiKTeX
winget install MiKTeX.MiKTeX --accept-package-agreements --accept-source-agreements

# 3. Enable auto-install (CRITICAL -- prevents popup dialogs)
& "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64\initexmf.exe" --set-config-value="[MPM]AutoInstall=1"

# 4. Pre-install packages
$pkgs = @('parskip','geometry','fancyvrb','framed','booktabs','longtable',
          'upquote','microtype','bookmark','etoolbox','hyperref','ulem',
          'listings','caption','float','setspace','amsmath','lm','xcolor',
          'graphicx','adjustbox','collectbox','enumitem','footmisc',
          'mdframed','needspace','pagecolor','sourcecodepro','sourcesanspro',
          'titling','zref')
foreach ($p in $pkgs) {
    & "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64\miktex.exe" packages install $p
}
```

#### Linux (Debian/Ubuntu)

```bash
bash "C:/TQ-WorkSpace/odoo/tmp/plugins/pandoc-plugin/pandoc/scripts/setup.sh"
```

Or manually:

```bash
sudo apt update && sudo apt install -y pandoc texlive texlive-latex-extra texlive-fonts-recommended texlive-xetex
```

#### Linux (Fedora)

```bash
sudo dnf install -y pandoc texlive-xetex texlive-collection-latexextra
```

#### macOS

```bash
brew install pandoc
brew install --cask mactex   # Full LaTeX -- or basictex for minimal
```

### Step 4: Verify installation

```bash
pandoc --version | head -1
pdflatex --version 2>/dev/null | head -1
echo "# Test" | pandoc -o /tmp/_pandoc_test.pdf && echo "PDF OK" && rm /tmp/_pandoc_test.pdf
```

### Step 5: Report result

```
==========================================================
              PANDOC SETUP COMPLETE
==========================================================

Pandoc:    {version}
LaTeX:     {version}
Auto-install: Enabled (no popup dialogs)

Next steps:
  /pandoc convert yourfile.md pdf
  /pandoc status    (detailed report)
==========================================================
```

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| `pandoc: command not found` | Restart terminal, or add to PATH: `$env:LOCALAPPDATA\Pandoc` |
| `pdflatex: command not found` | Add MiKTeX to PATH: `$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64` |
| MiKTeX popup still appears | Re-run: `initexmf.exe --set-config-value="[MPM]AutoInstall=1"` |
| `parskip.sty not found` | Install package: `miktex packages install parskip` |

---

## status

Detailed installation and capability report.

### Step 1: Gather info

```bash
# Pandoc
pandoc --version 2>/dev/null
which pandoc 2>/dev/null || where pandoc 2>/dev/null

# LaTeX engines
pdflatex --version 2>/dev/null | head -1
xelatex --version 2>/dev/null | head -1
lualatex --version 2>/dev/null | head -1

# MiKTeX auto-install (Windows)
initexmf --show-config-value="[MPM]AutoInstall" 2>/dev/null

# Format counts
pandoc --list-input-formats 2>/dev/null | wc -l
pandoc --list-output-formats 2>/dev/null | wc -l
pandoc --list-highlight-styles 2>/dev/null | wc -l
```

### Step 2: Display report

```
==========================================================
              PANDOC INSTALLATION STATUS
==========================================================

PANDOC:
  Installed:        {YES/NO}
  Version:          {x.x.x}
  Location:         {path}

PDF ENGINES:
  pdflatex:         {Available / Not found}
  xelatex:          {Available / Not found}
  lualatex:         {Available / Not found}

MIKTEX (Windows):
  Auto-install:     {Enabled (1) / Disabled (0) / N/A}

CAPABILITIES:
  Input Formats:    {count}
  Output Formats:   {count}
  Highlight Styles: {count}

OPTIONAL TOOLS:
  pandoc-crossref:  {version / Not installed}
  citeproc:         Built-in (--citeproc)

RECOMMENDATIONS:
  {Contextual advice based on what is missing}
==========================================================
```

If Pandoc is not installed, show install instructions and suggest `/pandoc setup`.

---

## convert

Explicit file conversion: `/pandoc convert <file> <format> [options]`

### Step 1: Parse arguments

Extract from `$ARGUMENTS` (after stripping the `convert` keyword):
- `<file>` -- input file path (required, supports globs like `chapters/*.md`)
- `<format>` -- target format (required): `pdf`, `docx`, `html`, `epub`, `revealjs`, `beamer`, `pptx`, `md`, `rst`, `latex`, `plain`, `odt`, `rtf`, etc.
- `[options]` -- any remaining flags passed through to pandoc

### Step 2: Validate

```bash
# Check pandoc exists
pandoc --version > /dev/null 2>&1 || { echo "[ERROR] Pandoc not installed. Run: /pandoc setup"; exit 1; }

# Check input file exists
[ -f "$INPUT_FILE" ] || { echo "[ERROR] File not found: $INPUT_FILE"; exit 1; }

# For PDF: check LaTeX
if [ "$FORMAT" = "pdf" ]; then
    pdflatex --version > /dev/null 2>&1 || echo "[WARN] LaTeX not found. PDF may fail. Run: /pandoc setup"
fi
```

### Step 3: Build and run command

Map format to output extension and pandoc flags:

| Format | Extension | Extra flags |
|--------|-----------|-------------|
| `pdf` | `.pdf` | *(none, or `--pdf-engine=xelatex` for Unicode/Arabic)* |
| `docx` | `.docx` | |
| `html` | `.html` | `-s` (standalone) |
| `epub` | `.epub` | |
| `revealjs` | `.html` | `-t revealjs -s` |
| `beamer` | `.pdf` | `-t beamer` |
| `pptx` | `.pptx` | |
| `md` | `.md` | `-t gfm` |
| `rst` | `.rst` | |
| `latex` / `tex` | `.tex` | `-s` |
| `odt` | `.odt` | |
| `rtf` | `.rtf` | |
| `plain` / `txt` | `.txt` | `-t plain` |

Construct the output filename by replacing the input extension with the target extension. Then run:

```bash
pandoc "$INPUT_FILE" -o "$OUTPUT_FILE" $USER_OPTIONS
```

Append any user-provided options (`--toc`, `--citeproc`, `--bibliography=...`, `--theme=...`, `--cover=...`, `-N`, etc.) verbatim.

### Step 4: Report

```
Converted: report.md -> report.pdf
Size:      142 KB
Command:   pandoc report.md -o report.pdf --toc -N
```

### Examples

```
/pandoc convert report.md pdf
/pandoc convert report.md pdf --toc --citeproc --bibliography=refs.bib
/pandoc convert slides.md revealjs --theme=moon
/pandoc convert chapters/*.md epub --cover=cover.jpg
/pandoc convert document.docx md
/pandoc convert paper.md pdf --pdf-engine=xelatex -V mainfont="Amiri"
/pandoc convert notes.md html --css=style.css --embed-resources --standalone
/pandoc convert thesis.md latex -s --toc -N
```

### Multi-file input

When a glob or multiple files are provided, concatenate them:

```bash
pandoc chapters/01.md chapters/02.md chapters/03.md -o book.pdf --toc
```

---

## formats

List all supported input and output formats.

### Implementation

```bash
echo "INPUT FORMATS:"
pandoc --list-input-formats 2>/dev/null | column
echo ""
echo "OUTPUT FORMATS:"
pandoc --list-output-formats 2>/dev/null | column
```

Display as a categorized table:

```
==========================================================
                PANDOC SUPPORTED FORMATS
==========================================================

INPUT FORMATS:
  Markdown:   commonmark, commonmark_x, gfm, markdown,
              markdown_mmd, markdown_phpextra, markdown_strict
  Documents:  docx, odt, rtf, epub
  Web:        html, html5
  Technical:  latex, rst, asciidoc, asciidoctor, docbook,
              jats, t2t, typst
  Wiki:       mediawiki, dokuwiki, tikiwiki, twiki, jira,
              vimwiki
  Data:       csv, tsv, json, bibtex, biblatex, endnotexml,
              ris
  Notebook:   ipynb (Jupyter)
  Other:      creole, fb2, haddock, man, muse, org, textile

OUTPUT FORMATS:
  Documents:  docx, odt, rtf, pdf (via LaTeX/engine)
  Web:        html, html5, epub, epub2, epub3
  Slides:     beamer, revealjs, pptx, slidy, s5, dzslides
  Technical:  latex, context, rst, asciidoc, asciidoctor,
              docbook4, docbook5, jats, jats_archiving,
              jats_articleauthoring, jats_publishing, tei,
              typst, texinfo
  Wiki:       mediawiki, dokuwiki, jira, xwiki, zimwiki
  Plain:      plain, gfm, commonmark, markdown, org, man, ms
  Other:      icml, opml, fb2, haddock, ipynb, markua,
              textile, slideous, chunkedhtml

==========================================================
```

---

## Error Handling

All sub-commands share these error patterns:

### Pandoc not installed

```
[ERROR] Pandoc is not installed.

Run:  /pandoc setup

Or install manually:
  Windows:  winget install JohnMacFarlane.Pandoc
  macOS:    brew install pandoc
  Linux:    sudo apt install pandoc
```

### File not found

```
[ERROR] File not found: {path}

Current directory: {cwd}
Check the path and try again.
```

### LaTeX not installed (PDF only)

```
[ERROR] PDF generation requires a LaTeX engine.

Run:  /pandoc setup

Or install manually:
  Windows:  winget install MiKTeX.MiKTeX
  macOS:    brew install --cask mactex
  Linux:    sudo apt install texlive-xetex

Alternative: convert to HTML instead:
  /pandoc convert {file} html
```

### Missing LaTeX package

```
[ERROR] LaTeX package missing: {package}.sty

Fix:
  Windows (MiKTeX):  miktex packages install {package}
  Linux (TeX Live):  tlmgr install {package}

Or run /pandoc setup to pre-install all common packages.
```

---

## Natural Language Support

The `/pandoc` command understands natural language. Map intent to sub-commands:

| User says | Action |
|-----------|--------|
| "Convert report.md to PDF" | `/pandoc convert report.md pdf` |
| "Turn this docx into markdown" | `/pandoc convert file.docx md` |
| "Make slides from presentation.md" | `/pandoc convert presentation.md revealjs` |
| "Create an eBook" | `/pandoc convert file.md epub` |
| "Is pandoc installed?" | `/pandoc status` |
| "Install pandoc" | `/pandoc setup` |
| "What formats are supported?" | `/pandoc formats` |
| "Help with citations" | `/pandoc help citations` |

---

> Previously available as separate commands: `/pandoc-pdf`, `/pandoc-docx`, `/pandoc-html`,
> `/pandoc-epub`, `/pandoc-slides`, `/pandoc-convert`, `/pandoc-setup`.
> All functionality is now in `/pandoc` or handled by the skill via natural language.

---

*Pandoc Plugin v2.0 - Unified Command Interface*
