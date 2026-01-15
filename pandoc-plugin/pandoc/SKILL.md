---
name: pandoc
description: "Universal document conversion skill powered by Pandoc - Convert between 50+ input formats and 60+ output formats. Professional document transformation with templates, citations, math rendering, and batch processing for PDF, Word, HTML, EPUB, LaTeX, and presentations."
version: "1.0.0"
author: "TaqaTechno"
license: "MIT"
category: "document-conversion"
tags:
  - pandoc
  - document-conversion
  - pdf
  - docx
  - html
  - epub
  - latex
  - markdown
  - presentations
  - academic-writing
  - technical-documentation
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
metadata:
  mode: "cli-tool"
  pandoc-min-version: "3.0.0"
  input-formats: "50+"
  output-formats: "60+"
  primary-use-cases:
    - document-conversion
    - pdf-generation
    - ebook-creation
    - slide-presentations
    - academic-papers
    - technical-documentation
---

# Pandoc - Universal Document Converter Skill

A comprehensive skill for document conversion using Pandoc, the universal document converter. This skill enables Claude to convert documents between virtually any format with professional-grade output.

## When to Use This Skill

Activate the Pandoc skill when you need to:

- **Convert Documents**: Transform files between formats (Markdown to PDF, Word to HTML, etc.)
- **Generate PDFs**: Create professional PDF documents from Markdown, HTML, or other sources
- **Create eBooks**: Generate EPUB files for e-readers
- **Build Presentations**: Create reveal.js or Beamer slides from Markdown
- **Academic Writing**: Process papers with citations and bibliography
- **Technical Documentation**: Generate docs in multiple formats from a single source
- **Batch Processing**: Convert multiple files at once

---

## Quick Reference

### Installation Check

```bash
# Check if Pandoc is installed
pandoc --version

# Install on Windows
choco install pandoc
# or
winget install JohnMacFarlane.Pandoc

# Install on macOS
brew install pandoc

# Install on Linux
sudo apt install pandoc  # Debian/Ubuntu
sudo dnf install pandoc  # Fedora
```

### Basic Conversion Syntax

```bash
pandoc [OPTIONS] [INPUT_FILES] -o OUTPUT_FILE
```

### Most Common Conversions

```bash
# Markdown to PDF
pandoc input.md -o output.pdf

# Markdown to Word
pandoc input.md -o output.docx

# Markdown to HTML
pandoc -s input.md -o output.html

# Word to Markdown
pandoc input.docx -o output.md

# HTML to Markdown
pandoc input.html -o output.md

# Markdown to EPUB
pandoc input.md -o output.epub

# Markdown to Slides (reveal.js)
pandoc -t revealjs -s slides.md -o slides.html
```

---

## Supported Formats

### Primary Input Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| **Markdown** | `.md` | CommonMark, GFM, Pandoc Markdown |
| **Word** | `.docx` | Microsoft Word documents |
| **HTML** | `.html` | Web pages |
| **LaTeX** | `.tex` | Academic/scientific documents |
| **reStructuredText** | `.rst` | Python documentation format |
| **Org Mode** | `.org` | Emacs org-mode files |
| **EPUB** | `.epub` | eBook format |
| **CSV** | `.csv` | Spreadsheet data |
| **Jupyter** | `.ipynb` | Jupyter notebooks |
| **AsciiDoc** | `.adoc` | Technical documentation |

### Primary Output Formats

| Format | Extension | Use Case |
|--------|-----------|----------|
| **PDF** | `.pdf` | Print-ready documents (requires LaTeX) |
| **Word** | `.docx` | Editable documents, business reports |
| **HTML** | `.html` | Web pages, online documentation |
| **EPUB** | `.epub` | eBooks for Kindle, Apple Books |
| **LaTeX** | `.tex` | Academic papers, thesis |
| **Beamer** | `.pdf` | PDF presentations |
| **reveal.js** | `.html` | Interactive web slides |
| **PowerPoint** | `.pptx` | Microsoft PowerPoint |
| **Plain Text** | `.txt` | Simple text output |

---

## Commands Reference

### Main Commands

| Command | Description |
|---------|-------------|
| `/pandoc` | Main entry point - shows help and capabilities |
| `/pandoc-pdf` | Convert to PDF document |
| `/pandoc-docx` | Convert to Microsoft Word |
| `/pandoc-html` | Convert to HTML web page |
| `/pandoc-epub` | Convert to EPUB eBook |
| `/pandoc-slides` | Create presentation slides |
| `/pandoc-convert` | General format conversion |
| `/pandoc-setup` | Install and configure Pandoc |
| `/pandoc-batch` | Batch convert multiple files |

---

