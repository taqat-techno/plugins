---
title: 'Pandoc EPUB'
read_only: false
type: 'command'
description: 'Create professional EPUB eBooks for Kindle, Apple Books, and other e-readers with covers, metadata, and custom styling.'
---

# /pandoc-epub - eBook Creation

Create professional EPUB eBooks from Markdown, Word, HTML, or other formats.

## Usage

```
/pandoc-epub <input-file> [options]
/pandoc-epub book.md
/pandoc-epub book.md --cover=cover.jpg
/pandoc-epub ch1.md ch2.md ch3.md --toc
```

---

## Complete Workflow

### Step 1: Gather eBook Information

```
============================================================
                    EBOOK CREATION OPTIONS
============================================================

INPUT: book.md

METADATA (enter or press Enter to skip):

  Title:      [My Book Title]
  Author:     [Author Name]
  Publisher:  [Publisher]
  Date:       [2025-01-15]
  Language:   [en-US]

OPTIONS:

  [1] Cover Image
      Path to cover image (JPG/PNG, recommended 1600x2400):
      [cover.jpg]

  [2] Table of Contents
      □ No TOC
      ■ Include TOC (default)

  [3] EPUB Version
      □ EPUB 2 (older devices)
      ■ EPUB 3 (default, modern)

  [4] Custom Stylesheet
      Path to CSS file (optional):
      [style.css]

============================================================
```

### Step 2: Build Command

```bash
# Basic EPUB
pandoc input.md -o output.epub

# With cover image
pandoc input.md --epub-cover-image=cover.jpg -o output.epub

# With metadata
pandoc input.md \
  --epub-cover-image=cover.jpg \
  --epub-metadata=metadata.xml \
  -o output.epub

# With custom CSS
pandoc input.md \
  --epub-stylesheet=ebook.css \
  --epub-cover-image=cover.jpg \
  -o output.epub

# Multiple chapters
pandoc \
  title.md \
  ch1.md \
  ch2.md \
  ch3.md \
  --toc \
  --epub-cover-image=cover.jpg \
  -o book.epub

# EPUB 3
pandoc input.md -t epub3 -o output.epub
```

### Step 3: Execute and Report

**Success:**

```
============================================================
                EPUB CREATED SUCCESSFULLY
============================================================

INPUT FILES:  5 (title.md, ch1.md, ch2.md, ch3.md, afterword.md)
OUTPUT:       my-book.epub (1.2 MB)

METADATA:
  Title:      My Book Title
  Author:     Author Name
  Language:   en-US
  Date:       2025-01-15

FEATURES:
  ✓ Cover Image: cover.jpg
  ✓ Table of Contents
  ✓ EPUB 3 Format
  ✓ Custom Stylesheet

OUTPUT FILE: C:\Users\ahmed\Documents\my-book.epub

COMPATIBLE WITH:
  • Apple Books
  • Kindle (convert with Calibre)
  • Kobo
  • Google Play Books
  • Most e-readers

============================================================
```

---

## Options Reference

### Basic Options

| Option | Description | Example |
|--------|-------------|---------|
| `-o FILE` | Output file | `-o book.epub` |
| `-t epub3` | EPUB 3 format | `-t epub3` |
| `-t epub2` | EPUB 2 format | `-t epub2` |
| `--toc` | Include TOC | `--toc` |
| `--toc-depth=N` | TOC depth | `--toc-depth=2` |

### Cover and Images

| Option | Description | Example |
|--------|-------------|---------|
| `--epub-cover-image=FILE` | Cover image | `--epub-cover-image=cover.jpg` |
| `--resource-path=DIR` | Image search path | `--resource-path=./images` |

### Metadata

| Option | Description | Example |
|--------|-------------|---------|
| `--epub-metadata=FILE` | Metadata XML file | `--epub-metadata=meta.xml` |
| `--metadata title="X"` | Set title | `--metadata title="My Book"` |
| `--metadata author="X"` | Set author | `--metadata author="John Doe"` |

### Styling

| Option | Description | Example |
|--------|-------------|---------|
| `--epub-stylesheet=FILE` | Custom CSS | `--epub-stylesheet=ebook.css` |
| `--epub-embed-font=FILE` | Embed font | `--epub-embed-font=font.ttf` |

### Chapter Options

| Option | Description | Example |
|--------|-------------|---------|
| `--epub-chapter-level=N` | Chapter heading level | `--epub-chapter-level=1` |
| `--split-level=N` | Split at heading level | `--split-level=1` |

---

## Metadata File

Create `metadata.xml`:

```xml
<dc:title>My Book Title</dc:title>
<dc:creator opf:role="aut">Author Name</dc:creator>
<dc:language>en-US</dc:language>
<dc:date>2025-01-15</dc:date>
<dc:publisher>My Publisher</dc:publisher>
<dc:rights>Copyright 2025 Author Name</dc:rights>
<dc:description>
A compelling description of the book that will
appear in e-reader libraries and stores.
</dc:description>
<dc:subject>Fiction</dc:subject>
<dc:subject>Adventure</dc:subject>
```

---

## YAML Front Matter

Include in your first Markdown file:

```yaml
---
title: "My Book Title"
subtitle: "An Amazing Subtitle"
author:
  - name: "Author Name"
    affiliation: "Publisher"
date: "2025"
lang: en-US
rights: "Copyright 2025 Author Name. All rights reserved."
description: |
  A compelling description of your book.
  This appears in e-reader libraries.
cover-image: cover.jpg
css: ebook.css
toc: true
toc-depth: 2
---
```

---

## eBook Stylesheet

Create `ebook.css`:

