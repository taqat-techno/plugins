---
title: 'Pandoc Slides'
read_only: false
type: 'command'
description: 'Create professional presentations in reveal.js (HTML), Beamer (PDF), or PowerPoint from Markdown.'
---

# /pandoc-slides - Presentation Creation

Create professional slide presentations from Markdown in multiple formats.

## Usage

```
/pandoc-slides <input-file> [format] [options]
/pandoc-slides presentation.md
/pandoc-slides slides.md --format=revealjs --theme=moon
/pandoc-slides slides.md --format=beamer --theme=Warsaw
/pandoc-slides slides.md --format=pptx
```

---

## Supported Formats

| Format | Output | Description |
|--------|--------|-------------|
| `revealjs` | HTML | Interactive web-based slides (default) |
| `beamer` | PDF | LaTeX-based PDF slides |
| `pptx` | PPTX | Microsoft PowerPoint |
| `slidy` | HTML | W3C Slidy (simpler HTML) |
| `dzslides` | HTML | DZSlides (single file) |
| `s5` | HTML | S5 slideshow |

---

## Complete Workflow

### Step 1: Choose Format

```
============================================================
                  PRESENTATION OPTIONS
============================================================

INPUT: presentation.md

SELECT OUTPUT FORMAT:

  [1] reveal.js (HTML) - Recommended
      Interactive web slides with themes and transitions
      Best for: Web, sharing, modern presentations

  [2] Beamer (PDF)
      Professional LaTeX-based PDF slides
      Best for: Academic, conferences, printing

  [3] PowerPoint (PPTX)
      Microsoft PowerPoint format
      Best for: Corporate, editing in PowerPoint

  [4] Slidy (HTML)
      Simple HTML slideshow
      Best for: Basic presentations

Enter choice (1-4) or format name:
============================================================
```

### Step 2: Build and Execute

---

## reveal.js (HTML Slides)

### Basic Command

```bash
pandoc -t revealjs -s slides.md -o presentation.html
```

### With Theme

```bash
pandoc -t revealjs -s \
  -V theme=moon \
  slides.md -o presentation.html
```

### With Transition

```bash
pandoc -t revealjs -s \
  -V theme=moon \
  -V transition=slide \
  slides.md -o presentation.html
```

### Full-Featured

```bash
pandoc -t revealjs -s \
  -V theme=night \
  -V transition=convex \
  -V revealjs-url=https://unpkg.com/reveal.js@4/ \
  -V controls=true \
  -V progress=true \
  -V slideNumber=true \
  -V hash=true \
  slides.md -o presentation.html
```

### reveal.js Options

| Option | Values | Description |
|--------|--------|-------------|
| `theme` | black, white, league, beige, sky, night, serif, simple, solarized, moon, dracula | Visual theme |
| `transition` | none, fade, slide, convex, concave, zoom | Slide transition |
| `controls` | true/false | Navigation controls |
| `progress` | true/false | Progress bar |
| `slideNumber` | true/false | Slide numbers |
| `hash` | true/false | URL hashes |
| `center` | true/false | Center content |
| `width` | pixels | Slide width |
| `height` | pixels | Slide height |

### reveal.js Themes

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

---

## Beamer (PDF Slides)

### Basic Command

```bash
pandoc -t beamer slides.md -o presentation.pdf
```

### With Theme

```bash
pandoc -t beamer \
  -V theme:Warsaw \
  slides.md -o presentation.pdf
```

### With Color Theme

```bash
pandoc -t beamer \
  -V theme:Madrid \
  -V colortheme:dolphin \
  slides.md -o presentation.pdf
```

### Widescreen Format

```bash
pandoc -t beamer \
  -V theme:Warsaw \
  -V aspectratio=169 \
  slides.md -o presentation.pdf
```

### Full-Featured

```bash
pandoc -t beamer \
  -V theme:Madrid \
  -V colortheme:seahorse \
  -V fonttheme:structurebold \
  -V aspectratio=169 \
  -V navigation=horizontal \
  --toc \
  slides.md -o presentation.pdf
```

### Beamer Themes

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

### Beamer Color Themes

`albatross`, `beaver`, `beetle`, `crane`, `default`, `dolphin`, `dove`, `fly`, `lily`, `monarca`, `orchid`, `rose`, `seagull`, `seahorse`, `sidebartab`, `spruce`, `structure`, `whale`, `wolverine`

---

## PowerPoint (PPTX)

### Basic Command

```bash
pandoc slides.md -o presentation.pptx
```

### With Reference Template

```bash
pandoc slides.md \
  --reference-doc=template.pptx \
  -o presentation.pptx
```

### Creating PowerPoint Template

1. Generate default template:
   ```bash
   pandoc -o template.pptx --print-default-data-file reference.pptx
   ```
