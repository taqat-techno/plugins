---
description: Check for Pandoc and LaTeX and show (or, with consent, run) the install commands
argument-hint: '[--skip-latex] [--install] [--enable-autoinstall]'
---

# /pandoc:setup

1. Run the installer in check-only mode first. It installs nothing; it reports
   what is present and prints the install commands for what is missing:
   - **Windows**: `powershell -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}/skills/pandoc/scripts/setup.ps1" -PrintOnly`
   - **Linux/macOS**: `bash "${CLAUDE_PLUGIN_ROOT}/skills/pandoc/scripts/setup.sh" --print-only`

   Add `-SkipLatex` / `--skip-latex` when `$ARGUMENTS` contains `--skip-latex`.
2. If something is missing, show the printed commands and their sizes, and
   recommend that the user runs them in their own terminal: the package
   managers ask for licence acceptance and `sudo` passwords, which cannot be
   answered from Claude's shell. Never add `-y`, `--noconfirm` or winget
   `--accept-*` flags yourself.
3. Only if the user explicitly asks you to run the installation here, re-run
   with `-Install` / `--install`. Report a failure as a failure (the scripts exit
   non-zero when an install does not complete).
4. MiKTeX (Windows) can download missing LaTeX packages on demand. Enabling it
   changes persistent MiKTeX settings for the user and lets MiKTeX fetch packages
   during later conversions. Describe that and ask; only on a clear yes, re-run
   with `-Install -EnableAutoInstall` (it also pre-installs about 30 common
   packages).
5. Finish with `pandoc --version` and, for PDF, `pdflatex --version` or
   `xelatex --version`.
