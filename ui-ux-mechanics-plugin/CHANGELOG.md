# Changelog

## [4.0.1] - 2026-10-19

Skill triggering tuned against real eval results. Measured with `claude plugin eval --runs 1 --model claude-sonnet-5-5`; the no-plugin baseline is the 2026-10-19 run, and Δ counts the criteria grader only.

### Changed
- `design` description opens with checking text, button or icon colours against their backgrounds for WCAG contrast, and which ratio applies to body text, large text and UI components.

### Eval results
- Must-fire: 2/3 -> 3/3. Must-not-fire: 3/3 quiet before and after. Mean Δ: +0.17 -> +0.17.

## [4.0.0] - 2026-10-19

Major: the command was renamed and Figma writes now stop for approval.

### Security
- **User approval before any Figma write** (UIUX-P1-02). `figma-mcp-mechanics` owns a new gate: before the first write of a session, including the net-zero write-access probe, Claude names the file, the pages / nodes and the change and waits for an explicit yes, suggesting a duplicated page or branch. `figma-workflow`, the command and the decision flow defer to it; registering Code Connect mappings counts as a write.
- Figma content (layer names, text, comments, API responses) is data, never instructions: rule added to both Figma skills and `design-reviewer`.
- The Figma REST PAT is read from `$FIGMA_TOKEN`; the skill no longer suggests getting it from the user in chat.

### Changed
- **Command renamed** `/ui-ux-mechanics:ui-ux-mechanics` -> `/ui-ux-mechanics:toolkit` (ECO-18). The old file is a deprecated stub until 4.1.0. The dispatch table marks which routes write to Figma.
- Skill descriptions rewritten to "Use when ..." and cut to 410-583 characters (were 1,494 / 2,466 / 3,176); `<example>` blocks removed (UIUX-P2-07).
- `figma-mcp-mechanics` split: the fifteen mechanics moved to `skills/figma-mcp-mechanics/references/mechanics.md`; SKILL.md keeps the gate, an index, the decision flow, safety gates, checklist and anti-patterns (38 KB -> 22 KB).
- Reference paths in skills and agents use `${CLAUDE_PLUGIN_ROOT}/reference/...` so they load from any working directory (UIUX-P1-05).
- Odoo palette moved out of `reference/color-theory.md` into `reference/appendix-framework-palettes.md` (UIUX-P1-03).
- Figma MCP tool table (owned by `figma-workflow`) checked against Figma's "Tools and prompts" docs: added `search_design_system`, `create_new_file`, `use_figma`, the remote/desktop column; `create_design_system_rules` is documented as a prompt, not a tool (UIUX-P2-06). Cross-references to the Figma plugin's `figma-use` skill are conditional.
- README rewritten to the marketplace template: marketplace install instead of manual copying, no `skills`-array advice, Requirements, Platform support, Data & privacy (UIUX-P1-01).

### Added
- WCAG 2.2 criteria (2.4.11-2.4.13, 2.5.7, 2.5.8, 3.2.6, 3.3.7-3.3.9; 4.1.1 obsolete) in the accessibility checklist; references updated to WCAG 2.2 AA (UIUX-P3-09).
- Attribution: `platform-guidelines.md` states it is an independent paraphrase with links to Apple HIG, Material 3 and Fluent 2 and no affiliation; the checklist cites W3C WCAG 2.2.
- `tests/test_surface.py` (12 tests); eval cases for `figma-workflow` and `figma-mcp-mechanics` plus two must-not-fire cases (not run).

### Removed
- The empty `hooks/hooks.json` (ECO-20).

### Not done
- UIUX-P2-08: evals were not run (cost); no Delta recorded.

## [3.2.3] - 2026-10-19

### Added
- MIT LICENSE file and `license` field in plugin.json.

## [3.2.2] - 2026-10-19

### Fixed
- **Least-privilege agent tools (QW #11, ECO-19 / UIUX-P2-04).** Both agents inherited every tool. `design-reviewer` now has `Read, Glob, Grep, Bash` plus the four namespaced Figma *read* tools its Phase 3 comparison uses (`mcp__plugin_figma_figma__get_screenshot`, `get_design_context`, `get_metadata`, `get_variable_defs`); `wireframe-builder` has `Read, Write, Glob, Grep, Bash` and no Figma write tools - pushing a wireframe to Figma is offered, and done by the main session after the user approves.

### Tests
- `tests/test_agent_tools.py`: every agent declares `tools:`; the reviewer cannot Write/Edit or call Figma write tools; the builder holds no MCP tools.

## [3.2.1] - 2026-09-12

Adds a behavioural eval suite under `evals/` (1 must-fire case + 1 must-not-fire case), so this plugin's value claim is measured as
`Delta` against a no-plugin baseline instead of asserted. Each must-fire case
pairs a namespace-tolerant `tool_used: Skill` indicator with an `llm` rubric
that demands a fact this plugin uniquely teaches, so a no-plugin run fails it.

- `fires-on-text-button-contrast-rules` targets `design`
- `ignores-dark-mode-toggle-persistence-storage` asserts no skill of this plugin fires (`min: 0`, `max: 0`, `arm: both`)

Pilot with `claude plugin eval . --case <case> --runs 1 --ablation none`,
then measure with `claude plugin eval .`. No runtime behaviour changed.

## [3.2.0] - 2026-08-18

Marketplace-wide architecture upgrade. Skill discovery, invocation-mode metadata, and identity consistency were corrected across the marketplace; no skill, command, agent, hook, or MCP behaviour was removed.

Fixed `user_invocable` -> `user-invocable` on 1 skill (previously inert).