2. Open in PowerPoint
3. Modify slide masters and layouts
4. Save and use with `--reference-doc`

---

## Slide Markdown Format

### Basic Structure

```markdown
---
title: "Presentation Title"
author: "Your Name"
date: "January 15, 2025"
---

# Section Title

## Slide Title

- Bullet point 1
- Bullet point 2
- Bullet point 3

## Another Slide

Content here.

# Another Section

## Slide in New Section

More content.
```

### Incremental Lists

```markdown
## Incremental Bullets

::: incremental

- First item (appears first)
- Second item (appears second)
- Third item (appears third)

:::
```

Or use pause:

```markdown
## With Pauses

- First item

. . .

- Second item (after pause)

. . .

- Third item (after another pause)
```

### Two-Column Layout

```markdown
## Two Columns

:::::::::::::: {.columns}
::: {.column width="50%"}

Left column content

- Point 1
- Point 2

:::
::: {.column width="50%"}

Right column content

- Point A
- Point B

:::
::::::::::::::
```

### Images

```markdown
## Slide with Image

![Image Caption](image.png){width=80%}
```

### Speaker Notes

```markdown
## Slide with Notes

Content visible to audience.

::: notes

These are speaker notes.
Only visible in presenter view.

:::
```

### Background Images (reveal.js)

```markdown
## {data-background-image="background.jpg"}

Content on custom background
```

### Code with Highlighting

````markdown
## Code Example

```python
def hello():
    print("Hello, World!")
```
````

---

## Examples

### Example 1: Quick reveal.js

**User**: `/pandoc-slides talk.md`

**Claude executes**:
```bash
pandoc -t revealjs -s talk.md -o talk.html
```

### Example 2: Themed reveal.js

**User**: `/pandoc-slides demo.md --format=revealjs --theme=moon`

**Claude executes**:
```bash
pandoc -t revealjs -s \
  -V theme=moon \
  -V transition=slide \
  -V controls=true \
  -V progress=true \
  demo.md -o demo.html
```

### Example 3: Academic Beamer

**User**: `/pandoc-slides lecture.md --format=beamer --theme=Warsaw`

**Claude executes**:
```bash
pandoc -t beamer \
  -V theme:Warsaw \
  -V colortheme:dolphin \
  -V aspectratio=169 \
  lecture.md -o lecture.pdf
```

### Example 4: Corporate PowerPoint

**User**: "Create PowerPoint from slides.md"

**Claude executes**:
```bash
pandoc slides.md \
  --reference-doc=company-template.pptx \
  -o presentation.pptx
```

### Example 5: Conference Presentation

**User**: "Create professional conference slides with TOC"

**Claude executes**:
```bash
pandoc -t beamer \
  -V theme:Madrid \
  -V colortheme:seahorse \
  -V aspectratio=169 \
  --toc \
  -V toc-title="Outline" \
  conference-talk.md -o conference-talk.pdf
```

---

## Output Report

**Success:**

```
============================================================
            PRESENTATION CREATED SUCCESSFULLY
============================================================

INPUT:      presentation.md (5 KB)
OUTPUT:     presentation.html (48 KB)
FORMAT:     reveal.js

OPTIONS:
  ✓ Theme: moon
  ✓ Transition: slide
  ✓ Controls: enabled
  ✓ Progress bar: enabled
  ✓ Slide numbers: enabled

SLIDES:     15 slides in 4 sections

OUTPUT FILE: C:\Users\ahmed\Documents\presentation.html

TO VIEW:
  • Open in web browser
  • Or serve: python -m http.server 8000

KEYBOARD SHORTCUTS:
  → / Space    Next slide
  ← / Backspace  Previous slide
  Esc          Overview mode
  S            Speaker notes
  F            Fullscreen
  ?            Help

============================================================
```

---

## YAML Front Matter for Slides

### reveal.js

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

### Beamer

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

## Troubleshooting

### reveal.js Not Loading

```
[ERROR] Styles not loading

Solutions:
1. Use CDN: -V revealjs-url=https://unpkg.com/reveal.js@4/
2. Or install locally: npm install reveal.js
3. Check internet connection for CDN
```

### Beamer Compilation Error

```
[ERROR] LaTeX error

Solutions:
1. Install LaTeX: choco install miktex
2. Install Beamer: tlmgr install beamer
3. Check for syntax errors in Markdown
```

### PowerPoint Formatting Issues

```
[TIP] Customize PowerPoint output

1. Create reference template from default
2. Modify slide masters in PowerPoint
3. Use --reference-doc=template.pptx
```

---

## Related Commands

| Command | Description |
|---------|-------------|
| `/pandoc-pdf` | Convert to PDF |
| `/pandoc-html` | Convert to HTML |
| `/pandoc` | Main help |

---

*Pandoc Plugin v1.0*
*Professional Presentation Creation*
