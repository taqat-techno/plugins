---
description: 'Universal document converter - setup, convert, status, and help for 50+ formats'
argument-hint: '[setup|status|convert|formats|help] [args...]'
---

# /pandoc - Universal Document Converter

Parse `$ARGUMENTS` and dispatch:

| Input | Action |
|-------|--------|
| *(empty)* / `help` | Show help with available formats and examples |
| `setup` | Install Pandoc + LaTeX (MiKTeX) with auto-install packages |
| `status` | Check Pandoc installation, version, available formats |
| `convert <file> <format> [opts]` | Convert document to target format |
| `formats` | List all supported input/output formats |

Use the pandoc skill for:
- Format-specific conversion patterns (PDF, DOCX, HTML, EPUB, slides)
- LaTeX template configuration and academic presets
- Citation processing with citeproc
- Batch conversion workflows
- Troubleshooting (pdflatex not found, encoding issues)
- Platform-specific setup (Windows MiKTeX, Linux texlive)

Common conversions:
```bash
# Markdown to PDF
pandoc input.md -o output.pdf --pdf-engine=xelatex

# Word to Markdown
pandoc input.docx -o output.md --extract-media=media/

# Markdown to reveal.js slides
pandoc slides.md -o slides.html -t revealjs -s

# Markdown to EPUB
pandoc chapters/*.md -o book.epub --toc --epub-cover-image=cover.jpg
```