## Detailed Command Usage

### `/pandoc-pdf` - PDF Generation

Generate professional PDF documents from various sources.

**Requirements**: LaTeX distribution (MiKTeX, TeX Live, or TinyTeX)

```bash
# Basic PDF
pandoc input.md -o output.pdf

# With table of contents
pandoc --toc input.md -o output.pdf

# With numbered sections
pandoc --toc -N input.md -o output.pdf

# With custom margins
pandoc -V geometry:margin=1in input.md -o output.pdf

# Academic paper with citations
pandoc --citeproc --bibliography=refs.bib paper.md -o paper.pdf

# Custom font
pandoc --pdf-engine=xelatex -V mainfont="Times New Roman" input.md -o output.pdf

# Two-column layout
pandoc -V classoption=twocolumn input.md -o output.pdf
```

**PDF Options**:

| Option | Description |
|--------|-------------|
| `--toc` | Include table of contents |
| `-N, --number-sections` | Number section headings |
| `--toc-depth=N` | TOC depth (default: 3) |
| `-V geometry:margin=X` | Set page margins |
| `-V fontsize=12pt` | Set font size |
| `-V papersize=a4` | Set paper size |
| `--pdf-engine=ENGINE` | xelatex, lualatex, pdflatex |
| `--template=FILE` | Custom LaTeX template |

---

### `/pandoc-docx` - Word Document Generation

Create Microsoft Word documents with formatting preserved.

```bash
# Basic conversion
pandoc input.md -o output.docx

# With custom reference doc (styling)
pandoc --reference-doc=template.docx input.md -o output.docx

# With table of contents
pandoc --toc input.md -o output.docx

# From HTML
pandoc input.html -o output.docx

# Multiple inputs
pandoc chapter1.md chapter2.md chapter3.md -o book.docx
```

**Creating a Reference Template**:

1. Generate a default reference doc:
   ```bash
   pandoc -o custom-reference.docx --print-default-data-file reference.docx
   ```
2. Open in Word and modify styles (Heading 1, Normal, etc.)
3. Use as template with `--reference-doc`

---

### `/pandoc-html` - HTML Generation

Create web pages with optional styling.

```bash
# Basic standalone HTML
pandoc -s input.md -o output.html

# With custom CSS
pandoc -s -c style.css input.md -o output.html

# With syntax highlighting
pandoc -s --highlight-style=tango input.md -o output.html

# With table of contents
pandoc -s --toc input.md -o output.html

# Self-contained (embeds resources)
pandoc -s --embed-resources input.md -o output.html

# With MathJax for equations
pandoc -s --mathjax input.md -o output.html

# HTML5 output
pandoc -s -t html5 input.md -o output.html
```

**Highlight Styles**: `pygments`, `tango`, `espresso`, `zenburn`, `kate`, `monochrome`, `breezeDark`, `haddock`

---

### `/pandoc-epub` - eBook Creation

Generate EPUB files for e-readers.

```bash
# Basic EPUB
pandoc input.md -o output.epub

# With cover image
pandoc --epub-cover-image=cover.jpg input.md -o output.epub

# With metadata
pandoc --epub-metadata=metadata.xml input.md -o output.epub

# With custom CSS
pandoc --epub-stylesheet=style.css input.md -o output.epub

# With table of contents
pandoc --toc --toc-depth=2 input.md -o output.epub

# Multiple chapters
pandoc title.md ch1.md ch2.md ch3.md -o book.epub

# EPUB version 3
pandoc -t epub3 input.md -o output.epub
```

**EPUB Metadata File** (`metadata.xml`):

```xml
<dc:title>Book Title</dc:title>
<dc:creator>Author Name</dc:creator>
<dc:language>en-US</dc:language>
<dc:date>2025-01-15</dc:date>
<dc:publisher>Publisher Name</dc:publisher>
<dc:rights>Copyright 2025</dc:rights>
```

---

### `/pandoc-slides` - Presentation Creation

Create slide presentations in multiple formats.

#### reveal.js (HTML Slides)

```bash
# Basic reveal.js
pandoc -t revealjs -s slides.md -o presentation.html

# With theme
pandoc -t revealjs -s -V theme=moon slides.md -o presentation.html

# With transition
pandoc -t revealjs -s -V transition=slide slides.md -o presentation.html

# Using CDN
pandoc -t revealjs -s \
  -V revealjs-url=https://unpkg.com/reveal.js@4/ \
  slides.md -o presentation.html
```

**reveal.js Themes**: `black`, `white`, `league`, `beige`, `sky`, `night`, `serif`, `simple`, `solarized`, `moon`, `dracula`

