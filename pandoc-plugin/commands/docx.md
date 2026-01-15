---
title: 'Pandoc DOCX'
read_only: false
type: 'command'
description: 'Convert documents to Microsoft Word (.docx) format with custom styling and templates.'
---

# /pandoc-docx - Word Document Generation

Generate Microsoft Word documents from Markdown, HTML, LaTeX, or other formats.

## Usage

```
/pandoc-docx <input-file> [options]
/pandoc-docx document.md
/pandoc-docx document.md --toc
/pandoc-docx document.md --template=reference.docx
```

---

## Complete Workflow

### Step 1: Check Input File

```bash
# Verify file exists
ls -la "${INPUT_FILE}"
```

### Step 2: Build Command

```bash
# Basic conversion
pandoc input.md -o output.docx

# With table of contents
pandoc input.md --toc -o output.docx

# With custom reference template
pandoc input.md --reference-doc=template.docx -o output.docx

# From HTML
pandoc input.html -o output.docx

# Multiple inputs combined
pandoc ch1.md ch2.md ch3.md -o book.docx
```

### Step 3: Execute and Report

**Success:**

```
============================================================
            WORD DOCUMENT GENERATED SUCCESSFULLY
============================================================

INPUT:     document.md (12 KB)
OUTPUT:    document.docx (28 KB)

OPTIONS APPLIED:
  ✓ Standard conversion
  ✓ Default Word styling

OUTPUT FILE: C:\Users\ahmed\Documents\document.docx

TIP: For custom styling, create a reference template:
  1. Generate default: pandoc -o ref.docx --print-default-data-file reference.docx
  2. Edit styles in Word
  3. Use: /pandoc-docx input.md --template=ref.docx

============================================================
```

---

## Options Reference

| Option | Description | Example |
|--------|-------------|---------|
| `-o FILE` | Output file | `-o output.docx` |
| `--toc` | Include table of contents | `--toc` |
| `--toc-depth=N` | TOC depth | `--toc-depth=2` |
| `--reference-doc=FILE` | Custom style template | `--reference-doc=template.docx` |
| `-N, --number-sections` | Number section headings | `-N` |
| `--highlight-style=STYLE` | Code highlighting | `--highlight-style=tango` |

---

## Custom Styling with Reference Document

### Creating a Reference Template

**Step 1: Generate Default Template**

```bash
pandoc -o custom-reference.docx --print-default-data-file reference.docx
```

**Step 2: Edit in Microsoft Word**

Open `custom-reference.docx` in Word and modify:
- **Heading 1, 2, 3** styles (fonts, sizes, colors)
- **Normal** text style
- **Code** and **Block Quote** styles
- Page margins and layout
- Headers and footers

**Step 3: Use Template**

```bash
pandoc input.md --reference-doc=custom-reference.docx -o output.docx
```

### Style Mapping

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

---

## Examples

### Example 1: Simple Conversion

**User**: `/pandoc-docx report.md`

**Claude executes**:
```bash
pandoc report.md -o report.docx
```

### Example 2: With Table of Contents

**User**: `/pandoc-docx manual.md --toc`

**Claude executes**:
```bash
pandoc manual.md --toc --toc-depth=3 -o manual.docx
```

### Example 3: Corporate Template

**User**: "Convert to Word using our company template"

**Claude executes**:
```bash
pandoc document.md \
  --reference-doc=company-template.docx \
  --toc \
  -o document.docx
```

### Example 4: From HTML

**User**: "Convert webpage to Word"

**Claude executes**:
```bash
pandoc webpage.html -o webpage.docx
```

### Example 5: Multiple Files

**User**: "Combine all chapters into Word document"

**Claude executes**:
```bash
pandoc \
  intro.md \
  chapter1.md \
  chapter2.md \
  chapter3.md \
  conclusion.md \
  --toc \
  -N \
  -o complete-document.docx
```

---

## Converting Word TO Other Formats

Pandoc also converts FROM Word:

```bash
# Word to Markdown
pandoc input.docx -o output.md

# Word to HTML
pandoc input.docx -o output.html

# Word to PDF (requires LaTeX)
pandoc input.docx -o output.pdf

# Word to LaTeX
pandoc input.docx -o output.tex

# Extract text only
pandoc input.docx -t plain -o output.txt
```

### Extraction Options

```bash
# Extract media/images
pandoc input.docx --extract-media=./images -o output.md

# Track changes (show revisions)
pandoc input.docx --track-changes=all -o output.md
```

---

## YAML Front Matter

Include in your Markdown:

```yaml
---
title: "Document Title"
author: "Author Name"
date: "January 15, 2025"
abstract: |
  Document abstract goes here.
toc: true
toc-depth: 2
numbersections: true
---
```

---

## Troubleshooting

### Images Not Appearing

```
[WARNING] Images not found in output

Solution: Ensure images are in the same directory or use absolute paths:
  ![Image](C:/path/to/image.png)

Or use web URLs:
  ![Image](https://example.com/image.png)
```

### Styles Not Applying

```
[INFO] Custom styles not appearing

Solution:
1. Verify reference-doc path is correct
2. Ensure styles are named correctly in Word
3. Check that styles are applied (not just formatted text)

Regenerate reference doc:
  pandoc -o ref.docx --print-default-data-file reference.docx
```

### Table Formatting Issues

```
[TIP] For better tables, use pipe tables:

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Cell 1   | Cell 2   | Cell 3   |
| Cell 4   | Cell 5   | Cell 6   |
```

---

## Related Commands

| Command | Description |
|---------|-------------|
| `/pandoc-pdf` | Convert to PDF |
| `/pandoc-html` | Convert to HTML |
| `/pandoc-convert` | General conversion |
| `/pandoc` | Main help |

---

*Pandoc Plugin v1.0*
*Professional Word Document Generation*
