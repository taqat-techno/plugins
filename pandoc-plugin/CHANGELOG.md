# Changelog

## [3.0.0] - 2026-10-19

Major: `/pandoc` is split into verb commands, and the installers no longer
install anything unattended.

### Added
- `/pandoc:convert` (bare: usage guide), `/pandoc:setup`, `/pandoc:status`,
  `/pandoc:formats`.
- Installer flags: `-PrintOnly`/`--print-only`, `-Install`/`--install`, and
  `-EnableAutoInstall` (Windows) for the MiKTeX AutoInstall setting.
- Skill safety rules (PDC-P1-04): ask before overwriting an existing output
  (one question per batch), `--sandbox` for untrusted documents, Lua filters and
  templates treated as code, raw LaTeX/HTML passthrough warning, and document
  text treated as data, never instructions.
- `tests/test_setup_scripts.py`: 14 offline tests. Both installers run against
  recording fakes for sudo/apt-get/brew/winget, so nothing is installed: syntax
  and parse checks, no auto-accept flags, check-only mode on a non-terminal
  stdin, `--quiet` completing, and failed installs exiting 1 (PDC-P2-09).

### Changed
- `/pandoc` is a deprecated stub routing to the new commands; removed in the
  next minor version.
- Skill description rewritten to 1,024 characters or fewer, starting "Use
  when"; `<example>` blocks removed; `last_reviewed` under `metadata`.
- README restructured to the marketplace template, with sizes, platform
  support, data & privacy and third-party licences (PDC-P2-07).
- `setup.sh` suggests BasicTeX (about 100 MB) on macOS and names MacTeX's
  size (about 5 GB) (PDC-P2-08).

### Fixed
- `setup.ps1` reported a failed `winget` install as success: native exit codes
  do not throw in Windows PowerShell 5.1. It now checks `$LASTEXITCODE`,
  re-resolves `pandoc.exe` / `pdflatex.exe` afterwards and exits 1 on failure;
  winget output no longer leaks into the function's return value (PDC-P1-05).
- `setup.sh --quiet` aborted at the first log line under `set -e`; the log
  helpers now always return 0 (PDC-P1-05).
- `setup.ps1` no longer redefines the built-in `Write-Warning` / `Write-Error`.

### Security
- No `--accept-package-agreements` / `--accept-source-agreements`, `-y` or
  `--noconfirm`: the user accepts licence terms and `sudo` prompts. Run from a
  non-terminal (Claude's shell) the installers only print commands (PDC-P1-03,
  PDC-P2-08).
- MiKTeX `[MPM]AutoInstall=1` is no longer described as mandatory before every
  PDF; `reference/format_guide.md` and the skill require asking first
  (PDC-P1-03).

### Removed
- `hooks/`: the empty `hooks.json` and the unregistered `session-check.sh` and
  `pandoc-context.sh` (PDC-P1-02).

### Not done
- Template presets (PDC-P3-10, effort M) are deferred.

## [2.2.3] - 2026-10-19

### Added
- MIT LICENSE file and `license` field in plugin.json.

## [2.2.2] - 2026-10-19

**`/pandoc setup` can find its installers again** (PDC-P0-01). Since 2.2.0 moved
the skill to `skills/pandoc/`, `SKILL.md` still pointed at
`${CLAUDE_PLUGIN_ROOT}/pandoc/scripts/setup.ps1|setup.sh`, a path that no longer
exists. It now uses `${CLAUDE_PLUGIN_ROOT}/skills/pandoc/scripts/...`, and
`commands/pandoc.md` gains a `setup` section that names the same installers
(it previously gave no path at all).

README no longer claims hooks that do not run: `hooks/hooks.json` is empty, so
the "Auto-detection Hooks" feature, the hooks table and the "Customizing hooks"
section were removed and the two unregistered scripts are labelled as such. The
plugin-structure tree now matches the files (`skills/pandoc/`, `tests/`), and the
footer version is current.

- Added `tests/test_paths.py` (offline, stdlib `unittest`): every
  `${CLAUDE_PLUGIN_ROOT}/...` reference in the plugin's markdown resolves to a
  file, and both the command and the skill reference both installers. Run with
  `python -m unittest discover -s tests -v`.

## [2.2.1] - 2026-09-12

Adds a behavioural eval suite under `evals/` (1 must-fire case + 1 must-not-fire case), so this plugin's value claim is measured as
`Delta` against a no-plugin baseline instead of asserted. Each must-fire case
pairs a namespace-tolerant `tool_used: Skill` indicator with an `llm` rubric
that demands a fact this plugin uniquely teaches, so a no-plugin run fails it.

- `fires-on-arabic-pdf-garbled-text` targets `pandoc`
- `ignores-scanned-pdf-ocr-extraction` asserts no skill of this plugin fires (`min: 0`, `max: 0`, `arm: both`)

Pilot with `claude plugin eval . --case <case> --runs 1 --ablation none`,
then measure with `claude plugin eval .`. No runtime behaviour changed.

## [2.2.0] - 2026-08-18

Marketplace-wide architecture upgrade. Skill discovery, invocation-mode metadata, and identity consistency were corrected across the marketplace; no skill, command, agent, hook, or MCP behaviour was removed.

**Restored an undiscovered skill.** `pandoc/SKILL.md` sat outside `skills/` and was never loaded. Moved to `skills/pandoc/` (git mv) and renamed to `pandoc-conversion` to clear a collision with `commands/pandoc.md`; `/pandoc` remains the user entry point (`user-invocable: false` on the skill).

