---
title: 'Pandoc PDF'
read_only: false
type: 'command'
description: 'Convert documents to professional PDF format with table of contents, numbered sections, citations, and custom styling.'
---

# /pandoc-pdf - PDF Document Generation

Generate professional PDF documents from Markdown, HTML, LaTeX, or other formats.

## Usage

```
/pandoc-pdf <input-file> [options]
/pandoc-pdf document.md
/pandoc-pdf document.md --toc --numbered
/pandoc-pdf paper.md --citations --bibliography=refs.bib
```

## Requirements

PDF generation requires a LaTeX distribution:
- **Windows**: MiKTeX or TeX Live
- **macOS**: BasicTeX or MacTeX
- **Linux**: texlive-xetex

---

## Complete Workflow

### Step 1: Validate Prerequisites

```bash
# Check Pandoc
pandoc --version

# Check LaTeX
pdflatex --version
# or
xelatex --version
```

**If LaTeX not found, guide installation:**

```
[WARNING] LaTeX is required for PDF generation.

Install with:
  Windows:  choco install miktex -y
  macOS:    brew install --cask basictex
  Linux:    sudo apt install texlive-xetex

Or use TinyTeX (minimal):
  https://yihui.org/tinytex/
```

### Step 2: Gather Requirements

Ask user for preferences if not specified:

```
============================================================
                    PDF GENERATION OPTIONS
============================================================

INPUT FILE: document.md

OPTIONS (respond with numbers or skip for defaults):

  [1] Table of Contents
      □ No TOC (default)
      ■ Include TOC (--toc)

  [2] Section Numbering
      □ No numbering (default)
      ■ Numbered sections (-N)

  [3] Paper Size
      ■ A4 (default)
      □ Letter
      □ Legal

  [4] Margins
      ■ 1 inch (default)
      □ 0.75 inch
      □ 1.25 inch
      □ Custom

  [5] Font Size
      □ 10pt
      □ 11pt
      ■ 12pt (default)

  [6] Citations
      □ No citations (default)
      ■ Process citations (--citeproc)

Press Enter for defaults or specify options:
============================================================
```

### Step 3: Build Command

Based on user input, construct the pandoc command:

```bash
# Basic conversion
pandoc input.md -o output.pdf

# With common options
pandoc input.md \
  --toc \
  --toc-depth=3 \
  -N \
  -V geometry:margin=1in \
  -V fontsize=12pt \
  -V papersize=a4 \
  -o output.pdf

# Academic paper
pandoc paper.md \
  --citeproc \
  --bibliography=refs.bib \
  --csl=ieee.csl \
  --toc \
  -N \
  -V geometry:margin=1in \
  --pdf-engine=xelatex \
  -o paper.pdf
```

### Step 4: Execute Conversion

```bash
# Run the command
pandoc [constructed-command]
```

### Step 5: Report Results

**Success:**

```
============================================================
              PDF GENERATION SUCCESSFUL
============================================================

INPUT:     document.md (15 KB)
OUTPUT:    document.pdf (142 KB)
PAGES:     8

OPTIONS APPLIED:
  ✓ Table of Contents (depth: 3)
  ✓ Numbered Sections
  ✓ Paper: A4
  ✓ Margins: 1 inch
  ✓ Font Size: 12pt

OUTPUT FILE: C:\Users\ahmed\Documents\document.pdf

============================================================
```

**Error:**

```
[ERROR] PDF generation failed.

Error: pdflatex not found

SOLUTION:
Install LaTeX with: choco install miktex

Or try HTML output instead:
  pandoc document.md -o document.html
```

---

## Options Reference

### Basic Options

| Option | Description | Example |
|--------|-------------|---------|
| `--toc` | Include table of contents | `--toc` |
| `--toc-depth=N` | TOC depth (1-6) | `--toc-depth=2` |
| `-N, --number-sections` | Number section headings | `-N` |
| `-o FILE` | Output file | `-o output.pdf` |

