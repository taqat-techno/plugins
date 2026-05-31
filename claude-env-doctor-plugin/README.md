# claude-env-doctor

Diagnose your local Claude Code and development environment — read-only, no mutation. It tells you what is wrong and how to fix it; it never changes your system for you.

## What it does

`claude-env-doctor` inspects the local machine where Claude Code runs and reports problems in plain language, ranked by likelihood. It **diagnoses, it does not mutate**: every probe is read-only, and any fix is presented as a suggestion you choose to apply yourself.

It covers the environment failure modes that block day-to-day work:

- **MCP wiring** — MCP servers that fail to start, are misconfigured, point at a dead command, or never connect; stdio/SSE/HTTP transport mismatches; `${CLAUDE_PLUGIN_ROOT}` and path resolution issues.
- **Windows / WSL networking** — loopback and `localhost` resolution across the Windows/WSL boundary, port-forwarding gaps, firewall-blocked local ports, and services bound to the wrong interface.
- **Login / 401 / auth** — expired or missing credentials, repeated 401 responses, token-refresh loops, and proxy/TLS interception that breaks authenticated calls.
- **LSP / Node spawn** — language servers or Node-based tooling that fail to spawn, crash on launch, or exit with non-zero codes; missing runtimes and `PATH` gaps.
- **Python encoding** — `UnicodeDecodeError`/`UnicodeEncodeError`, mismatched locale/`PYTHONIOENCODING`, and console code-page problems (common on Windows) that corrupt tool output.
- **Playwright / browser MCP** — missing browser binaries, headless-launch failures, sandbox/permission blocks, and browser-MCP connections that never become ready.

The output is a triage report: symptom, most likely cause, and a suggested next step. Nothing is executed against your machine without your say-so.

## Commands

### `/env-doctor`

Runs the full local environment diagnosis. **Works with no arguments** — a bare `/env-doctor` performs a complete read-only sweep and prints a ranked report.

Optional flags narrow the scope to one area (for example, focus only on MCP wiring, or only on networking) when you already know roughly where the problem is. Flags are shortcuts, never required.

## Skills

### `env-doctor`

The routing skill that owns the diagnostic workflow. It decides which probes to run, interprets their output, and assembles the report. It pulls detailed, OS-specific guidance from six bundled reference documents:

1. **`references/mcp-wiring.md`** — MCP server start-up, transport, and configuration diagnosis.
2. **`references/windows-wsl-networking.md`** — loopback, port-forwarding, and firewall checks across the Windows/WSL boundary.
3. **`references/login-401-auth.md`** — credential, token-refresh, 401, and proxy/TLS diagnosis.
4. **`references/lsp-node-spawn.md`** — language-server and Node process spawn failures, runtime and `PATH` checks.
5. **`references/python-encoding.md`** — locale, code-page, and `PYTHONIOENCODING` issues that corrupt output.
6. **`references/playwright-browser-mcp.md`** — browser-binary, headless-launch, and browser-MCP readiness diagnosis.

Reference docs hold the heavy, platform-specific detail so the skill body stays a thin router. Add new failure modes by extending a reference doc first, then wiring it into the skill.

## Agent

### `env-probe-reporter` (read-only)

A focused subagent that gathers environment signals and produces the diagnostic report without making any changes. It is constrained to inspection — reading config, checking process and port state, inspecting versions and logs — and returns findings as structured text. It never writes files, never restarts services, and never edits configuration. Use it to keep probe-and-report work off the main context window.

## Hook

A **non-blocking `SessionStart` advisory** hook. When a session begins, it runs a fast, lightweight check and, if it spots an obvious environment problem, prints a one-line advisory pointing you at `/env-doctor`. It is advisory only: it never blocks the session, never prompts, and never mutates anything. If nothing looks wrong, it stays silent.

## Scope / non-goals

This plugin diagnoses the **local development environment** and nothing else.

It is **not**:

- a server-operations or production-incident tool,
- a deployment runbook or release-automation tool,
- a DevOps, CI/CD, or GitHub-workflow tool.

Server ops, deployment, and workflow logic belong to other, purpose-built plugins. `claude-env-doctor` stays in its lane: figuring out why the tooling on *this* machine is misbehaving.

## Canonical home

This plugin is the **canonical home for generic local-environment diagnosis**. Other plugins that hit a generic environment problem — an MCP server that will not connect, a 401 they cannot explain, a Node or Python tool that will not spawn — should reference `claude-env-doctor` rather than re-implementing their own ad-hoc checks. Keeping the diagnostic logic in one place means every plugin benefits from the same probes and the same reference docs.

## Portability

`claude-env-doctor` is built to run for **any user, in any workspace, on any major OS** (Windows, macOS, Linux, and WSL). Its behavior never depends on a specific user, project, company, path, repo, or credential.

- Cross-OS by default: the skill and agent detect the platform at run time and select the appropriate probes.
- OS-specific detail lives in the reference docs (notably the Windows/WSL networking and Python-encoding guides), so the core routing stays platform-neutral.
- No absolute user paths, no hard-coded hosts, no project assumptions are baked into behavior.

### Adapter inputs

The diagnosis adapts to the environment it finds, using inputs such as:

- **OS and shell** — Windows / macOS / Linux / WSL, and the active shell.
- **Runtime presence and versions** — Node, Python, and other interpreters/tools discoverable on `PATH`.
- **MCP configuration** — declared MCP servers, their transports, and connection state.
- **Network context** — relevant local ports and loopback reachability for services under test.
- **Locale / encoding** — active locale, code page, and encoding-related environment variables.
- **Browser tooling state** — presence and readiness of Playwright/browser-MCP components.

All inputs are read for diagnosis only. The plugin never prints secrets, tokens, or environment-variable values, and never writes to your configuration.

---

> Example (illustrative — not required): a session starts, the hook notices an MCP server stuck in a failed state, and prints `Environment check: 1 MCP server failed to connect — run /env-doctor`. Running `/env-doctor` then reports the likely cause (a stdio command not found on `PATH`) and the suggested fix, which you apply yourself.
