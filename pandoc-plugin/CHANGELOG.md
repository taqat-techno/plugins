# Changelog

## [2.2.0] - 2026-08-18

Marketplace-wide architecture upgrade. Skill discovery, invocation-mode metadata, and identity consistency were corrected across the marketplace; no skill, command, agent, hook, or MCP behaviour was removed.

**Restored an undiscovered skill.** `pandoc/SKILL.md` sat outside `skills/` and was never loaded. Moved to `skills/pandoc/` (git mv) and renamed to `pandoc-conversion` to clear a collision with `commands/pandoc.md`; `/pandoc` remains the user entry point (`user-invocable: false` on the skill).

