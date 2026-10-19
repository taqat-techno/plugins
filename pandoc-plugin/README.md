# Pandoc Plugin for Claude Code

A document conversion plugin powered by [Pandoc](https://pandoc.org/). Convert between 50+ input formats and 60+ output formats with intelligent automation.

---

## Quick Start

```
1. /pandoc setup          (one-time installation)
2. /pandoc status         (verify everything works)
3. Just describe what you need:
   - "Convert report.md to PDF with TOC"
   - "Make reveal.js slides from outline.md"
   - "Create an EPUB from these chapters"
```

---

## Commands

All functionality lives under a single command:

| Command | Description |
|---------|-------------|
| `/pandoc setup` | Install and configure Pandoc + LaTeX |
| `/pandoc status` | Check installation and available engines |
| `/pandoc convert` | Convert files between any supported formats |
| `/pandoc formats` | List all supported input/output formats |
| `/pandoc help` | Show usage guide and examples |

## Natural Language

You don't need to memorize commands. Just describe what you want and the skill handles it:

- "Convert my thesis to PDF with a table of contents and bibliography"
- "Turn these markdown files into a Word document"
- "Make a reveal.js presentation from slides.md with the moon theme"
- "Create an EPUB from ch1.md, ch2.md, and ch3.md with a cover image"
- "Convert this HTML page to clean Markdown"

The skill detects the input format, chooses the right output engine, and applies best-practice options automatically.

## Features

- **Universal Conversion** -- Markdown, Word, HTML, PDF, LaTeX, EPUB, and many more
- **Professional PDFs** -- Academic, report, and book presets with LaTeX
- **Presentations** -- reveal.js (HTML), Beamer (PDF), or PowerPoint
- **eBook Publishing** -- EPUB with covers, metadata, and custom styling
- **Smart Defaults** -- Automatic format detection and best-practice options
- **Batch Processing** -- Convert multiple files in one go

## Hooks

No hooks are registered: `hooks/hooks.json` is empty, so nothing runs automatically at session start or before Bash commands. The two scripts in `hooks/` (`session-check.sh`, `pandoc-context.sh`) are not wired up and do not run. Use `/pandoc status` to check the installation.

## Plugin Structure

```
pandoc-plugin/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest
├── commands/
│   └── pandoc.md                # Unified /pandoc command
├── hooks/
│   ├── hooks.json               # Empty: no hooks registered
│   ├── session-check.sh         # Not registered (does not run)
│   └── pandoc-context.sh        # Not registered (does not run)
├── skills/
│   └── pandoc/
│       ├── SKILL.md             # pandoc-conversion skill
│       └── scripts/
│           ├── setup.ps1        # Windows installer (used by /pandoc setup)
│           └── setup.sh         # Linux/macOS installer (used by /pandoc setup)
├── reference/
│   └── format_guide.md          # Format-specific best practices
├── test/                        # Sample inputs (md, rst, tex)
├── tests/
│   └── test_paths.py            # Offline check: referenced plugin paths exist
├── CHANGELOG.md
└── README.md
```

## Extending the Plugin

### Adding a custom template
Place template files (LaTeX, HTML, DOCX reference docs) in a `templates/` directory and reference them in your pandoc commands with `--template` or `--reference-doc`.

### Adding format-specific guidance
Extend `reference/format_guide.md` with best practices for your specific use cases (corporate templates, language-specific PDF settings, etc.).

## Troubleshooting

**Pandoc not found** -- Run `/pandoc setup` or install manually from https://pandoc.org/installing.html. Restart your terminal afterward.

**PDF generation fails** -- LaTeX is required for PDF output. Run `/pandoc setup` to install MiKTeX (Windows), MacTeX (macOS), or TeX Live (Linux).

**Images missing in output** -- Use relative paths in source documents. When converting from Word, the skill automatically extracts media.

**Encoding issues** -- Save source files as UTF-8. The skill handles smart quotes and Unicode automatically.

## License

MIT License

## Credits

- **Pandoc**: John MacFarlane -- https://pandoc.org/
- **Plugin**: TAQAT Techno -- https://www.taqatechno.com/

---

*Pandoc Plugin v2.2.2 -- Universal Document Conversion for Claude Code*
