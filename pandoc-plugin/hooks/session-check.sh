#!/usr/bin/env bash
# SessionStart hook: Check pandoc and LaTeX availability
# Stdout becomes conversation context. Exit 0 always (non-blocking).

PANDOC_OK=false
LATEX_OK=false
PANDOC_VER=""

if pandoc --version >/dev/null 2>&1; then
  PANDOC_VER=$(pandoc --version 2>/dev/null | head -1)
  PANDOC_OK=true
fi

if pdflatex --version >/dev/null 2>&1; then
  LATEX_OK=true
elif xelatex --version >/dev/null 2>&1; then
  LATEX_OK=true
fi

if [ "$PANDOC_OK" = true ] && [ "$LATEX_OK" = true ]; then
  # Both available — stay silent
  exit 0
elif [ "$PANDOC_OK" = true ] && [ "$LATEX_OK" = false ]; then
  echo "[pandoc-plugin] $PANDOC_VER available. LaTeX NOT found — PDF generation will fail. Run /pandoc setup to install."
elif [ "$PANDOC_OK" = false ]; then
  echo "[pandoc-plugin] Pandoc is NOT installed. Run /pandoc setup to install Pandoc and LaTeX for document conversion."
fi

exit 0