**Transitions**: `none`, `fade`, `slide`, `convex`, `concave`, `zoom`

#### Beamer (PDF Slides)

```bash
# Basic Beamer
pandoc -t beamer slides.md -o presentation.pdf

# With theme
pandoc -t beamer -V theme:Warsaw slides.md -o presentation.pdf

# With color theme
pandoc -t beamer -V theme:Madrid -V colortheme:dolphin slides.md -o presentation.pdf

# With aspect ratio
pandoc -t beamer -V aspectratio=169 slides.md -o presentation.pdf
```

**Beamer Themes**: `AnnArbor`, `Berlin`, `Copenhagen`, `Madrid`, `Warsaw`, `Singapore`, `Boadilla`, `Montpellier`

#### PowerPoint

```bash
# Basic PowerPoint
pandoc slides.md -o presentation.pptx

# With reference template
pandoc --reference-doc=template.pptx slides.md -o presentation.pptx
```

#### Slide Markdown Format

```markdown
---
title: Presentation Title
author: Author Name
date: January 2025
---

# Section 1

## Slide 1.1

- Bullet point 1
- Bullet point 2
- Bullet point 3

## Slide 1.2

Content for slide 1.2

. . .

This appears after a pause (incremental)

# Section 2

## Slide 2.1

![Image](image.png)

---

Speaker notes go here
```

---

### `/pandoc-convert` - General Conversion

Convert between any supported formats.

```bash
# Explicit format specification
pandoc -f FORMAT -t FORMAT input -o output

# Examples
pandoc -f docx -t markdown input.docx -o output.md
pandoc -f html -t latex input.html -o output.tex
pandoc -f rst -t docx input.rst -o output.docx
pandoc -f org -t html input.org -o output.html
pandoc -f csv -t html data.csv -o table.html
```

**Format Codes**:

| Code | Format |
|------|--------|
| `markdown` | Pandoc Markdown |
| `gfm` | GitHub Flavored Markdown |
| `commonmark` | CommonMark |
| `docx` | Microsoft Word |
| `html` / `html5` | HTML |
| `latex` | LaTeX |
| `pdf` | PDF |
| `epub` / `epub3` | EPUB |
| `rst` | reStructuredText |
| `org` | Org Mode |
| `asciidoc` | AsciiDoc |
| `mediawiki` | MediaWiki |
| `docbook` | DocBook XML |

---

## Advanced Features

### Citations and Bibliography

Process academic citations with `--citeproc`.

**YAML Front Matter**:

```yaml
---
title: "My Paper"
author: "Author Name"
bibliography: references.bib
csl: ieee.csl
---
```

**Citation Syntax**:

```markdown
According to Smith [@smith2020].

Multiple sources [@doe99; @smith2000, pp. 33-35].

Author in text: @johnson2015 argues that...

Suppress author: [-@wilson2018] shows...
```

**Command**:

```bash
pandoc --citeproc --bibliography=refs.bib paper.md -o paper.pdf
```

---

### Custom Templates

Use custom templates for consistent styling.

```bash
# View default template
pandoc -D latex > my-template.tex

# Use custom template
pandoc --template=my-template.tex input.md -o output.pdf

# Template with variables
pandoc --template=letter.tex \
  --variable recipient="John Doe" \
  --variable date="January 15, 2025" \
  letter.md -o letter.pdf
```

---

### Metadata and Variables

Set document metadata via command line.

```bash
# Title, author, date
pandoc --metadata title="My Document" \
       --metadata author="John Doe" \
       --metadata date="2025-01-15" \
       input.md -o output.pdf

# Template variables
pandoc -V fontsize=12pt \
       -V geometry:margin=1in \
       -V documentclass=report \
       input.md -o output.pdf

# From YAML file
pandoc --metadata-file=meta.yaml input.md -o output.pdf
```

---

### Filters and Extensions

#### Lua Filters

```bash
# Apply Lua filter
pandoc --lua-filter=filter.lua input.md -o output.pdf
```

**Example Filter** (`uppercase.lua`):

```lua
function Str(elem)
    elem.text = elem.text:upper()
    return elem
end
```

#### Markdown Extensions

```bash
# Enable extensions
pandoc -f markdown+footnotes+smart input.md -o output.pdf

# Disable extensions
pandoc -f markdown-smart-raw_html input.md -o output.pdf
```

**Useful Extensions**:

| Extension | Description |
|-----------|-------------|
| `+smart` | Smart quotes and dashes |
| `+footnotes` | Footnote support |
| `+pipe_tables` | Pipe table syntax |
| `+yaml_metadata_block` | YAML front matter |
| `+tex_math_dollars` | LaTeX math with $ |
| `+strikeout` | ~~Strikethrough~~ |
| `+task_lists` | - [x] Checkboxes |

