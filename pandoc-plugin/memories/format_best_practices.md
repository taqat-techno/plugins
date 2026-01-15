# Format Conversion Best Practices

## Memory: Format-Specific Recommendations

This memory contains best practices for different format conversions that Claude should apply automatically.

---

## Installation & Setup (CRITICAL)

### Before ANY conversion, verify setup:
1. Check if Pandoc is installed: `pandoc --version`
2. For PDF: Check LaTeX: `pdflatex --version`
3. If missing, direct user to run `/pandoc-setup`

### Windows-Specific PATH Issues:
- Pandoc installs to: `%LOCALAPPDATA%\Pandoc\`
- MiKTeX installs to: `%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64\`
- If "command not found", add these to PATH or use full paths

### MiKTeX Auto-Install (CRITICAL for Windows):
- **ALWAYS** ensure auto-install is enabled before PDF conversion
- Command: `initexmf --set-config-value=[MPM]AutoInstall=1`
- Without this, users get popup dialogs for EVERY missing package

### Required LaTeX Packages (pre-install to avoid popups):
```
parskip, geometry, fancyvrb, framed, booktabs, longtable,
upquote, microtype, bookmark, etoolbox, hyperref, ulem,
listings, caption, float, setspace, amsmath, lm, xcolor,
graphicx, fontspec, unicode-math
```

### Quick Fix Commands (Windows):
```powershell
# Enable auto-install
& "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64\initexmf.exe" --set-config-value="[MPM]AutoInstall=1"

# Install package manually
& "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64\miktex.exe" packages install <package-name>
```

---

## PDF Generation

### When generating PDF:
1. Always check LaTeX is installed first
2. Recommend XeLaTeX for custom fonts or Unicode
3. Default to 1-inch margins unless specified
4. Use `--toc` for documents longer than 5 pages
5. Enable `-N` (numbering) for technical documents

### Academic Papers:
- Use `--citeproc` with `--bibliography`
- Default CSL: IEEE or APA based on context
- Set `linestretch=1.5` for readability
- Use `documentclass=article` for short papers, `report` for thesis

---

## Word Document Generation

### When generating DOCX:
1. Suggest creating a reference template for consistent styling
2. Use `--toc` for formal documents
3. Extract media when converting FROM Word: `--extract-media=./media`
4. Mention that styles can be customized via reference doc

### Corporate Documents:
- Ask if they have a company template
- Recommend creating one for consistent branding

---

## HTML Generation

### When generating HTML:
1. Always use `-s` (standalone) for complete documents
2. Suggest CSS styling for better appearance
3. Use `--highlight-style=tango` for code-heavy content
4. Recommend `--embed-resources` for portable single-file HTML
5. Use `--mathjax` or `--katex` for math content

### Documentation Sites:
- Include `--toc` with `--toc-depth=3`
- Add section numbering with `-N`

---

## EPUB Generation

### When generating EPUB:
1. Always recommend a cover image (1600x2400 recommended)
2. Suggest creating metadata.xml for proper eBook metadata
3. Include custom CSS for consistent eReader appearance
4. Use `--toc` for navigable books
5. Default to EPUB 3 for modern readers

### Book Projects:
- Recommend organizing chapters as separate files
- Suggest front matter (title, copyright) and back matter

---

## Slides Generation

### reveal.js (HTML):
1. Default theme: `moon` or `black` (professional)
2. Enable controls and progress bar
3. Use CDN for portability: `revealjs-url=https://unpkg.com/reveal.js@4/`

### Beamer (PDF):
1. Default theme: `Madrid` or `Warsaw`
2. Use 16:9 aspect ratio: `-V aspectratio=169`
3. Include TOC for longer presentations

### PowerPoint:
1. Suggest reference template for company branding
2. Note that animations won't transfer from Markdown

---

## General Conversion

### From Word to Markdown:
- Always use `--extract-media=./media`
- Use `--wrap=none` to preserve paragraph structure
- Mention manual cleanup may be needed for complex formatting

### From HTML to Markdown:
- Use clean, well-structured HTML for best results
- Complex layouts may simplify

### Batch Conversions:
- Offer to create a shell script for multiple files
- Suggest Makefile for repeated builds

---

## Error Prevention

### Always verify before conversion:
1. Input file exists
2. Pandoc is installed
3. LaTeX is installed (for PDF)
4. Output directory is writable

### Common issues to warn about:
- PDF without LaTeX
- Custom fonts without XeLaTeX
- Large images in EPUB
- Complex Word formatting loss
