# Pandoc Plugin for Claude Code

A professional document conversion plugin powered by [Pandoc](https://pandoc.org/), the universal document converter. Transform your documents between 50+ input formats and 60+ output formats with intelligent automation and best-practice recommendations.

---

## Quick Setup (30 seconds)

### Windows (PowerShell - Run as Admin)
```powershell
# One-liner: Install Pandoc + LaTeX + Configure everything
powershell -ExecutionPolicy Bypass -Command "& { winget install JohnMacFarlane.Pandoc --accept-package-agreements -s; winget install MiKTeX.MiKTeX --accept-package-agreements -s; Start-Sleep 5; & \"$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64\initexmf.exe\" --set-config-value='[MPM]AutoInstall=1' }"
```

### Or run the setup script:
```powershell
powershell -ExecutionPolicy Bypass -File "pandoc-plugin\pandoc\scripts\setup.ps1"
```

### Linux
```bash
sudo apt install pandoc texlive texlive-latex-extra  # Ubuntu/Debian
# or
sudo dnf install pandoc texlive                       # Fedora
```

### macOS
```bash
brew install pandoc && brew install --cask mactex
```

**After installation, restart your terminal!**

---

## Features

- **Universal Conversion**: Convert between Markdown, Word, HTML, PDF, LaTeX, EPUB, and many more
- **Professional PDF Generation**: Create publication-ready PDFs with academic, report, and book presets
- **Presentation Creation**: Generate slides in reveal.js (HTML), Beamer (PDF), or PowerPoint
- **eBook Publishing**: Create EPUB eBooks with covers, metadata, and custom styling
- **Smart Automation**: Automatic format detection, best-practice application, and error handling
- **Batch Processing**: Convert multiple files in a single command

## Installation

### Prerequisites

1. **Pandoc** (v3.0.0 or higher)
   ```bash
   # Windows (Chocolatey)
   choco install pandoc

   # macOS (Homebrew)
   brew install pandoc

   # Ubuntu/Debian
   sudo apt install pandoc

   # Or download from: https://pandoc.org/installing.html
   ```

2. **LaTeX** (for PDF generation)
   ```bash
   # Windows
   choco install miktex

   # macOS
   brew install --cask mactex

   # Ubuntu/Debian
   sudo apt install texlive-full
   ```

### Plugin Installation

1. Copy the `pandoc-plugin` folder to your Claude Code plugins directory:
   ```
   C:\odoo\tmp\plugins\pandoc-plugin\
   ```

2. The plugin will be automatically detected by Claude Code.

3. Verify installation:
   ```
   /pandoc status
   ```

## Commands

| Command | Description |
|---------|-------------|
| `/pandoc` | Main help and quick start guide |
| `/pandoc-pdf` | Convert to professional PDF documents |
| `/pandoc-docx` | Convert to Microsoft Word format |
| `/pandoc-html` | Convert to HTML web pages |
| `/pandoc-epub` | Create EPUB eBooks |
| `/pandoc-slides` | Create presentations (reveal.js, Beamer, PowerPoint) |
| `/pandoc-convert` | General format conversion |

## Quick Start

### Convert Markdown to PDF

```
/pandoc-pdf document.md
```

### Create Word Document

```
/pandoc-docx report.md
```

### Generate HTML

```
/pandoc-html article.md
```

### Create Presentation

```
/pandoc-slides talk.md --format=revealjs --theme=moon
```

### Create eBook

```
/pandoc-epub book.md --cover=cover.jpg
```

### General Conversion

```
/pandoc-convert input.docx output.md
```

## Detailed Usage

### PDF Generation

```bash
# Basic PDF
/pandoc-pdf document.md

# Academic paper with citations
/pandoc-pdf paper.md --preset=academic --bibliography=refs.bib

# Book format
/pandoc-pdf manuscript.md --preset=book --toc

# Custom options
/pandoc-pdf report.md --engine=xelatex --template=custom.tex
```

**Presets**:
- `academic` - Double-spaced, citations, numbered sections
- `report` - Professional business format
- `article` - Clean article format
- `book` - Book layout with chapters
- `minimal` - Simple, no extra formatting

### Word Documents

```bash
# Basic conversion
/pandoc-docx document.md

# With company template
/pandoc-docx report.md --template=company.docx

# With table of contents
/pandoc-docx manual.md --toc
```

### HTML Generation

```bash
# Standalone HTML
/pandoc-html article.md

# With custom CSS
/pandoc-html document.md --css=style.css

# Self-contained (all resources embedded)
/pandoc-html page.md --embed-resources

# With syntax highlighting
/pandoc-html code-tutorial.md --highlight=tango
```

### Presentations

```bash
# reveal.js (HTML slides)
/pandoc-slides talk.md --format=revealjs --theme=moon

# Beamer (PDF slides)
/pandoc-slides lecture.md --format=beamer --theme=Warsaw

# PowerPoint
/pandoc-slides meeting.md --format=pptx
```

**reveal.js Themes**: black, white, league, beige, sky, night, serif, simple, solarized, moon, dracula

**Beamer Themes**: Warsaw, Madrid, Berlin, Copenhagen, Frankfurt, and many more

### EPUB eBooks

```bash
# Simple eBook
/pandoc-epub novel.md

# With cover and metadata
/pandoc-epub book.md --cover=cover.jpg --title="My Book" --author="Jane Doe"

# Multi-chapter book
/pandoc-epub ch1.md ch2.md ch3.md --toc
```

### General Conversion

```bash
# Word to Markdown
/pandoc-convert document.docx output.md

# HTML to Word
/pandoc-convert webpage.html document.docx

# LaTeX to Word
/pandoc-convert thesis.tex thesis.docx

# Any to any
/pandoc-convert input.rst output.html
```

## Supported Formats

### Input Formats (50+)

| Category | Formats |
|----------|---------|
| **Markdown** | markdown, gfm, commonmark, markdown_strict, markdown_mmd |
| **Documents** | docx, odt, rtf, epub |
| **Web** | html, html5 |
| **Technical** | latex, rst, asciidoc, org, docbook |
| **Wiki** | mediawiki, dokuwiki, tikiwiki, jira |
| **Data** | csv, tsv, json |
| **Other** | ipynb (Jupyter), fb2, man, typst |

### Output Formats (60+)

All input formats plus:

| Category | Formats |
|----------|---------|
| **Print** | pdf |
| **Presentations** | revealjs, beamer, pptx, slidy, dzslides |
| **Publishing** | epub, epub3, icml |
| **Technical** | context, texinfo, ms |
| **Other** | plain, ansi, chunkedhtml |

## Plugin Structure

```
pandoc-plugin/
├── .claude-plugin/
│   └── plugin.json           # Plugin manifest
├── commands/
│   ├── pandoc.md             # Main entry point
│   ├── pdf.md                # PDF generation
│   ├── docx.md               # Word conversion
│   ├── html.md               # HTML generation
│   ├── epub.md               # eBook creation
│   ├── slides.md             # Presentations
│   └── convert.md            # General conversion
├── pandoc/
│   ├── SKILL.md              # Skill definition
│   └── scripts/
│       └── pandoc_utils.py   # Helper utilities
├── templates/                # Custom templates
├── memories/
│   └── format_best_practices.md  # Best practices
└── README.md                 # This file
```

## Best Practices

The plugin automatically applies best practices:

### PDF Generation
- Checks LaTeX installation before conversion
- Recommends XeLaTeX for custom fonts or Unicode
- Adds table of contents for documents over 5 pages
- Uses appropriate presets for academic papers

### Word Documents
- Suggests reference templates for consistent styling
- Extracts media when converting from Word
- Preserves paragraph structure with `--wrap=none`

### HTML Generation
- Always uses standalone mode for complete documents
- Suggests CSS for better appearance
- Embeds resources for portable single-file HTML

### EPUB eBooks
- Recommends cover image (1600x2400 pixels)
- Includes metadata for proper eBook listings
- Uses EPUB 3 for modern readers

### Presentations
- Uses professional themes by default
- Enables navigation controls and progress bars
- Recommends 16:9 aspect ratio for Beamer

## Troubleshooting

### Pandoc Not Found

```
Error: Pandoc is not installed

Solution:
1. Install Pandoc from https://pandoc.org/installing.html
2. Verify: pandoc --version
3. Restart terminal/Claude Code
```

### PDF Generation Fails

```
Error: LaTeX not installed

Solution:
1. Install LaTeX (MiKTeX, MacTeX, or TeX Live)
2. Verify: pdflatex --version
3. For custom fonts, use XeLaTeX: --pdf-engine=xelatex
```

### Images Missing in Output

```
Warning: Images not appearing

Solution:
1. Use relative paths in source document
2. Add --extract-media=./images when converting from Word
3. Ensure images are accessible from working directory
```

### Encoding Issues

```
Error: UTF-8 encoding error

Solution:
1. Save source file as UTF-8
2. Remove special characters if problematic
3. Use --from=markdown+smart for smart quotes
```

## Examples

### Academic Paper Workflow

```bash
# 1. Write in Markdown with citations
# paper.md uses [@citation] syntax

# 2. Generate PDF with bibliography
/pandoc-pdf paper.md --preset=academic --bibliography=refs.bib --csl=ieee.csl
```

### Book Publishing Workflow

```bash
# 1. Organize chapters
# manuscript/ch01.md, ch02.md, ch03.md...

# 2. Create EPUB
/pandoc-epub manuscript/*.md --cover=cover.jpg --toc --title="My Novel"

# 3. Create print PDF
/pandoc-pdf manuscript/*.md --preset=book --toc
```

### Documentation Workflow

```bash
# 1. Write docs in Markdown
# docs/*.md

# 2. Generate HTML documentation
/pandoc-html docs/*.md --toc --toc-depth=3 -N --embed-resources

# 3. Generate Word for review
/pandoc-docx docs/*.md --toc
```

### Presentation Workflow

```bash
# 1. Write slides in Markdown
# slides.md using ## for slide breaks

# 2. Generate HTML slides for web
/pandoc-slides slides.md --format=revealjs --theme=night

# 3. Generate PDF for printing
/pandoc-slides slides.md --format=beamer --theme=Madrid
```

## Contributing

Contributions are welcome! Please submit issues and pull requests to the plugin repository.

## License

MIT License - See LICENSE file for details.

## Credits

- **Pandoc**: Created by John MacFarlane - https://pandoc.org/
- **Plugin**: Developed by TAQAT Techno - https://www.taqatechno.com/

---

*Pandoc Plugin v1.0.0*
*Universal Document Conversion for Claude Code*
