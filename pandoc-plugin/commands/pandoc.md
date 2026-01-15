---
title: 'Pandoc'
read_only: false
type: 'command'
description: 'Universal document converter - Convert between 50+ input formats and 60+ output formats. Main entry point with help and status.'
---

# Pandoc - Universal Document Converter

Main entry point for the Pandoc plugin. Provides help, status, and quick conversion capabilities.

---

## FIRST TIME? Run Setup First!

Before using Pandoc commands, run the automated setup:

```
/pandoc-setup
```

This one command will:
- Install Pandoc (if needed)
- Install LaTeX/MiKTeX (for PDF generation)
- Configure auto-install (no popup dialogs!)
- Pre-install all required packages

**Without setup, you may encounter:**
- `pandoc: command not found`
- MiKTeX popup dialogs asking to install packages
- `parskip.sty not found` errors

---

## Sub-Commands

| Sub-Command | Description |
|-------------|-------------|
| `/pandoc` | Show capabilities overview and quick help |
| `/pandoc-setup` | **One-click install & configure (RUN FIRST!)** |
| `/pandoc status` | Check Pandoc installation and version |
| `/pandoc help [topic]` | Detailed help on specific topics |
| `/pandoc formats` | List all supported formats |
| `/pandoc quick <file>` | Quick convert with auto-detected output |

---

## `/pandoc` - Capabilities Overview

When user runs `/pandoc` without arguments, display:

```
============================================================
            PANDOC - UNIVERSAL DOCUMENT CONVERTER
============================================================

Pandoc converts documents between virtually ANY format.
50+ input formats | 60+ output formats | Professional quality

QUICK CONVERSIONS:
  /pandoc-pdf <file>        Convert to PDF (requires LaTeX)
  /pandoc-docx <file>       Convert to Microsoft Word
  /pandoc-html <file>       Convert to HTML web page
  /pandoc-epub <file>       Create EPUB eBook
  /pandoc-slides <file>     Create presentation slides
  /pandoc-convert           General format conversion

POPULAR CONVERSIONS:
  Markdown → PDF            pandoc input.md -o output.pdf
  Markdown → Word           pandoc input.md -o output.docx
  Word → Markdown           pandoc input.docx -o output.md
  Markdown → HTML           pandoc -s input.md -o output.html
  Markdown → EPUB           pandoc input.md -o output.epub

FEATURES:
  • Table of Contents       --toc
  • Numbered Sections       -N, --number-sections
  • Citations               --citeproc --bibliography=refs.bib
  • Custom Templates        --template=template.tex
  • Math Rendering          --mathjax, --katex
  • Syntax Highlighting     --highlight-style=tango

TYPE /pandoc help <topic> FOR DETAILED HELP:
  formats   - All supported formats
  pdf       - PDF generation options
  templates - Using custom templates
  citations - Bibliography and citations
  slides    - Presentation creation
  batch     - Batch processing

============================================================
```

---

## `/pandoc status` - Installation Check

### Implementation

**Step 1: Check Pandoc Installation**

```bash
pandoc --version
```

**Step 2: Parse and Report**

```
============================================================
                  PANDOC INSTALLATION STATUS
============================================================

PANDOC:
  Installed:           YES
  Version:             3.7.0.1
  Location:            C:\Users\ahmed\AppData\Local\Pandoc
  Compiled with:       ghc-9.4.8

PDF SUPPORT:
  LaTeX Engine:        pdflatex (MiKTeX 24.1)
  XeLaTeX:             Available
  LuaLaTeX:            Available

OPTIONAL TOOLS:
  pandoc-crossref:     Not Installed
  pandoc-citeproc:     Built-in (--citeproc)

CAPABILITIES:
  Input Formats:       52
  Output Formats:      65
  Extensions:          80+
  Highlight Styles:    12

RECOMMENDATIONS:
  ✓ Pandoc is ready for document conversion
  ✓ PDF generation available (LaTeX installed)
  ○ Consider installing pandoc-crossref for
    advanced cross-references

============================================================
```

### Status When Not Installed

```
============================================================
                  PANDOC INSTALLATION STATUS
============================================================

PANDOC:
  Installed:           NO

To install Pandoc, run:

  Windows (Chocolatey):
    choco install pandoc

  Windows (Winget):
    winget install JohnMacFarlane.Pandoc

  macOS (Homebrew):
    brew install pandoc

  Linux (Debian/Ubuntu):
    sudo apt install pandoc

  Linux (Fedora):
    sudo dnf install pandoc

Or download from: https://github.com/jgm/pandoc/releases

============================================================
```

---

## `/pandoc setup` - Installation

### Implementation

**Step 1: Detect Platform**

```bash
# Windows
echo $env:OS
# or
echo %OS%

# macOS/Linux
uname -s
```

**Step 2: Install Based on Platform**

#### Windows Installation

```powershell
# Try winget first (Windows 10/11)
winget install --source winget --exact --id JohnMacFarlane.Pandoc

# Or Chocolatey
choco install pandoc -y

# For PDF support
choco install miktex -y
```

#### macOS Installation

```bash
# Homebrew
brew install pandoc

# For PDF support
brew install --cask basictex
```

#### Linux Installation

```bash
# Debian/Ubuntu
sudo apt update && sudo apt install -y pandoc texlive-xetex

# Fedora
sudo dnf install -y pandoc texlive-xetex
```

**Step 3: Verify Installation**

```bash
pandoc --version
```

**Step 4: Report Success**

