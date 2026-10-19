---
description: Show the installed Pandoc version and available PDF engines
---

# /pandoc:status

Run and summarise, without installing anything:

```bash
pandoc --version
pdflatex --version
xelatex --version
```

Report the Pandoc version (3.0 or later is expected), which PDF engines are
available, and what does not work without the missing pieces (no LaTeX: no PDF
output via LaTeX; HTML, DOCX, EPUB and the rest still work). If Pandoc is
missing, point to `/pandoc:setup`.