```css
/* ebook.css - Optimized for e-readers */

body {
    font-family: Georgia, serif;
    font-size: 1em;
    line-height: 1.6;
    margin: 0;
    padding: 0;
}

h1 {
    font-size: 2em;
    margin-top: 2em;
    margin-bottom: 0.5em;
    text-align: center;
    page-break-before: always;
}

h2 {
    font-size: 1.5em;
    margin-top: 1.5em;
}

h3 {
    font-size: 1.2em;
    margin-top: 1em;
}

p {
    text-indent: 1.5em;
    margin: 0;
    text-align: justify;
}

p.first, h1 + p, h2 + p, h3 + p {
    text-indent: 0;
}

blockquote {
    margin: 1em 2em;
    font-style: italic;
}

.chapter-title {
    text-align: center;
    margin-top: 3em;
    margin-bottom: 2em;
}

.scene-break {
    text-align: center;
    margin: 2em 0;
}

.scene-break::before {
    content: "* * *";
}

/* Images */
img {
    max-width: 100%;
    height: auto;
}

figure {
    text-align: center;
    margin: 1em 0;
}

figcaption {
    font-style: italic;
    font-size: 0.9em;
}

/* Code (for technical books) */
code {
    font-family: monospace;
    font-size: 0.9em;
    background: #f4f4f4;
}

pre {
    white-space: pre-wrap;
    background: #f4f4f4;
    padding: 0.5em;
    font-size: 0.85em;
}
```

---

## Examples

### Example 1: Simple eBook

**User**: `/pandoc-epub novel.md`

**Claude executes**:
```bash
pandoc novel.md -o novel.epub
```

### Example 2: eBook with Cover

**User**: `/pandoc-epub book.md --cover=cover.jpg`

**Claude executes**:
```bash
pandoc book.md \
  --epub-cover-image=cover.jpg \
  --toc \
  -o book.epub
```

### Example 3: Multi-Chapter Book

**User**: "Create eBook from all chapter files"

**Claude executes**:
```bash
pandoc \
  frontmatter.md \
  chapter-01.md \
  chapter-02.md \
  chapter-03.md \
  chapter-04.md \
  backmatter.md \
  --epub-cover-image=cover.jpg \
  --epub-stylesheet=ebook.css \
  --toc \
  --toc-depth=1 \
  --metadata title="My Novel" \
  --metadata author="Jane Author" \
  -o my-novel.epub
```

### Example 4: Technical eBook

**User**: "Create technical eBook with code highlighting"

**Claude executes**:
```bash
pandoc technical-guide.md \
  -t epub3 \
  --epub-cover-image=cover.png \
  --highlight-style=tango \
  --toc \
  --toc-depth=3 \
  -N \
  -o technical-guide.epub
```

### Example 5: From Word Document

**User**: "Convert my Word manuscript to EPUB"

**Claude executes**:
```bash
pandoc manuscript.docx \
  --epub-cover-image=cover.jpg \
  --toc \
  -o manuscript.epub
```

---

## Cover Image Guidelines

### Recommended Specifications

| Property | Recommendation |
|----------|----------------|
| **Dimensions** | 1600 x 2400 pixels (2:3 ratio) |
| **Format** | JPEG or PNG |
| **File Size** | Under 5 MB |
| **Color Mode** | RGB |
| **DPI** | 72-300 |

### Minimum Specifications

| Platform | Minimum Size |
|----------|--------------|
| Kindle | 625 x 1000 pixels |
| Apple Books | 1400 x 2100 pixels |
| Kobo | 1072 x 1448 pixels |
| General | 800 x 1200 pixels |

---

## Book Structure

### Recommended File Organization

```
book-project/
├── manuscript/
│   ├── 00-frontmatter.md    # Title, copyright, dedication
│   ├── 01-chapter-one.md
│   ├── 02-chapter-two.md
│   ├── 03-chapter-three.md
│   └── 99-backmatter.md     # Acknowledgments, about author
├── images/
│   ├── cover.jpg
│   └── illustrations/
├── styles/
│   └── ebook.css
├── metadata.xml
└── build.sh                  # Build script
```

### Build Script

```bash
#!/bin/bash
# build.sh - Build eBook

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

---

## Converting to Other eBook Formats

### Kindle (MOBI/AZW3)

Use Calibre (free software):

```bash
# Install Calibre, then:
ebook-convert book.epub book.mobi
ebook-convert book.epub book.azw3
```

Or use Amazon's Kindle Previewer/KindleGen.

### PDF

```bash
# High-quality PDF from EPUB
pandoc book.epub -o book.pdf

# Or directly from Markdown
pandoc book.md --pdf-engine=xelatex -o book.pdf
```

---

## Validation

### Validate EPUB

Use [EPUBCheck](https://www.w3.org/publishing/epubcheck/):

```bash
java -jar epubcheck.jar book.epub
```

Or online validator: https://validator.idpf.org/

---

## Troubleshooting

### Images Not Appearing

```
[WARNING] Images missing in EPUB

Solutions:
1. Use relative paths: ![](images/photo.jpg)
2. Set resource path: --resource-path=./images
3. Ensure images are in same directory as markdown files
```

### Cover Not Showing

```
[WARNING] Cover image not displaying

Check:
1. Image format is JPG or PNG
2. Path is correct (relative to command execution)
3. Image is readable: ls -la cover.jpg
```

### Large File Size

```
[TIP] Reduce EPUB file size

1. Optimize images before including
2. Use JPEG instead of PNG for photos
3. Reduce image dimensions
4. Remove unnecessary images
```

---

## Related Commands

| Command | Description |
|---------|-------------|
| `/pandoc-pdf` | Convert to PDF |
| `/pandoc-docx` | Convert to Word |
| `/pandoc-html` | Convert to HTML |
| `/pandoc` | Main help |

---

*Pandoc Plugin v1.0*
*Professional eBook Creation*
