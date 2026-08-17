# Changelog

## [3.1.0] - 2026-08-18

Marketplace-wide architecture upgrade. Skill discovery, invocation-mode metadata, and identity consistency were corrected across the marketplace; no skill, command, agent, hook, or MCP behaviour was removed.

**Restored an undiscovered skill.** `ntfy/SKILL.md` sat outside `skills/` and was never loaded. Moved to `skills/ntfy/` (git mv). Renamed to `ntfy-messaging` because relocation collided with `commands/ntfy.md` on `ntfy-notifications:ntfy`; `/ntfy` remains the user entry point and the skill is now the model-loaded knowledge layer (`user-invocable: false`).

