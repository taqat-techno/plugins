---
description: Convert a document between formats with Pandoc (no arguments shows usage and examples)
argument-hint: '<file> <format> [pandoc options]'
---

# /pandoc:convert

With no arguments, show a short usage guide: the syntax above, the most used
targets (pdf, docx, html, epub, revealjs, pptx, md) and the examples below, and
point to `/pandoc:formats` and `/pandoc:setup`.

Otherwise follow the `pandoc-conversion` skill's Core Workflow for `$ARGUMENTS`:
check the installation, pick the flags for the target format, **ask before
overwriting an existing output file**, add `--sandbox` when the input came from
an untrusted source, run the command, and report the output path, size and the
exact command.

```bash
pandoc input.md -o output.pdf --pdf-engine=xelatex
pandoc input.docx -o output.md --extract-media=media/
pandoc slides.md -o slides.html -t revealjs -s
pandoc chapters/*.md -o book.epub --toc --epub-cover-image=cover.jpg
```
