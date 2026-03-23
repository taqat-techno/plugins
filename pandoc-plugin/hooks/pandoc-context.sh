#!/usr/bin/env bash
# PreToolUse/Bash hook: Inject pandoc best-practice context
# Reads tool input JSON on stdin, checks if command involves pandoc.
# Stdout becomes additionalContext. Exit 0 always (non-blocking).

INPUT=$(cat)

# Extract the command field from JSON input
COMMAND=$(echo "$INPUT" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"command"[[:space:]]*:[[:space:]]*"//' | sed 's/"$//')

# Only act on pandoc commands
if ! echo "$COMMAND" | grep -qi 'pandoc'; then
  exit 0
fi

TIPS=""

# PDF: suggest xelatex for Unicode/RTL, warn about LaTeX requirement
if echo "$COMMAND" | grep -qiE '\.pdf|--pdf-engine'; then
  if ! pdflatex --version >/dev/null 2>&1 && ! xelatex --version >/dev/null 2>&1; then
    TIPS="${TIPS}[pandoc] PDF requires LaTeX. Run /pandoc setup first.\n"
  fi
  if echo "$COMMAND" | grep -qiE 'arab|rtl|amiri|cairo' && ! echo "$COMMAND" | grep -qi 'xelatex'; then
    TIPS="${TIPS}[pandoc] Arabic/RTL content detected — use --pdf-engine=xelatex with -V dir=rtl.\n"
  fi
fi

# EPUB: suggest cover image if missing
if echo "$COMMAND" | grep -qiE '\.epub' && ! echo "$COMMAND" | grep -qi 'epub-cover'; then
  TIPS="${TIPS}[pandoc] EPUB tip: Add --epub-cover-image for a professional eBook (recommended: 1600x2400px).\n"
fi

# HTML: suggest standalone flag if missing
if echo "$COMMAND" | grep -qiE '\.html' && ! echo "$COMMAND" | grep -qE '\-s |--standalone'; then
  TIPS="${TIPS}[pandoc] HTML tip: Add -s (--standalone) for a complete document with <head> and <body>.\n"
fi

# Output tips if any
if [ -n "$TIPS" ]; then
  echo -e "$TIPS"
fi

exit 0