```
============================================================
              PANDOC INSTALLATION COMPLETE
============================================================

Pandoc has been successfully installed!

Version:    3.7.0.1
Location:   [PATH]

NEXT STEPS:

1. Test with a simple conversion:
   pandoc --version

2. Try converting a file:
   /pandoc-pdf your-document.md

3. For PDF generation, ensure LaTeX is installed:
   - Windows: choco install miktex
   - macOS: brew install --cask basictex
   - Linux: apt install texlive-xetex

============================================================
```

---

## `/pandoc help <topic>` - Detailed Help

### Topics

**`/pandoc help formats`** - Show all formats:

```
============================================================
                  PANDOC SUPPORTED FORMATS
============================================================

INPUT FORMATS (52):
  Markdown:    markdown, gfm, commonmark, commonmark_x
  Documents:   docx, odt, rtf, epub
  Web:         html, html5
  Technical:   latex, rst, asciidoc, docbook, jats
  Wiki:        mediawiki, dokuwiki, tikiwiki, twiki, jira
  Data:        csv, tsv, json
  Other:       org, textile, haddock, creole, vimwiki,
               ipynb (Jupyter), fb2, man, muse, typst

OUTPUT FORMATS (65):
  Documents:   docx, odt, rtf, pdf (via LaTeX)
  Web:         html, html5, epub, epub3
  Technical:   latex, context, rst, asciidoc, docbook, jats
  Slides:      beamer, revealjs, pptx, slidy, s5, dzslides
  Wiki:        mediawiki, dokuwiki, jira, xwiki
  Other:       plain, markdown, gfm, org, texinfo, man,
               ms, icml, tei, typst, opml

============================================================
```

**`/pandoc help pdf`** - PDF-specific help
**`/pandoc help templates`** - Template customization
**`/pandoc help citations`** - Bibliography handling
**`/pandoc help slides`** - Presentation creation

---

## `/pandoc formats` - Quick Format List

```bash
# List input formats
pandoc --list-input-formats

# List output formats
pandoc --list-output-formats
```

Display organized by category (see above).

---

## `/pandoc quick <file>` - Smart Quick Conversion

Automatically detect input format and suggest appropriate output.

### Implementation

**Step 1: Detect Input Format**

```python
import os

file = "${ARGS}"  # User provided file
ext = os.path.splitext(file)[1].lower()

format_map = {
    '.md': 'markdown',
    '.markdown': 'markdown',
    '.txt': 'plain',
    '.html': 'html',
    '.htm': 'html',
    '.docx': 'docx',
    '.doc': 'docx',
    '.tex': 'latex',
    '.rst': 'rst',
    '.org': 'org',
    '.adoc': 'asciidoc',
    '.epub': 'epub',
    '.json': 'json',
    '.csv': 'csv',
}

input_format = format_map.get(ext, 'markdown')
```

**Step 2: Suggest Output Options**

```
============================================================
               QUICK CONVERSION: input.md
============================================================

Detected Format: Markdown

RECOMMENDED CONVERSIONS:

  [1] PDF Document
      pandoc input.md -o input.pdf

  [2] Word Document
      pandoc input.md -o input.docx

  [3] HTML Page
      pandoc -s input.md -o input.html

  [4] EPUB eBook
      pandoc input.md -o input.epub

Select an option or specify custom output format:
============================================================
```

**Step 3: Execute User Choice**

---

## Natural Language Support

The `/pandoc` command understands natural language requests:

| User Says | Action |
|-----------|--------|
| "Convert report.md to PDF" | Run `/pandoc-pdf report.md` |
| "Turn this Word doc into Markdown" | Run `/pandoc-convert input.docx output.md` |
| "Make slides from presentation.md" | Run `/pandoc-slides presentation.md` |
| "Create an eBook from chapters" | Run `/pandoc-epub` with multiple files |
| "Is Pandoc installed?" | Run `/pandoc status` |
| "Help me with citations" | Run `/pandoc help citations` |

---

## Error Handling

### Pandoc Not Installed

```
[ERROR] Pandoc is not installed on this system.

To install, run: /pandoc setup

Or manually install from:
https://github.com/jgm/pandoc/releases
```

### File Not Found

```
[ERROR] File not found: document.md

Please check:
1. The file path is correct
2. The file exists in the current directory
3. You have read permissions

Current directory: C:\Users\ahmed\Documents
```

### LaTeX Not Installed (for PDF)

```
[ERROR] PDF generation requires LaTeX.

LaTeX is not installed. To generate PDFs, install:

  Windows:  choco install miktex
  macOS:    brew install --cask basictex
  Linux:    apt install texlive-xetex

Alternative: Use HTML output instead:
  pandoc input.md -o output.html
```

---

## Examples

### Basic Usage

**User**: `/pandoc`
**Claude**: Shows capabilities overview

**User**: `/pandoc status`
**Claude**: Checks and reports installation status

**User**: `/pandoc setup`
**Claude**: Guides through installation process

**User**: `/pandoc quick report.md`
**Claude**: Suggests conversion options for the file

**User**: "Convert my document to PDF"
**Claude**: Identifies file and runs appropriate conversion

---

## Related Commands

| Command | Description |
|---------|-------------|
| `/pandoc-pdf` | Specialized PDF conversion |
| `/pandoc-docx` | Word document conversion |
| `/pandoc-html` | HTML generation |
| `/pandoc-epub` | eBook creation |
| `/pandoc-slides` | Presentation creation |
| `/pandoc-convert` | General format conversion |
| `/pandoc-batch` | Batch file conversion |

---

*Pandoc Plugin v1.0*
*Universal Document Conversion for Claude Code*
