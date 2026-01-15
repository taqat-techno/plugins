---
title: 'Pandoc Convert'
read_only: false
type: 'command'
description: 'General-purpose document conversion between any supported formats. Convert Word to Markdown, HTML to LaTeX, and more.'
---

# /pandoc-convert - General Format Conversion

Convert documents between any of Pandoc's 50+ input and 60+ output formats.

## Usage

```
/pandoc-convert <input-file> <output-file>
/pandoc-convert <input-file> --to=FORMAT
/pandoc-convert document.docx document.md
/pandoc-convert --from=html --to=latex input.html output.tex
```

---

## Quick Conversion Matrix

### Popular Conversions

| From | To | Command |
|------|-----|---------|
| Word → Markdown | `pandoc input.docx -o output.md` |
| Markdown → Word | `pandoc input.md -o output.docx` |
| HTML → Markdown | `pandoc input.html -o output.md` |
| Markdown → HTML | `pandoc -s input.md -o output.html` |
| Word → HTML | `pandoc input.docx -o output.html` |
| HTML → Word | `pandoc input.html -o output.docx` |
| LaTeX → Word | `pandoc input.tex -o output.docx` |
| Word → LaTeX | `pandoc input.docx -o output.tex` |
| Markdown → LaTeX | `pandoc input.md -o output.tex` |
| RST → Markdown | `pandoc input.rst -o output.md` |
| Org → Markdown | `pandoc input.org -o output.md` |
| AsciiDoc → HTML | `pandoc input.adoc -o output.html` |

---

## Complete Workflow

### Step 1: Detect Input Format

```python
# Auto-detect from extension
extension_map = {
    '.md': 'markdown',
    '.markdown': 'markdown',
    '.txt': 'plain',
    '.html': 'html',
    '.htm': 'html',
    '.docx': 'docx',
    '.odt': 'odt',
    '.tex': 'latex',
    '.rst': 'rst',
    '.org': 'org',
    '.adoc': 'asciidoc',
    '.epub': 'epub',
    '.ipynb': 'ipynb',
    '.csv': 'csv',
    '.json': 'json',
    '.xml': 'docbook',
}
```

### Step 2: Determine Output Format

If not specified, detect from output extension or ask user:

```
============================================================
                    FORMAT CONVERSION
============================================================

INPUT:  document.docx (Word)

SELECT OUTPUT FORMAT:

  [1] Markdown (.md)        - Plain text markup
  [2] HTML (.html)          - Web page
  [3] PDF (.pdf)            - Print document
  [4] LaTeX (.tex)          - Academic/scientific
  [5] Plain Text (.txt)     - Simple text
  [6] RST (.rst)            - reStructuredText
  [7] Org Mode (.org)       - Emacs org-mode
  [8] EPUB (.epub)          - eBook
  [9] Custom                - Specify format

Enter choice:
============================================================
```

### Step 3: Execute Conversion

```bash
# With explicit formats
pandoc -f FORMAT -t FORMAT input -o output

# With auto-detection
pandoc input.docx -o output.md
```

### Step 4: Report Results

```
============================================================
              CONVERSION COMPLETED SUCCESSFULLY
============================================================

INPUT:      document.docx (Word)
            Size: 45 KB

OUTPUT:     document.md (Markdown)
            Size: 12 KB

CONVERSION: docx → markdown

NOTES:
  • Images extracted to: ./media/
  • Tables converted to pipe format
  • Formatting preserved where possible

OUTPUT FILE: C:\Users\ahmed\Documents\document.md

============================================================
```

---

## Format Reference

### Input Formats

```bash
# List all input formats
pandoc --list-input-formats
```

**Markdown Variants**:
- `markdown` - Pandoc Markdown (default)
- `gfm` - GitHub Flavored Markdown
- `commonmark` - CommonMark
- `commonmark_x` - CommonMark with extensions
- `markdown_strict` - Original Markdown
- `markdown_phpextra` - PHP Markdown Extra
- `markdown_mmd` - MultiMarkdown

**Document Formats**:
- `docx` - Microsoft Word
- `odt` - OpenDocument Text
- `rtf` - Rich Text Format
- `epub` - EPUB eBook

**Web Formats**:
- `html` - HTML
- `html5` - HTML5

**Technical/Academic**:
- `latex` - LaTeX
- `rst` - reStructuredText
- `asciidoc` - AsciiDoc
- `docbook` - DocBook XML
- `jats` - JATS XML
- `tei` - TEI XML

**Wiki Formats**:
- `mediawiki` - MediaWiki
- `dokuwiki` - DokuWiki
- `tikiwiki` - TikiWiki
- `twiki` - TWiki
- `vimwiki` - VimWiki
- `jira` - Jira markup

**Other**:
- `org` - Emacs Org mode
- `textile` - Textile
- `ipynb` - Jupyter Notebook
- `csv` - CSV table
- `tsv` - TSV table
- `json` - JSON
- `fb2` - FictionBook 2
- `man` - Man page
- `typst` - Typst

### Output Formats

```bash
# List all output formats
pandoc --list-output-formats
```

**All input formats** plus:

**PDF** (via LaTeX):
- `pdf`

**Presentation**:
- `beamer` - LaTeX Beamer
- `revealjs` - reveal.js
- `pptx` - PowerPoint
- `slidy` - Slidy
- `dzslides` - DZSlides
- `s5` - S5

