# Pandoc Plugin for Claude Code

A document conversion plugin powered by [Pandoc](https://pandoc.org/). Convert between 50+ input formats and 60+ output formats with intelligent automation.

> **Migration note**: Previously, this plugin had 8 separate commands. In v2.0, all functionality is unified into `/pandoc` and the enhanced skill.

---

## Quick Start

```
1. /pandoc setup          (one-time installation)
2. /pandoc status         (verify everything works)
3. Just describe what you need:
   - "Convert report.md to PDF with TOC"
   - "Make reveal.js slides from outline.md"
   - "Create an EPUB from these chapters"
```

---

## Commands

All functionality lives under a single command:

| Command | Description |
|---------|-------------|
| `/pandoc setup` | Install and configure Pandoc + LaTeX |
| `/pandoc status` | Check installation and available engines |
| `/pandoc convert` | Convert files between any supported formats |
| `/pandoc formats` | List all supported input/output formats |
| `/pandoc help` | Show usage guide and examples |

## Natural Language

You don't need to memorize commands. Just describe what you want and the skill handles it:

- "Convert my thesis to PDF with a table of contents and bibliography"
- "Turn these markdown files into a Word document"
- "Make a reveal.js presentation from slides.md with the moon theme"
- "Create an EPUB from ch1.md, ch2.md, and ch3.md with a cover image"
- "Convert this HTML page to clean Markdown"

The skill detects the input format, chooses the right output engine, and applies best-practice options automatically.

## Features

- **Universal Conversion** -- Markdown, Word, HTML, PDF, LaTeX, EPUB, and many more
- **Professional PDFs** -- Academic, report, and book presets with LaTeX
- **Presentations** -- reveal.js (HTML), Beamer (PDF), or PowerPoint
- **eBook Publishing** -- EPUB with covers, metadata, and custom styling
- **Smart Defaults** -- Automatic format detection and best-practice options
- **Batch Processing** -- Convert multiple files in one go

## Supported Formats

### Input (50+)

| Category | Formats |
|----------|---------|
| **Markdown** | markdown, gfm, commonmark, markdown_strict, markdown_mmd |
| **Documents** | docx, odt, rtf, epub |
| **Web** | html, html5 |
| **Technical** | latex, rst, asciidoc, org, docbook |
| **Wiki** | mediawiki, dokuwiki, tikiwiki, jira |
| **Data** | csv, tsv, json |
| **Other** | ipynb (Jupyter), fb2, man, typst |

### Output (60+)

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
├── commands/
│   └── pandoc.md              # Unified command entry point
├── pandoc/
│   ├── SKILL.md               # Skill definition
│   └── scripts/
│       └── pandoc_utils.py    # Helper utilities
├── templates/                 # Custom templates
├── memories/
│   └── format_best_practices.md
└── README.md
```

## Troubleshooting

**Pandoc not found** -- Run `/pandoc setup` or install manually from https://pandoc.org/installing.html. Restart your terminal afterward.

**PDF generation fails** -- LaTeX is required for PDF output. Run `/pandoc setup` to install MiKTeX (Windows), MacTeX (macOS), or TeX Live (Linux).

**Images missing in output** -- Use relative paths in source documents. When converting from Word, the skill automatically extracts media.

**Encoding issues** -- Save source files as UTF-8. The skill handles smart quotes and Unicode automatically.

## License

MIT License

## Credits

- **Pandoc**: John MacFarlane -- https://pandoc.org/
- **Plugin**: TAQAT Techno -- https://www.taqatechno.com/

---

*Pandoc Plugin v2.0.0 -- Universal Document Conversion for Claude Code*
