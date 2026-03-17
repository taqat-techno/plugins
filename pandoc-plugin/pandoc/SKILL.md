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
  Context: User wants to create an eBook
  user: "Turn my chapters into an EPUB with a cover image"
  assistant: "I will use the pandoc skill to combine the chapter files into an EPUB eBook, attaching the cover image, generating a table of contents, and embedding metadata."
  <commentary>eBook trigger - Markdown to EPUB conversion.</commentary>
  </example>

  <example>
  Context: User wants to convert between arbitrary formats
  user: "Convert this Word document to LaTeX"
  assistant: "I will use the pandoc skill to convert the .docx file to LaTeX, extracting images and preserving table structures."
  <commentary>General conversion trigger - docx to LaTeX.</commentary>
  </example>

  <example>
  Context: User wants a styled HTML page
  user: "Generate a documentation website from my Markdown files with syntax highlighting"
  assistant: "I will use the pandoc skill to produce standalone HTML5 with a table of contents, syntax highlighting, and MathJax support."
  <commentary>HTML generation trigger - Markdown to styled HTML.</commentary>
  </example>

  <example>
  Context: User needs to install Pandoc or fix PDF generation
  user: "I keep getting pdflatex not found when converting to PDF"
  assistant: "I will use the pandoc skill's setup workflow to install MiKTeX, enable auto-install for LaTeX packages, and pre-install all required packages so PDF generation works without popups."
  <commentary>Setup trigger - installation and configuration.</commentary>
  </example>

  <example>
  Context: User wants academic PDF output
  user: "Generate a PDF of my thesis with citations, numbered sections, and double spacing"
  assistant: "I will use the pandoc skill with the academic preset to produce a PDF via XeLaTeX with citeproc, TOC, numbered sections, and 1.5 line spacing."
  <commentary>Academic PDF trigger - citations and formatting.</commentary>
  </example>

  <example>
  Context: User wants batch conversion
  user: "Convert all the .docx files in this folder to Markdown"
  assistant: "I will use the pandoc skill to batch-convert every .docx file in the directory to Markdown, extracting images into a media folder."
  <commentary>Batch processing trigger - multiple file conversion.</commentary>
  </example>

  <example>
  Context: User wants Beamer slides
  user: "Create PDF slides for my conference talk using the Warsaw theme"
  assistant: "I will use the pandoc skill to produce Beamer PDF slides with the Warsaw theme, dolphin color theme, and 16:9 aspect ratio."
  <commentary>Beamer slides trigger - academic presentations.</commentary>
  </example>

  <example>
  Context: User wants a PowerPoint
  user: "Make a PowerPoint presentation from my outline"
  assistant: "I will use the pandoc skill to convert the Markdown outline to a .pptx file, optionally using a reference template for corporate branding."
  <commentary>PowerPoint trigger - PPTX generation.</commentary>
  </example>
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

### PDF Page Layout Options

| Option | Description | Example |
|--------|-------------|---------|
| `-V geometry:top=X` | Top margin | `-V geometry:top=2cm` |
| `-V geometry:bottom=X` | Bottom margin | `-V geometry:bottom=2cm` |
| `-V geometry:left=X` | Left margin | `-V geometry:left=2.5cm` |
| `-V geometry:right=X` | Right margin | `-V geometry:right=2.5cm` |

### PDF Typography Options

| Option | Description | Example |
|--------|-------------|---------|
| `-V mainfont=FONT` | Main font (requires XeLaTeX) | `-V mainfont="Times New Roman"` |
| `-V sansfont=FONT` | Sans-serif font | `-V sansfont="Arial"` |
| `-V monofont=FONT` | Monospace font | `-V monofont="Consolas"` |
| `-V linestretch=N` | Line spacing | `-V linestretch=1.5` |

### PDF Document Classes