---

### Batch Processing

Convert multiple files efficiently.

**Shell Script (Bash/PowerShell)**:

```bash
# Convert all .md files to .pdf
for f in *.md; do
    pandoc "$f" -o "${f%.md}.pdf"
done

# PowerShell
Get-ChildItem *.md | ForEach-Object {
    pandoc $_.Name -o ($_.BaseName + ".pdf")
}
```

**Makefile**:

```makefile
SOURCES = $(wildcard *.md)
PDFS = $(SOURCES:.md=.pdf)
HTMLS = $(SOURCES:.md=.html)

all: $(PDFS) $(HTMLS)

%.pdf: %.md
	pandoc -s $< -o $@

%.html: %.md
	pandoc -s $< -o $@

clean:
	rm -f $(PDFS) $(HTMLS)
```

**Defaults File** (`defaults.yaml`):

```yaml
from: markdown+smart+footnotes
to: html5
standalone: true
toc: true
toc-depth: 2
number-sections: true
highlight-style: tango
css:
  - style.css
metadata:
  author: "Default Author"
  lang: en
```

```bash
pandoc -d defaults.yaml input.md -o output.html
```

---

## Error Handling

### Common Issues and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `pandoc: command not found` | Not installed | Install Pandoc for your platform |
| `pdflatex not found` | No LaTeX for PDF | Install MiKTeX/TeX Live |
| `Unknown extension: +xxx` | Invalid extension | Check spelling, use `pandoc --list-extensions` |
| `Could not find bibliography file` | Wrong path | Use absolute path or correct relative path |
| `UTF-8 encoding error` | File encoding issue | Save file as UTF-8 |

### Checking Installation

```bash
# Full version info
pandoc --version

# List input formats
pandoc --list-input-formats

# List output formats
pandoc --list-output-formats

# List extensions for a format
pandoc --list-extensions=markdown

# List highlight styles
pandoc --list-highlight-styles
```

---

## Best Practices

### 1. Use YAML Front Matter

```yaml
---
title: "Document Title"
author: "Your Name"
date: "2025-01-15"
abstract: |
  This is the abstract.
keywords:
  - pandoc
  - documentation
lang: en
---
```

### 2. Organize Large Documents

```bash
# Combine multiple files
pandoc title.md intro.md ch1.md ch2.md conclusion.md -o book.pdf

# Use defaults file for consistency
pandoc -d project-defaults.yaml chapter*.md -o book.pdf
```

### 3. Version Control Friendly

- Keep source in Markdown
- Generate outputs on demand
- Use Makefile for builds
- Store templates separately

### 4. Citation Management

- Use Zotero with Better BibTeX export
- Keep `.bib` file in project directory
- Choose appropriate CSL style

### 5. Custom Styling

- Create reference templates for DOCX
- Develop custom LaTeX templates for PDF
- Use CSS for HTML output

---

## Integration Examples

### VS Code Integration

1. Install "vscode-pandoc" extension
2. Configure in settings.json:
   ```json
   {
     "pandoc.pdfOptString": "--toc -N",
     "pandoc.docxOptString": "--toc"
   }
   ```
3. Use command palette: "Pandoc Render"

### CI/CD Pipeline (GitHub Actions)

```yaml
name: Build Documentation
on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build PDF
        uses: docker://pandoc/latex:3.7
        with:
          args: >-
            --toc
            --number-sections
            docs/*.md
            -o documentation.pdf

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: documentation
          path: documentation.pdf
```

---

## File Output Structure

When using Pandoc commands, files are created in the current directory or specified output path:

```
project/
├── source/
│   ├── document.md        # Source file
│   ├── references.bib     # Bibliography
│   └── metadata.yaml      # Metadata file
├── output/
│   ├── document.pdf       # Generated PDF
│   ├── document.docx      # Generated Word
│   ├── document.html      # Generated HTML
│   └── document.epub      # Generated EPUB
├── templates/
│   ├── custom.tex         # LaTeX template
│   ├── reference.docx     # Word template
│   └── style.css          # HTML stylesheet
└── defaults.yaml          # Pandoc defaults
```

---

## Related Documentation

| Resource | URL |
|----------|-----|
| Pandoc Manual | https://pandoc.org/MANUAL.html |
| Pandoc GitHub | https://github.com/jgm/pandoc |
| CSL Styles | https://www.zotero.org/styles |
| Lua Filters | https://github.com/pandoc/lua-filters |

---

*Pandoc Plugin v1.0*
*TaqaTechno - Universal Document Conversion*
*Powered by Pandoc - The Universal Document Converter*
