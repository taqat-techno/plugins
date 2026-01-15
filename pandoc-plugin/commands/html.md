---
title: 'Pandoc HTML'
read_only: false
type: 'command'
description: 'Convert documents to HTML web pages with custom CSS, syntax highlighting, and math rendering.'
---

# /pandoc-html - HTML Web Page Generation

Generate HTML web pages from Markdown, Word, LaTeX, or other formats.

## Usage

```
/pandoc-html <input-file> [options]
/pandoc-html document.md
/pandoc-html document.md --toc --css=style.css
/pandoc-html document.md --self-contained
```

---

## Complete Workflow

### Step 1: Build Command

```bash
# Basic standalone HTML
pandoc -s input.md -o output.html

# With custom CSS
pandoc -s -c style.css input.md -o output.html

# Self-contained (embedded resources)
pandoc -s --embed-resources input.md -o output.html

# With table of contents
pandoc -s --toc input.md -o output.html

# With syntax highlighting
pandoc -s --highlight-style=tango input.md -o output.html

# With math (MathJax)
pandoc -s --mathjax input.md -o output.html

# HTML5 output
pandoc -s -t html5 input.md -o output.html
```

### Step 2: Execute and Report

**Success:**

```
============================================================
              HTML GENERATED SUCCESSFULLY
============================================================

INPUT:     document.md (8 KB)
OUTPUT:    document.html (15 KB)

OPTIONS APPLIED:
  ✓ Standalone document (-s)
  ✓ HTML5 output
  ✓ Syntax highlighting: tango

OUTPUT FILE: C:\Users\ahmed\Documents\document.html

VIEW: Open in browser or serve with:
  python -m http.server 8000

============================================================
```

---

## Options Reference

### Basic Options

| Option | Description | Example |
|--------|-------------|---------|
| `-s, --standalone` | Complete HTML document | `-s` |
| `-o FILE` | Output file | `-o output.html` |
| `-t html5` | HTML5 output | `-t html5` |
| `--toc` | Table of contents | `--toc` |
| `-N, --number-sections` | Number sections | `-N` |

### Styling Options

| Option | Description | Example |
|--------|-------------|---------|
| `-c, --css=URL` | Link CSS stylesheet | `-c style.css` |
| `-H, --include-in-header=FILE` | Include in `<head>` | `-H header.html` |
| `-B, --include-before-body=FILE` | Include at start of body | `-B nav.html` |
| `-A, --include-after-body=FILE` | Include at end of body | `-A footer.html` |
| `--template=FILE` | Custom HTML template | `--template=custom.html` |

### Resource Options

| Option | Description | Example |
|--------|-------------|---------|
| `--embed-resources` | Embed all resources | `--embed-resources` |
| `--self-contained` | Alias for embed-resources | `--self-contained` |
| `--resource-path=DIR` | Resource search path | `--resource-path=./images` |

### Code Highlighting

| Option | Description | Example |
|--------|-------------|---------|
| `--highlight-style=STYLE` | Highlight style | `--highlight-style=tango` |
| `--no-highlight` | Disable highlighting | `--no-highlight` |

**Available Styles**: `pygments`, `tango`, `espresso`, `zenburn`, `kate`, `monochrome`, `breezeDark`, `haddock`

### Math Rendering

| Option | Description | Example |
|--------|-------------|---------|
| `--mathjax` | Use MathJax (CDN) | `--mathjax` |
| `--katex` | Use KaTeX | `--katex` |
| `--mathml` | Native MathML | `--mathml` |
| `--webtex` | Convert to images | `--webtex` |

---

## Preset Configurations

### `/pandoc-html document.md --preset blog`

```bash
pandoc -s \
  -t html5 \
  --toc \
  -c style.css \
  --highlight-style=tango \
  --metadata title="Blog Post" \
  document.md -o document.html
```

### `/pandoc-html document.md --preset docs`

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

### `/pandoc-html document.md --preset email`

```bash
pandoc -s \
  --embed-resources \
  document.md -o document.html
```

### `/pandoc-html document.md --preset minimal`

```bash
pandoc document.md -o document.html
```

---

## Custom Templates

### Creating HTML Template

Save as `template.html`:

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

**Use template:**

```bash
pandoc -s --template=template.html input.md -o output.html
```

---

## Examples

### Example 1: Simple HTML

**User**: `/pandoc-html readme.md`

**Claude executes**:
```bash
pandoc -s readme.md -o readme.html
```

### Example 2: Styled Documentation

**User**: `/pandoc-html docs.md --toc --css=styles.css`

**Claude executes**:
```bash
pandoc -s \
  --toc \
  --toc-depth=3 \
  -c styles.css \
  docs.md -o docs.html
```

### Example 3: Self-Contained Email

**User**: "Create HTML email I can send"

**Claude executes**:
```bash
pandoc -s \
  --embed-resources \
  --metadata title="Newsletter" \
  newsletter.md -o newsletter.html
```

### Example 4: Technical Documentation

**User**: "Generate docs with syntax highlighting and math"

**Claude executes**:
```bash
pandoc -s \
  -t html5 \
  --toc \
  -N \
  --highlight-style=tango \
  --mathjax \
  technical-docs.md -o docs.html
```

### Example 5: Multi-File Website

**User**: "Combine all pages into single HTML"

**Claude executes**:
```bash
pandoc -s \
  index.md \
  about.md \
  contact.md \
  --toc \
  -c site.css \
  -o website.html
```

---

## CSS Styling Tips

### Basic Stylesheet

```css
/* style.css */
body {
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    line-height: 1.6;
    color: #333;
}

h1, h2, h3 {
    color: #2c3e50;
    margin-top: 1.5em;
}

code {
    background: #f4f4f4;
    padding: 0.2em 0.4em;
    border-radius: 3px;
    font-size: 0.9em;
}

pre {
    background: #f4f4f4;
    padding: 1rem;
    border-radius: 5px;
    overflow-x: auto;
}

blockquote {
    border-left: 4px solid #3498db;
    margin: 1em 0;
    padding-left: 1em;
    color: #666;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
}

th, td {
    border: 1px solid #ddd;
    padding: 0.5em;
    text-align: left;
}

th {
    background: #f4f4f4;
}

#toc {
    background: #f9f9f9;
    padding: 1rem;
    border-radius: 5px;
    margin-bottom: 2rem;
}
```

---

## Converting HTML TO Other Formats

```bash
# HTML to Markdown
pandoc input.html -o output.md

# HTML to Word
pandoc input.html -o output.docx

# HTML to PDF
pandoc input.html -o output.pdf

# HTML to EPUB
pandoc input.html -o output.epub
```

---

## YAML Front Matter

```yaml
---
title: "Page Title"
author: "Author Name"
date: "January 15, 2025"
lang: en
toc: true
toc-depth: 2
numbersections: true
css:
  - style.css
  - custom.css
header-includes: |
  <style>
    body { background: #fafafa; }
  </style>
---
```

---

## Related Commands

| Command | Description |
|---------|-------------|
| `/pandoc-pdf` | Convert to PDF |
| `/pandoc-docx` | Convert to Word |
| `/pandoc-epub` | Convert to EPUB |
| `/pandoc-slides` | Create slides (reveal.js) |
| `/pandoc` | Main help |

---

*Pandoc Plugin v1.0*
*Professional HTML Generation*
