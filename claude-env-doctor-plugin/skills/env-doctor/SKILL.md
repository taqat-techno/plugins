---
name: env-doctor
description: Routes a broken-local-environment symptom to the right diagnostic branch, runs read-only probes, classifies the failure, and proposes one safe next action without mutating config. Owns the diagnose-don't-mutate discipline for Claude Code and dev-environment problems. Activates when an MCP server will not load, a tool errors with a spawn / ENOENT / encoding failure, Claude Code login loops on a 401, an LSP or language server is missing, a Playwright or browser tool cannot find a browser, or any "my local environment is broken" symptom surfaces.
version: 0.1.0
last_reviewed: 2026-05-31
owns:
  - the diagnose-don't-mutate discipline (probe before recommend, recommend before apply)
  - the symptom -> diagnostic-branch router
  - the seven-class failure taxonomy (spawn / auth / missing-binary / wrong-version / network-DNS / encoding / config-shadowing)
  - the ENVIRONMENT REPORT output contract
  - secret redaction by key-name and JWT/opaque shape
defers_to:
  - the six reference files for per-branch platform specifics (references/*.md)
  - env-probe-reporter agent (runs the probes and drafts the report)
  - env-doctor command (entry point and flag surface)
  - each consuming plugin for its own product internals (rag-plugin, odoo-plugin, qa-browser-plugin, paper-plugin)
user_invocable: false
---

# env-doctor

## Purpose

A broken local environment has many shapes (MCP won't load, a tool spawn-fails, login loops, an LSP is absent, a browser can't be found) but one correct response: probe read-only, classify the failure, report, then propose a single explicit fix. This skill encodes that discipline so no diagnostic session ever blindly edits config, prints a secret, or runs a destructive repair.

## When to use

Activate when any of these symptoms appear:

- An MCP server is configured but will not load, shows as disconnected, or times out on startup.
- A tool errors with a spawn failure, `ENOENT`, `command not found`, or a non-zero exit on launch.
- Claude Code login loops, repeatedly returns a 401, or auth silently fails.
- An LSP or language server is missing, or a Node CLI invoked by a tool cannot be spawned.
- Output is mojibake, a `UnicodeDecodeError`/`UnicodeEncodeError` appears, or a subprocess garbles non-ASCII text.
- A Playwright or browser-MCP tool reports it cannot find or launch a browser.
- Any vague "my local environment is broken" report where the failing branch is not yet known.

Do NOT activate for application logic bugs, test assertions, or product-internal issues — those belong to the owning project, not the environment layer.

## Inputs (adapter)

Every project-specific value is a named adapter input. Nothing below is hardcoded.

1. **`os_family`** — `windows` | `macos` | `linux`. Selects path, process, and shell conventions.
2. **`shell`** — `powershell` | `bash` | `zsh` | other. Selects probe command syntax.
3. **`wsl_involved`** — `true` | `false`. Whether the failing component crosses the Windows/WSL boundary.
4. **`configured_mcp_servers`** — the list of MCP server names the user has wired up (names only; never their secret values).
5. **`failing_command_or_tool`** — the exact command or tool name that errors, plus the verbatim error text (pre-redaction).

If an adapter value is unknown, the first probe is to discover it read-only (e.g. detect OS/shell), never to assume it.

## Read-only investigation steps

1. **Capture the symptom verbatim.** Record the exact error text and the failing command/tool name before touching anything.
2. **Resolve the adapter.** Determine `os_family`, `shell`, and `wsl_involved` by inspection if not supplied.
3. **Route to one branch** using the table below. Pick the single best-matching symptom class.
4. **Open the matching reference file** and run only the read-only probes it lists (existence checks, `--version`, config reads, connectivity tests). Never a write.
5. **Classify each finding** into exactly one of the seven failure classes.
6. **Assemble the ENVIRONMENT REPORT** (see Output format). Redact every secret.
7. **Propose one safe next action** — the smallest explicit change — and stop. The user applies it.

## Decision framework

### Symptom -> diagnostic-branch router

| Symptom class | Trigger signs | Reference file |
|---|---|---|
| MCP not loading | server disconnected, startup timeout, "failed to connect", config present but inactive | `references/mcp-not-loading.md` |
| Windows / WSL networking | `localhost` unreachable across the WSL boundary, DNS fails inside WSL, port not visible from the other side | `references/windows-wsl.md` |
| Login / 401 | login loop, repeated 401, token rejected, auth silently fails | `references/login-auth.md` |
| LSP / Node CLI spawn | `ENOENT`, `command not found`, language server absent, Node CLI fails to spawn | `references/lsp-node-spawn.md` |
| Python encoding | mojibake, `UnicodeDecodeError`/`UnicodeEncodeError`, subprocess garbles non-ASCII | `references/python-encoding.md` |
| Playwright / browser-MCP | "browser not found", missing browser binary, headless launch fails | `references/playwright-browser.md` |

When two branches seem to match, pick the one matching the *first* failure in the chain (a spawn failure that surfaces as MCP-not-loading is a spawn failure — start at the binary, then revisit MCP wiring).

### Failure taxonomy (classify every finding)

| Class | Means | Typical safe next action |
|---|---|---|
| spawn failure | the binary launches but exits non-zero, or the runtime cannot start it | re-check the launch command/args, working dir, runtime version |
| auth failure | credentials rejected or absent | re-auth via the official flow; never paste a token into config |
| missing binary | the executable is not on `PATH` or not installed | install or add to `PATH` (explicit path, user-confirmed) |
| wrong version | binary present but incompatible version | pin/upgrade to the required version |
| network / DNS | connectivity, port, or name resolution fails | test reachability; fix the boundary (see windows-wsl) |
| encoding | byte<->text decoding mismatch | set the encoding env/locale for the subprocess |
| config-shadowing | a higher-precedence config overrides the expected one | identify which file wins; edit the right one only after confirmation |

```
symptom --> [router] --> branch --> read-only probes --> [classify: 1 of 7]
                                                              |
                                            ENVIRONMENT REPORT + ONE safe action
                                                              |
                                                   user applies (or declines)
```

## Safety gates

- **Never** edit global git config (or any global config) as part of a diagnosis.
- **Never** print tokens, credentials, or env values — redact by key-name plus shape (e.g. `<JWT, 3 segments, redacted>`, `<opaque 40 chars, redacted>`).
- **Never** auto-mutate `~/.claude.json`, settings files, or MCP config without explicit per-change user confirmation.
- **Never** run a destructive repair (delete, reset, reinstall, kill) during diagnosis.
- **Never** assume an adapter value — probe for it read-only.
- **Never** chain multiple fixes at once — propose one, let the user apply, re-probe.
- **Never** echo the verbatim error if it embeds a secret — redact first.

## Validation checklist

- [ ] Symptom captured verbatim (with any secrets already redacted).
- [ ] Adapter values resolved or probed (`os_family`, `shell`, `wsl_involved`).
- [ ] Exactly one diagnostic branch selected via the router.
- [ ] Only read-only probes were run — zero writes, zero mutations.
- [ ] Each finding classified into exactly one of the seven classes.
- [ ] All secrets redacted by key-name + shape; no raw token anywhere.
- [ ] Exactly one safe next action proposed (not applied).
- [ ] "Not tested or blocked" lists anything that could not be probed.

## Output format

The skill emits exactly one block:

```
ENVIRONMENT REPORT
  Symptom:            <verbatim failing command/tool + error, secrets redacted>
  Detected environment:
                      os_family=<...> shell=<...> wsl_involved=<true|false>
                      configured_mcp_servers=[<names only>]
  Probes run:
                      - <probe 1> -> <read-only result>
                      - <probe 2> -> <read-only result>
  Classification:     <one of: spawn failure | auth failure | missing binary |
                       wrong version | network/DNS | encoding | config-shadowing>
  Safe next action:   <single explicit change for the USER to apply>
  Not tested or blocked:
                      - <anything that could not be probed read-only, and why>
  (no secrets included)
```

## Anti-patterns

| Anti-pattern | Why it is wrong | Correct |
|---|---|---|
| Edit `~/.claude.json` to "just fix it" | Mutates state before the cause is proven; may corrupt working config | Probe, report, propose one change for the user to apply |
| Print the offending token to "show the problem" | Leaks a secret into the transcript/logs | Redact by key-name + shape |
| Assume the OS or shell | A wrong assumption sends every later probe astray | Probe `os_family`/`shell` read-only first |
| Reinstall the MCP server / browser as the first step | Destructive and slow; hides the real cause | Classify first; reinstall only if "missing binary" is proven and confirmed |
| Apply three fixes at once | Cannot tell which one worked; compounds risk | One fix, re-probe, repeat |
| Treat MCP-not-loading as always a config problem | Often a downstream spawn or missing-binary failure | Follow the chain to the first failure, then classify |
| Re-implement these probes inside another plugin | Duplicated, drifting logic across plugins | Reference this skill for generic environment issues |

## Portability rationale

The router, taxonomy, safety gates, and report contract are OS- and shell-agnostic — they describe *how to reason*, not *what to type*. Every platform-specific command, path, and quirk lives in the six reference files, selected by the `os_family`/`shell`/`wsl_involved` adapter. Adding support for a new platform means adding probe variants to a reference file, not changing this skill.

Example (illustrative — not required): on `os_family=windows`, `shell=powershell`, a missing-binary probe might use `Get-Command`; on `linux`/`bash` it might use `command -v`. The skill picks the variant from the adapter; neither command is baked into the routing logic.

## Cross-references

- `references/mcp-not-loading.md` — MCP startup, wiring, and config-shadowing probes.
- `references/windows-wsl.md` — Windows/WSL networking, port, and DNS probes.
- `references/login-auth.md` — login-loop and 401 auth-flow probes.
- `references/lsp-node-spawn.md` — LSP and Node-CLI spawn / missing-binary / version probes.
- `references/python-encoding.md` — subprocess encoding and locale probes.
- `references/playwright-browser.md` — browser-binary discovery and headless-launch probes.
- `env-probe-reporter` (agent) — runs the read-only probes and drafts the ENVIRONMENT REPORT.
- `env-doctor` (command) — user entry point; surfaces flags and invokes this skill.
- Consuming plugins (`rag-plugin`, `odoo-plugin`, `qa-browser-plugin`, `paper-plugin`) should REFERENCE this skill for generic environment issues instead of duplicating its probes or taxonomy.
