---
type: llm
---
PASS if the reply says the PDF must be generated with the xelatex engine (--pdf-engine=xelatex) instead of the default pdflatex, and sets an Arabic-capable font such as Amiri or Cairo via -V mainfont, and sets right-to-left direction via -V dir=rtl (and/or -V lang=ar).
FAIL if the reply only gives generic PDF troubleshooting advice (checking file encoding, reinstalling pandoc, "try a different font") without naming the xelatex engine switch, or if it recommends the default pdflatex engine for Arabic content.