### Page Layout

| Option | Description | Example |
|--------|-------------|---------|
| `-V papersize=SIZE` | Paper size | `-V papersize=a4` |
| `-V geometry:margin=X` | Page margins | `-V geometry:margin=1in` |
| `-V geometry:top=X` | Top margin | `-V geometry:top=2cm` |
| `-V geometry:bottom=X` | Bottom margin | `-V geometry:bottom=2cm` |
| `-V geometry:left=X` | Left margin | `-V geometry:left=2.5cm` |
| `-V geometry:right=X` | Right margin | `-V geometry:right=2.5cm` |

### Typography

| Option | Description | Example |
|--------|-------------|---------|
| `-V fontsize=SIZE` | Font size | `-V fontsize=12pt` |
| `-V mainfont=FONT` | Main font (XeLaTeX) | `-V mainfont="Times New Roman"` |
| `-V sansfont=FONT` | Sans-serif font | `-V sansfont="Arial"` |
| `-V monofont=FONT` | Monospace font | `-V monofont="Consolas"` |
| `-V linestretch=N` | Line spacing | `-V linestretch=1.5` |

### Document Class

| Option | Description | Example |
|--------|-------------|---------|
| `-V documentclass=CLASS` | LaTeX document class | `-V documentclass=report` |
| `-V classoption=OPT` | Class options | `-V classoption=twocolumn` |

**Document Classes**:
- `article` - Short documents (default)
- `report` - Longer documents with chapters
- `book` - Books with front/back matter
- `memoir` - Flexible document class
- `scrartcl` - KOMA-Script article

### PDF Engine

| Option | Description | Use Case |
|--------|-------------|----------|
| `--pdf-engine=pdflatex` | Standard LaTeX | Default, fast |
| `--pdf-engine=xelatex` | XeTeX | Unicode, custom fonts |
| `--pdf-engine=lualatex` | LuaTeX | Advanced features |
| `--pdf-engine=tectonic` | Tectonic | Minimal setup |
| `--pdf-engine=wkhtmltopdf` | Via HTML | No LaTeX needed |

### Citations

| Option | Description | Example |
|--------|-------------|---------|
| `--citeproc` | Process citations | `--citeproc` |
| `--bibliography=FILE` | Bibliography file | `--bibliography=refs.bib` |
| `--csl=FILE` | Citation style | `--csl=ieee.csl` |

### Code Highlighting

| Option | Description | Example |
|--------|-------------|---------|
| `--highlight-style=STYLE` | Code highlighting | `--highlight-style=tango` |
| `--no-highlight` | Disable highlighting | `--no-highlight` |
| `--listings` | Use listings package | `--listings` |

**Highlight Styles**: `pygments`, `tango`, `espresso`, `zenburn`, `kate`, `monochrome`, `breezeDark`, `haddock`

---

## Preset Configurations

### `/pandoc-pdf document.md --preset academic`

```bash
pandoc document.md \
  --toc \
  --toc-depth=3 \
  -N \
  --citeproc \
  --bibliography=references.bib \
  -V geometry:margin=1in \
  -V fontsize=12pt \
  -V linestretch=1.5 \
  --pdf-engine=xelatex \
  -o document.pdf
```

### `/pandoc-pdf document.md --preset report`

```bash
pandoc document.md \
  -V documentclass=report \
  --toc \
  -N \
  -V geometry:margin=1in \
  -V fontsize=11pt \
  -o document.pdf
```

### `/pandoc-pdf document.md --preset article`

```bash
pandoc document.md \
  -V documentclass=article \
  -V fontsize=11pt \
  -V geometry:margin=1in \
  -o document.pdf
```

### `/pandoc-pdf document.md --preset book`

```bash
pandoc document.md \
  -V documentclass=book \
  --toc \
  -N \
  -V geometry:margin=1in \
  -V fontsize=11pt \
  -V classoption=openright \
  -o document.pdf
```

