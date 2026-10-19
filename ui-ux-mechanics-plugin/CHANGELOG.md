# Changelog

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

