---
description: Diagnose a local Claude Code / dev-environment problem (MCP, WSL, login, LSP, encoding, browser).
argument-hint: "[symptom]"
---

# Environment Doctor

You are the entry point for diagnosing local Claude Code and dev-environment problems. Your job is thin: hand control to the `env-doctor` skill and follow its symptom-to-branch router. All real diagnostic logic lives in the skill, not here.

## How to run

1. Load the `env-doctor` skill now.
2. If `$ARGUMENTS` (a free-text symptom) is present, pass it to the skill so it can route directly to the matching branch (for example: MCP, WSL, login/auth, LSP, encoding, browser).
3. If `$ARGUMENTS` is empty, run a **general environment triage**: walk the skill's default checklist across all branches and report what looks healthy vs. what looks broken. A bare invocation MUST do something useful on its own — never block waiting for a symptom.

The optional symptom only makes routing faster. It is never required.

## Operating rules (the skill enforces these — restate, do not re-implement)

- **Read-only by default.** Run only inspection probes (version checks, status queries, config reads, log tails). Do not install, edit, restart, or delete anything as part of triage.
- **Propose, never auto-mutate.** When you find a likely cause, present the safe fix as a concrete, copy-pasteable suggestion and let the user decide. Do not apply fixes unless the user explicitly asks.
- **Never print secrets.** Do not echo tokens, API keys, passwords, credentials, or raw environment-variable values. Report presence/absence and shape (e.g. "set / not set", "looks malformed") — never the value itself.
- **Stay generic.** Diagnose whatever environment you find. Behavior must not depend on any specific project, company, path, or URL.

## Output

Give the user a short, structured result: what was checked, what is healthy, the most likely cause of the reported symptom, and the proposed safe next step. Keep it focused on the symptom when one was given; keep it a broad sweep when none was.

> Example (illustrative — not required): a user runs `/env-doctor mcp server won't connect`; you route to the MCP branch, confirm the server is configured but its process is not listening, and propose the restart command for them to run — without printing any token from its config.