### `/pandoc-pdf document.md --preset minimal`

```bash
pandoc document.md -o document.pdf
```

---

## Examples

### Example 1: Simple PDF

**User**: `/pandoc-pdf report.md`

**Claude executes**:
```bash
pandoc report.md -o report.pdf
```

**Output**:
```
[OK] PDF generated: report.pdf (45 KB, 3 pages)
```

### Example 2: Academic Paper

**User**: `/pandoc-pdf thesis.md --toc --numbered --citations`

**Claude executes**:
```bash
pandoc thesis.md \
  --toc \
  --toc-depth=3 \
  -N \
  --citeproc \
  --bibliography=references.bib \
  -V geometry:margin=1in \
  -V fontsize=12pt \
  -V linestretch=1.5 \
  --pdf-engine=xelatex \
  -o thesis.pdf
```

### Example 3: Custom Fonts

**User**: "Create PDF with Times New Roman font"

**Claude executes**:
```bash
pandoc document.md \
  --pdf-engine=xelatex \
  -V mainfont="Times New Roman" \
  -V fontsize=12pt \
  -o document.pdf
```

### Example 4: Two-Column Layout

**User**: "Generate two-column PDF article"

**Claude executes**:
```bash
pandoc article.md \
  -V documentclass=article \
  -V classoption=twocolumn \
  -V fontsize=10pt \
  -o article.pdf
```

### Example 5: Multiple Files

**User**: "Combine chapters into single PDF"

**Claude executes**:
```bash
pandoc \
  title.md \
  ch1.md \
  ch2.md \
  ch3.md \
  conclusion.md \
  --toc \
  -N \
  -V documentclass=report \
  -o book.pdf
```

---

## Troubleshooting

### LaTeX Not Found

```
[ERROR] pdflatex not found

PDF generation requires LaTeX. Install with:

  Windows:
    choco install miktex -y

  macOS:
    brew install --cask basictex

  Linux:
    sudo apt install texlive-xetex

Alternative without LaTeX:
  pandoc document.md --pdf-engine=wkhtmltopdf -o document.pdf
  (Requires wkhtmltopdf installation)
```

### Missing Font

```
[ERROR] Font "Arial" not found

Solutions:
1. Install the font on your system
2. Use a standard font: -V mainfont="DejaVu Sans"
3. Use pdflatex instead of xelatex (uses LaTeX fonts)
```

### Unicode Issues

```
[ERROR] Package inputenc Error: Unicode character not set up

Solution: Use XeLaTeX or LuaLaTeX:
  pandoc document.md --pdf-engine=xelatex -o document.pdf
```

### Missing LaTeX Package

```
[ERROR] File 'xxx.sty' not found

Solution (MiKTeX - auto installs):
  Just re-run the command, MiKTeX will install

Solution (TeX Live):
  tlmgr install xxx
```

---

## YAML Front Matter for PDF

Include in your Markdown file:

```yaml
---
title: "Document Title"
author: "Author Name"
date: "January 15, 2025"
abstract: |
  This is the abstract of the document.
  It can span multiple lines.

# PDF Options
geometry:
  - margin=1in
fontsize: 12pt
linestretch: 1.5
documentclass: article

# Table of Contents
toc: true
toc-depth: 3
numbersections: true

# Bibliography
bibliography: references.bib
csl: ieee.csl

# Header/Footer
header-includes:
  - \usepackage{fancyhdr}
  - \pagestyle{fancy}
  - \fancyhead[L]{My Document}
  - \fancyhead[R]{\thepage}
---
```

---

## Related Commands

| Command | Description |
|---------|-------------|
| `/pandoc` | Main help and status |
| `/pandoc-docx` | Convert to Word |
| `/pandoc-html` | Convert to HTML |
| `/pandoc-slides` | Create slides (Beamer PDF) |
| `/pandoc-convert` | General conversion |

---

*Pandoc Plugin v1.0*
*Professional PDF Generation*
