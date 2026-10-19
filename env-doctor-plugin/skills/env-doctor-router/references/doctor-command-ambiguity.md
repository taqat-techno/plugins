# `/doctor` ambiguity and non-interactive health checks

Two traps collide here: the word **"doctor"** is overloaded, and the tools people reach for to
check Claude Code health are **interactive TUIs that hang** when an agent runs them in a
non-interactive shell. This reference disambiguates the routes and names the non-interactive,
read-only checks to use instead. It also carries a short note on permissions-allowlist hygiene.

Generic throughout — no specific project, path, or credential. Never print secrets, tokens, or
environment values while diagnosing.

## The literal `/doctor` may not mean "check Claude Code"

Typing `/doctor` can resolve to a **React-doctor-style skill** — a code-quality/diagnostics skill
that expects a React project (lint, a11y, bundle, architecture). If you invoke it outside a React
codebase, it has nothing to scan and the result is confusing: it is doing its job on the wrong
target, not failing to check your environment.

Disambiguate by intent before acting:

| The user actually wants… | Route to |
|---|---|
| "Is my React code healthy?" (lint/a11y/bundle) | the React-doctor skill, **inside a React project** |
| "Is my Claude Code install / MCP wiring healthy?" | the CLI checks below — **not** the interactive doctor TUI |
| A vague "run doctor" with no React project present | clarify intent; default to the Claude Code CLI checks |

If a `/doctor` invocation lands on the React skill and there is no React project, that is the
ambiguity — re-route to the CLI health checks rather than treating the empty React scan as a fault.

## For Claude Code health, use the CLI — not the interactive doctor TUI

The interactive doctor / health screen is a **TUI**: it expects a terminal it can draw to and read
keystrokes from. Run from an agent's non-interactive shell, it **hangs** (waiting on input that
never comes) or renders garbage. Never launch the interactive doctor TUI as a probe.

Use the non-interactive, scriptable commands instead — they print and exit:

```
# List configured MCP servers and their state (read-only, exits cleanly)
claude mcp list

# Confirm the installed CLI version (capability/feature gating, mismatch checks)
claude --version
```

`claude mcp list` is the right health probe for MCP wiring (it is Rung 1 of
`references/mcp-not-loading.md`); `claude --version` is the right probe for the "wrong CLI version"
classification. Both are read-only and safe to run unattended. If a check *needs* the interactive
TUI, treat that as a limitation to report — ask the user to run it in their own terminal — rather
than spawning a screen that will hang the session.

> Why this matters for an agent: a hung TUI ties up the shell and produces no usable output, so
> the diagnosis stalls with nothing to classify. The CLI equivalents give you the same facts as
> plain text.

## Managed cloud connectors authorize only through the interactive MCP menu

A specific exception to "prefer the CLI": **managed / cloud MCP connectors** (hosted connectors
that require an OAuth-style authorization step) generally **cannot be authorized from a flag or a
one-shot command** — the authorization happens through the **interactive MCP menu** inside Claude
Code, which opens the consent/login flow. An agent cannot complete that handshake non-interactively.

Diagnosis implication:

- If a managed connector shows as present-but-unauthorized in `claude mcp list`, do **not** try to
  script the auth. The probe is read-only; the fix is a human step.

Safe action: report that the connector needs authorization via the **interactive MCP menu**, and
hand that step to the user. Do not attempt to inject a token into config to bypass the menu, and
never echo any token involved.

## Permissions-allowlist hygiene

When proposing additions to a permissions allowlist (so the user is prompted less), keep it lean
and conservative:

- **Exclude basics that are already auto-allowed.** Read-only inspection many setups permit by
  default (listing files, reading a file, simple status reads) does not need an allowlist entry.
  Adding them is noise that bloats the list and obscures the entries that matter.
- **Never wildcard a shell or interpreter.** Do not allowlist a blanket `bash`, `sh`,
  `powershell`, `python`, `node`, or an `npx`/`uvx`-style runner with a wildcard argument — a
  wildcard on an interpreter grants *arbitrary code execution*, defeating the point of the
  allowlist. Allowlist the **specific, narrowly-scoped commands** actually needed instead.
- **Scope to exact subcommands.** Prefer `<tool> <specific subcommand>` over `<tool> *`. Narrow
  entries are auditable and safe; broad entries quietly re-open everything.

Safe action: propose the minimal set of specific entries and let the user apply them. This is a
settings change the user makes — never auto-write an allowlist, and never widen it to a shell
wildcard to make a prompt go away.

## Cross-references

- `references/mcp-not-loading.md` — `claude mcp list` is Rung 1 there; this doc explains *why* to
  prefer it over the interactive TUI in a non-interactive shell.
- `references/login-auth.md` — managed-connector authorization is an auth flow; the no-token,
  user-applies discipline is shared.