**Other Outputs**:
- `plain` - Plain text
- `context` - ConTeXt
- `texinfo` - Texinfo
- `ms` - groff ms
- `icml` - InCopy ICML
- `opml` - OPML
- `chunkedhtml` - Chunked HTML
- `ansi` - ANSI terminal

---

## Conversion Options

### Common Options

| Option | Description |
|--------|-------------|
| `-f, --from=FORMAT` | Input format |
| `-t, --to=FORMAT` | Output format |
| `-o, --output=FILE` | Output file |
| `-s, --standalone` | Complete document |
| `--extract-media=DIR` | Extract images to directory |
| `--wrap=auto/none/preserve` | Text wrapping |
| `--columns=N` | Line width for wrapping |

### Word-Specific Options

```bash
# Extract images when converting from Word
pandoc --extract-media=./images input.docx -o output.md

# Handle track changes
pandoc --track-changes=accept input.docx -o output.md
pandoc --track-changes=reject input.docx -o output.md
pandoc --track-changes=all input.docx -o output.md  # Show all
```

### HTML-Specific Options

```bash
# Standalone HTML with CSS
pandoc -s -c style.css input.md -o output.html

# Self-contained (embedded resources)
pandoc -s --embed-resources input.md -o output.html
```

### LaTeX-Specific Options

```bash
# Use custom template
pandoc --template=custom.tex input.md -o output.tex

# Set document class
pandoc -V documentclass=article input.md -o output.tex
```

---

## Examples

### Example 1: Word to Markdown

**User**: `/pandoc-convert report.docx report.md`

**Claude executes**:
```bash
pandoc report.docx \
  --extract-media=./media \
  --wrap=none \
  -o report.md
```

### Example 2: HTML to Word

**User**: `/pandoc-convert webpage.html document.docx`

**Claude executes**:
```bash
pandoc webpage.html -o document.docx
```

### Example 3: Jupyter to Markdown

**User**: "Convert my notebook to Markdown"

**Claude executes**:
```bash
pandoc notebook.ipynb \
  --extract-media=./notebook_files \
  -o notebook.md
```

### Example 4: RST to HTML

**User**: `/pandoc-convert docs.rst docs.html`

**Claude executes**:
```bash
pandoc -s docs.rst -o docs.html
```

### Example 5: Multiple Markdown to Single HTML

**User**: "Combine all .md files into single HTML"

**Claude executes**:
```bash
pandoc -s \
  *.md \
  --toc \
  -o combined.html
```

### Example 6: LaTeX to Word

**User**: "Convert my thesis from LaTeX to Word for review"

**Claude executes**:
```bash
pandoc thesis.tex \
  --bibliography=refs.bib \
  --citeproc \
  -o thesis.docx
```

### Example 7: Wiki to Markdown

**User**: "Convert MediaWiki export to Markdown"

**Claude executes**:
```bash
pandoc -f mediawiki wiki-export.txt -o documentation.md
```

---

## Batch Conversion

### Convert Multiple Files

**Bash**:
```bash
# Convert all .docx to .md
for f in *.docx; do
    pandoc "$f" -o "${f%.docx}.md"
done

# Convert all .md to .html
for f in *.md; do
    pandoc -s "$f" -o "${f%.md}.html"
done
```

**PowerShell**:
```powershell
# Convert all .docx to .md
Get-ChildItem *.docx | ForEach-Object {
    pandoc $_.Name -o ($_.BaseName + ".md")
}
```

### Batch Conversion Command

**User**: `/pandoc-convert --batch *.docx --to=markdown`

**Claude executes**:
```bash
for f in *.docx; do
    echo "Converting: $f"
    pandoc "$f" --extract-media="./media" -o "${f%.docx}.md"
done
```

---

## Quality Considerations

### Conversion Quality Matrix

| From → To | Quality | Notes |
|-----------|---------|-------|
| Word → Markdown | Good | Tables and basic formatting preserved |
| Markdown → Word | Excellent | Full fidelity |
| HTML → Markdown | Good | Complex layouts may simplify |
| LaTeX → Word | Good | Math may need adjustment |
| Word → LaTeX | Good | May need manual cleanup |
| PDF → Markdown | N/A | PDF is not a supported input |

### Tips for Best Results

1. **Word → Markdown**: Use styles in Word for better conversion
2. **HTML → Markdown**: Clean HTML converts better
3. **With Images**: Always use `--extract-media`
4. **Tables**: Prefer simple tables for best conversion
5. **Complex Documents**: May need manual post-processing

---

## Troubleshooting

### Encoding Issues

```
[ERROR] UTF-8 encoding error

Solution:
1. Save file as UTF-8: Open in editor, Save As, select UTF-8
2. Specify input encoding if needed
```

### Missing Images

```
[WARNING] Images not found in output

Solution:
1. Use --extract-media=./images
2. Ensure source images are accessible
3. Check file paths are relative
```

### Formatting Loss

```
[INFO] Some formatting may be lost

Complex formatting (columns, text boxes, etc.) may not
convert perfectly. Post-conversion editing may be needed.

For best results:
- Use standard styles in source documents
- Simplify complex layouts before converting
```

---

## Related Commands

| Command | Description |
|---------|-------------|
| `/pandoc-pdf` | Convert to PDF |
| `/pandoc-docx` | Convert to Word |
| `/pandoc-html` | Convert to HTML |
| `/pandoc-epub` | Convert to EPUB |
| `/pandoc` | Main help |

---

*Pandoc Plugin v1.0*
*Universal Format Conversion*
