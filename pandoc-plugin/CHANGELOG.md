# Changelog

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