| Class | Use Case |
|-------|----------|
| `article` | Short documents (default) |
| `report` | Longer documents with chapters |
| `book` | Books with front/back matter |
| `memoir` | Flexible document class |
| `scrartcl` | KOMA-Script article |

### PDF Engine Options

| Engine | Use Case |
|--------|----------|
| `--pdf-engine=pdflatex` | Standard LaTeX (default, fast) |
| `--pdf-engine=xelatex` | Unicode support, custom fonts |
| `--pdf-engine=lualatex` | Advanced features |
| `--pdf-engine=tectonic` | Minimal setup |
| `--pdf-engine=wkhtmltopdf` | Via HTML, no LaTeX needed |

### PDF Presets

#### Academic Preset

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

#### Report Preset

```bash
pandoc document.md \
  -V documentclass=report \
  --toc \
  -N \
  -V geometry:margin=1in \
  -V fontsize=11pt \
  -o document.pdf
```

#### Article Preset

```bash
pandoc document.md \
  -V documentclass=article \
  -V fontsize=11pt \
  -V geometry:margin=1in \
  -o document.pdf
```

#### Book Preset

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

#### Minimal Preset

```bash
pandoc document.md -o document.pdf
```

### YAML Front Matter for PDF

Include in your Markdown file for full control:

```yaml
---
title: "Document Title"
author: "Author Name"
date: "January 15, 2025"
abstract: |
  This is the abstract of the document.

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

### DOCX Style Mapping

| Markdown Element | Word Style |
|------------------|------------|
| `# Heading` | Heading 1 |
| `## Heading` | Heading 2 |
| `### Heading` | Heading 3 |
| Normal text | Normal |
| `> Quote` | Block Text |
| `` `code` `` | Verbatim Char |
| Code block | Source Code |
| `**bold**` | Strong |
| `*italic*` | Emphasis |

### Converting FROM Word

```bash
# Word to Markdown (extract images)
pandoc input.docx --extract-media=./images -o output.md

# Word to HTML
pandoc input.docx -o output.html

# Word to LaTeX
pandoc input.docx -o output.tex

# Extract text only
pandoc input.docx -t plain -o output.txt

# Handle track changes
pandoc input.docx --track-changes=accept -o output.md   # Accept all
pandoc input.docx --track-changes=reject -o output.md   # Reject all
pandoc input.docx --track-changes=all -o output.md      # Show all
```

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

### HTML Math Rendering Options

| Option | Description |
|--------|-------------|
| `--mathjax` | Use MathJax (CDN) |
| `--katex` | Use KaTeX (faster) |
| `--mathml` | Native MathML |
| `--webtex` | Convert to images |

### HTML Resource Options

| Option | Description |
|--------|-------------|
| `--embed-resources` | Embed all resources into single file |
| `--self-contained` | Alias for embed-resources |
| `--resource-path=DIR` | Resource search path |
| `-H, --include-in-header=FILE` | Include in `<head>` |
| `-B, --include-before-body=FILE` | Include at start of body |
| `-A, --include-after-body=FILE` | Include at end of body |

### HTML Presets

#### Blog Preset

```bash
pandoc -s \
  -t html5 \
  --toc \
  -c style.css \
  --highlight-style=tango \
  --metadata title="Blog Post" \
  document.md -o document.html
```

#### Documentation Preset

```bash
pandoc -s \
  -t html5 \
  --toc \
  --toc-depth=3 \
  -N \
  --highlight-style=kate \
  --template=docs-template.html \
  document.md -o document.html
```

#### Email Preset (self-contained)

```bash
pandoc -s \
  --embed-resources \
  document.md -o document.html
```

#### Minimal Preset

```bash
pandoc document.md -o document.html
```

### Custom HTML Template

Save as `template.html` and use with `--template=template.html`:

```html
<!DOCTYPE html>
<html lang="$lang$">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>$title$</title>
    $for(css)$
    <link rel="stylesheet" href="$css$">
    $endfor$
    $if(math)$
    <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    $endif$
    $for(header-includes)$
    $header-includes$
    $endfor$
</head>
<body>
    <header>
        <h1>$title$</h1>
        $if(subtitle)$<p class="subtitle">$subtitle$</p>$endif$
        $if(author)$<p class="author">$author$</p>$endif$
        $if(date)$<p class="date">$date$</p>$endif$
    </header>
    <nav id="toc">
        $if(toc)$
        <h2>Contents</h2>
        $toc$
        $endif$
    </nav>
    <main>
        $body$
    </main>
    <footer>
        <p>Generated with Pandoc</p>
    </footer>
</body>
</html>
```

### CSS Styling Tips

A basic stylesheet for Pandoc HTML output:

```css
body {
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    line-height: 1.6;
    color: #333;
}
h1, h2, h3 { color: #2c3e50; margin-top: 1.5em; }
code { background: #f4f4f4; padding: 0.2em 0.4em; border-radius: 3px; font-size: 0.9em; }
pre { background: #f4f4f4; padding: 1rem; border-radius: 5px; overflow-x: auto; }
blockquote { border-left: 4px solid #3498db; margin: 1em 0; padding-left: 1em; color: #666; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
th, td { border: 1px solid #ddd; padding: 0.5em; text-align: left; }
th { background: #f4f4f4; }
#toc { background: #f9f9f9; padding: 1rem; border-radius: 5px; margin-bottom: 2rem; }
```

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
<dc:creator opf:role="aut">Author Name</dc:creator>
<dc:language>en-US</dc:language>
<dc:date>2025-01-15</dc:date>
<dc:publisher>Publisher Name</dc:publisher>
<dc:rights>Copyright 2025 Author Name</dc:rights>
<dc:description>
A compelling description of the book that will
appear in e-reader libraries and stores.
</dc:description>
<dc:subject>Fiction</dc:subject>
<dc:subject>Adventure</dc:subject>
```

### EPUB Cover Image Specifications

**Recommended**:

| Property | Recommendation |
|----------|----------------|
| **Dimensions** | 1600 x 2400 pixels (2:3 ratio) |
| **Format** | JPEG or PNG |
| **File Size** | Under 5 MB |
| **Color Mode** | RGB |
| **DPI** | 72-300 |

**Minimum by Platform**:

| Platform | Minimum Size |
|----------|--------------|
| Kindle | 625 x 1000 pixels |
| Apple Books | 1400 x 2100 pixels |
| Kobo | 1072 x 1448 pixels |
| General | 800 x 1200 pixels |

### EPUB Chapter and Styling Options

| Option | Description | Example |
|--------|-------------|---------|
| `--epub-chapter-level=N` | Chapter heading level | `--epub-chapter-level=1` |
| `--split-level=N` | Split at heading level | `--split-level=1` |
| `--epub-embed-font=FILE` | Embed custom font | `--epub-embed-font=font.ttf` |

### eBook Stylesheet

Save as `ebook.css` and use with `--epub-stylesheet=ebook.css`:

```css
body { font-family: Georgia, serif; font-size: 1em; line-height: 1.6; margin: 0; padding: 0; }
h1 { font-size: 2em; margin-top: 2em; text-align: center; page-break-before: always; }
h2 { font-size: 1.5em; margin-top: 1.5em; }
p { text-indent: 1.5em; margin: 0; text-align: justify; }
p.first, h1 + p, h2 + p, h3 + p { text-indent: 0; }
blockquote { margin: 1em 2em; font-style: italic; }
.scene-break { text-align: center; margin: 2em 0; }
.scene-break::before { content: "* * *"; }
img { max-width: 100%; height: auto; }
code { font-family: monospace; font-size: 0.9em; background: #f4f4f4; }
pre { white-space: pre-wrap; background: #f4f4f4; padding: 0.5em; font-size: 0.85em; }
```

### eBook Project Structure and Build Script

Recommended file organization:

```
book-project/
├── manuscript/
│   ├── 00-frontmatter.md
│   ├── 01-chapter-one.md
│   ├── 02-chapter-two.md
│   └── 99-backmatter.md
├── images/
│   ├── cover.jpg
│   └── illustrations/
├── styles/
│   └── ebook.css
├── metadata.xml
└── build.sh
```

Build script (`build.sh`):

```bash
#!/bin/bash
pandoc \
  manuscript/*.md \
  --epub-cover-image=images/cover.jpg \
  --epub-stylesheet=styles/ebook.css \
  --epub-metadata=metadata.xml \
  --toc \
  --toc-depth=1 \
  -t epub3 \
  -o output/my-book.epub
echo "eBook created: output/my-book.epub"
```

### Converting to Kindle (MOBI/AZW3)

Use Calibre (free software):

```bash
ebook-convert book.epub book.mobi
ebook-convert book.epub book.azw3
```

### EPUB Validation

Use [EPUBCheck](https://www.w3.org/publishing/epubcheck/):

```bash
java -jar epubcheck.jar book.epub
```

Or online validator: https://validator.idpf.org/

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

**reveal.js Themes**:

| Theme | Style |
|-------|-------|
| `black` | Black background, white text |
| `white` | White background, black text |
| `league` | Gray background, subtle |
| `beige` | Cream background, warm |
| `sky` | Blue gradient |
| `night` | Dark blue |
| `serif` | Classic serif fonts |
| `simple` | Minimal, clean |
| `solarized` | Solarized colors |
| `moon` | Dark, purple accents |
| `dracula` | Dracula color scheme |

**reveal.js Options**:

| Option | Values | Description |
|--------|--------|-------------|
| `controls` | true/false | Navigation controls |
| `progress` | true/false | Progress bar |
| `slideNumber` | true/false | Slide numbers |
| `hash` | true/false | URL hashes |
| `center` | true/false | Center content |
| `width` | pixels | Slide width |
| `height` | pixels | Slide height |

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

**Beamer Themes**:

| Theme | Style |
|-------|-------|
| `AnnArbor` | Yellow/blue corporate |
| `Antibes` | Tree navigation |
| `Berlin` | Structured sections |
| `Boadilla` | Clean, minimal |
| `Copenhagen` | Blue header |
| `Darmstadt` | Navigation dots |
| `Dresden` | Compact navigation |
| `Frankfurt` | Dot navigation |
| `Goettingen` | Sidebar TOC |
| `Hannover` | Sidebar navigation |
| `Ilmenau` | Three-line header |
| `JuanLesPins` | Tree-like |
| `Luebeck` | Corporate style |
| `Madrid` | Clean, modern |
| `Malmoe` | Simple structure |
| `Marburg` | Sidebar |
| `Montpellier` | Tree navigation |
| `PaloAlto` | Stanford style |
| `Pittsburgh` | Simple headers |
| `Rochester` | Cornell style |
| `Singapore` | Compact |
| `Szeged` | Simple sections |
| `Warsaw` | Blue blocks |

**Beamer Color Themes**: `albatross`, `beaver`, `beetle`, `crane`, `default`, `dolphin`, `dove`, `fly`, `lily`, `monarca`, `orchid`, `rose`, `seagull`, `seahorse`, `sidebartab`, `spruce`, `structure`, `whale`, `wolverine`

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

#### Incremental Lists

```markdown
## Incremental Bullets

::: incremental

- First item (appears first)
- Second item (appears second)
- Third item (appears third)

:::
```

#### Two-Column Layout

```markdown
## Two Columns

:::::::::::::: {.columns}
::: {.column width="50%"}

Left column content

:::
::: {.column width="50%"}

Right column content

:::
::::::::::::::
```

#### Speaker Notes

```markdown
## Slide with Notes

Content visible to audience.

::: notes

These are speaker notes.
Only visible in presenter view.

:::
```

#### Background Images (reveal.js)

```markdown
## {data-background-image="background.jpg"}

Content on custom background
```

#### YAML Front Matter for reveal.js

```yaml
---
title: "My Presentation"
author: "Author Name"
date: "January 2025"
theme: moon
transition: slide
controls: true
progress: true
slideNumber: true
hash: true
center: true
---
```

#### YAML Front Matter for Beamer

```yaml
---
title: "My Presentation"
author: "Author Name"
date: "January 2025"
theme: Warsaw
colortheme: dolphin
fonttheme: structurebold
aspectratio: 169
toc: true
---
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

### Quick Conversion Matrix

| From | To | Command |
|------|-----|---------|
| Word to Markdown | `pandoc input.docx -o output.md` |
| Markdown to Word | `pandoc input.md -o output.docx` |
| HTML to Markdown | `pandoc input.html -o output.md` |
| Markdown to HTML | `pandoc -s input.md -o output.html` |
| Word to HTML | `pandoc input.docx -o output.html` |
| HTML to Word | `pandoc input.html -o output.docx` |
| LaTeX to Word | `pandoc input.tex -o output.docx` |
| Word to LaTeX | `pandoc input.docx -o output.tex` |
| RST to Markdown | `pandoc input.rst -o output.md` |
| Org to Markdown | `pandoc input.org -o output.md` |
| AsciiDoc to HTML | `pandoc input.adoc -o output.html` |
| Jupyter to Markdown | `pandoc notebook.ipynb --extract-media=./media -o output.md` |
| MediaWiki to Markdown | `pandoc -f mediawiki wiki.txt -o output.md` |

### Conversion Quality Matrix

| From to To | Quality | Notes |
|-----------|---------|-------|
| Word to Markdown | Good | Tables and basic formatting preserved |
| Markdown to Word | Excellent | Full fidelity |
| HTML to Markdown | Good | Complex layouts may simplify |
| LaTeX to Word | Good | Math may need adjustment |
| Word to LaTeX | Good | May need manual cleanup |
| PDF to Markdown | N/A | PDF is not a supported input |

**Format Codes**:

| Code | Format |
|------|--------|
| `markdown` | Pandoc Markdown |
| `gfm` | GitHub Flavored Markdown |
| `commonmark` | CommonMark |
| `commonmark_x` | CommonMark with extensions |
| `markdown_strict` | Original Markdown |
| `markdown_phpextra` | PHP Markdown Extra |
| `markdown_mmd` | MultiMarkdown |
| `docx` | Microsoft Word |
| `odt` | OpenDocument Text |
| `rtf` | Rich Text Format |
| `html` / `html5` | HTML |
| `latex` | LaTeX |
| `pdf` | PDF |
| `epub` / `epub3` | EPUB |
| `rst` | reStructuredText |
| `org` | Org Mode |
| `asciidoc` | AsciiDoc |
| `mediawiki` | MediaWiki |
| `dokuwiki` | DokuWiki |
| `jira` | Jira markup |
| `docbook` | DocBook XML |
| `jats` | JATS XML |
| `ipynb` | Jupyter Notebook |
| `csv` / `tsv` | Tabular data |
| `typst` | Typst |
| `fb2` | FictionBook 2 |
| `man` | Man page |

### Conversion-Specific Options

```bash
# Extract images when converting from Word
pandoc --extract-media=./images input.docx -o output.md

# Control text wrapping
pandoc --wrap=none input.docx -o output.md      # No wrapping
pandoc --wrap=auto input.html -o output.md       # Auto wrap
pandoc --wrap=preserve input.md -o output.html   # Preserve original

# Set line width for wrapping
pandoc --columns=80 input.md -o output.txt
```

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

**Bash Scripts**:

```bash
# Convert all .md files to .pdf
for f in *.md; do
    pandoc "$f" -o "${f%.md}.pdf"
done

# Convert all .docx to .md (with image extraction)
for f in *.docx; do
    echo "Converting: $f"
    pandoc "$f" --extract-media="./media" -o "${f%.docx}.md"
done

# Convert all .md to .html
for f in *.md; do
    pandoc -s "$f" -o "${f%.md}.html"
done
```

**PowerShell Scripts**:

```powershell
# Convert all .md to .pdf
Get-ChildItem *.md | ForEach-Object {
    pandoc $_.Name -o ($_.BaseName + ".pdf")
}

# Convert all .docx to .md
Get-ChildItem *.docx | ForEach-Object {
    pandoc $_.Name -o ($_.BaseName + ".md")
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

## Setup & Installation

### Automated Setup

Run the setup script for one-click installation:

**Windows (PowerShell)**:
```powershell
# Full setup (Pandoc + LaTeX)
powershell -ExecutionPolicy Bypass -File "pandoc-plugin/pandoc/scripts/setup.ps1"

# Skip LaTeX (Pandoc only)
powershell -ExecutionPolicy Bypass -File "pandoc-plugin/pandoc/scripts/setup.ps1" -SkipLatex

# Quiet mode
powershell -ExecutionPolicy Bypass -File "pandoc-plugin/pandoc/scripts/setup.ps1" -Quiet
```

**Linux/macOS (Bash)**:
```bash
# Full setup
bash pandoc-plugin/pandoc/scripts/setup.sh

# Skip LaTeX
bash pandoc-plugin/pandoc/scripts/setup.sh --skip-latex
```

### What the Setup Script Does

1. Installs Pandoc (if not installed)
2. Installs MiKTeX/LaTeX (for PDF generation)
3. Enables auto-install for LaTeX packages (no more popups)
4. Pre-installs all required LaTeX packages
5. Configures PATH automatically

### Manual Quick Setup

#### Windows

```powershell
# 1. Install Pandoc
winget install JohnMacFarlane.Pandoc --accept-package-agreements --accept-source-agreements

# 2. Install MiKTeX (for PDF)
winget install MiKTeX.MiKTeX --accept-package-agreements --accept-source-agreements

# 3. Enable auto-install (prevents popup dialogs!)
& "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64\initexmf.exe" --set-config-value="[MPM]AutoInstall=1"

# 4. Install required packages
$packages = @('parskip','geometry','fancyvrb','framed','booktabs','longtable','upquote','microtype','bookmark','etoolbox','hyperref','ulem','listings','caption','float','setspace','amsmath','lm','xcolor')
foreach ($p in $packages) { & "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64\miktex.exe" packages install $p }
```

#### Linux (Ubuntu/Debian)

```bash
sudo apt install pandoc
sudo apt install texlive texlive-latex-extra texlive-fonts-recommended
```

#### macOS

```bash
brew install pandoc
brew install --cask mactex
# Or smaller: brew install basictex
```

### Pre-installed LaTeX Packages

The setup pre-installs these packages to prevent MiKTeX popup dialogs:

| Package | Purpose |
|---------|---------|
| `parskip` | Paragraph spacing |
| `geometry` | Page margins |
| `fancyvrb` | Verbatim/code blocks |
| `framed` | Framed boxes |
| `booktabs` | Professional tables |
| `longtable` | Multi-page tables |
| `hyperref` | PDF links |
| `listings` | Code listings |
| `amsmath` | Math formulas |
| `xcolor` | Colors |
| `graphicx` | Images |
| `upquote` | Straight quotes in verbatim |
| `microtype` | Microtypography |
| `bookmark` | PDF bookmarks |
| `etoolbox` | Programming tools |
| `ulem` | Underline/strikeout |
| `caption` | Figure/table captions |
| `float` | Float placement |
| `setspace` | Line spacing |
| `lm` | Latin Modern fonts |

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
