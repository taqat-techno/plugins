---
name: env-doctor
description: Routes a broken-local-environment symptom to the right diagnostic branch, runs read-only probes, classifies the failure, and proposes one safe next action without mutating config. Owns the diagnose-don't-mutate discipline for Claude Code and dev-environment problems. Activates when an MCP server will not load, a tool errors with a spawn / ENOENT / encoding failure, Claude Code login loops on a 401, an LSP or language server is missing, a Playwright or browser tool cannot find a browser, a plugin hook never fires or force-ends the turn, an agent spawns without its MCP tools, a long-running process vanishes with no crash artifact, a hand-edit to a running application's own config file is rejected as modified-since-read or is silently reverted, every tool from one server disappears at once after a file reorganization, or any "my local environment is broken" symptom surfaces.
version: 0.4.0
last_reviewed: 2026-07-23
owns:
  - the diagnose-don't-mutate discipline (probe before recommend, recommend before apply)
  - the symptom -> diagnostic-branch router
  - the seven-class failure taxonomy (spawn / auth / missing-binary / wrong-version / network-DNS / encoding / config-shadowing)
  - the Claude Code plugin & MCP gotchas (tool-name namespacing, plugin-cache staleness, valid hook events, Stop-hook `additionalContext` blocking the turn regardless of exit code, gate hooks that no-op on a missing dependency, settings.json strict-JSON, auto-invoke = SKILL+hooks not a command, wiki write-gate false positives, hook-process env isolation, local-source plugins that cannot update remotely)
  - the freshness rule for environment findings (re-probe a blocker before restating it)
  - the live-application config-ownership rule (a running app owns its own config files, so hand-editing one either fails or is clobbered; hand the user UI steps instead)
  - the ENVIRONMENT REPORT output contract
  - secret redaction by key-name and JWT/opaque shape
defers_to:
  - the eleven reference files for per-branch platform specifics (references/*.md)
  - env-probe-reporter agent (runs the probes and drafts the report)
  - env-doctor command (entry point and flag surface)
  - each consuming plugin for its own product internals (rag-plugin, odoo-plugin, qa-browser-plugin, ui-ux-mechanics-plugin)
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
- An IDE remote-dev session hangs at "Connecting" or drops mid-session even though the network path checks out.
- A long-running application vanishes with no crash dump, no OS error record, and no error in its own log.
- A hook never fires, or a `Stop` hook force-ends turns with "A hook blocked the turn from ending" even though it exits 0.
- `/doctor` runs the wrong skill, an interactive health TUI hangs in a non-interactive shell, or a managed cloud connector will not authorize.
- A file-sync daemon (Syncthing) shows conflict files, a folder stuck just under 100%, a delete that never completes, a peer whose pending count keeps growing without clearing, or a device that drops after an encryption change.
- A Windows shell mangles a command that is itself correct — a native exe gets stripped quotes or a BOM-prefixed pipe, an "excluded" directory is copied anyway, or Git-Bash breaks a `node`/`git` path argument.
- A Mermaid diagram renders as raw text in an IDE/editor, or an SVG-rendering script fails on `getBBox`.
- A daemon ignores the port or address in its own config, a config test fails on a missing runtime directory, or a background process survives a kill that reported no error.
- A write to a desktop application's own config file is rejected as "has been modified since read", or lands and is silently reverted the next time that application saves.
- Every tool from one server disappears at once immediately after a file move, reorganization, or migration.
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
| MCP not loading | server disconnected, startup timeout, "failed to connect", config present but inactive, or every tool from one server vanishing at once right after a file move | `references/mcp-not-loading.md` |
| Windows / WSL networking | `localhost` unreachable across the WSL boundary, DNS fails inside WSL, port not visible from the other side, an in-WSL bind fails `EADDRINUSE` while the Linux side shows the port free, a daemon listens on a port its own config never names, a background/pin process survives a `pkill` that reported no error | `references/windows-wsl.md` |
| Login / 401 | login loop, repeated 401, token rejected, auth silently fails | `references/login-auth.md` |
| LSP / Node CLI spawn | `ENOENT`, `command not found`, language server absent, Node CLI fails to spawn | `references/lsp-node-spawn.md` |
| Python encoding | mojibake, `UnicodeDecodeError`/`UnicodeEncodeError`, subprocess garbles non-ASCII | `references/python-encoding.md` |
| Playwright / browser-MCP | "browser not found", missing browser binary, headless launch fails | `references/playwright-browser.md` |
| IDE remote-dev backend | remote-dev "Connecting" hang or mid-session "No connection" while the wire probes pass; an IDE or backend process that vanishes with no crash dump and no heap error | `references/ide-remote-dev.md` |
| `/doctor` ambiguity / health TUI hangs | `/doctor` lands on the wrong skill, the interactive doctor TUI hangs non-interactively, managed-connector auth | `references/doctor-command-ambiguity.md` |
| Syncthing sync operations | `.sync-conflict-*` files, a folder parked <100% with 0 B pending, a delete that never completes, errors that persist after a rescan, a peer whose need count climbs for minutes without clearing, a device that drops after an encryption change (every folder to that peer offline at once) | `references/syncthing.md` |
| Windows shell / native-exe arg mangling | a native exe gets stripped quotes or a BOM-prefixed pipe, `Copy-Item -Exclude` copies an excluded dir, Git-Bash breaks a `node`/`git` path arg, `kubectl exec`/`port-forward` flakiness, `--parallel` tests pickle on Windows, a bare command name keeps resolving to the wrong binary after a `PATH` edit | `references/windows-powershell.md` |
| Mermaid / SVG not rendering | a Mermaid block shows as raw text in an IDE/editor preview, or an SVG-rasterizing script fails on `getBBox` | `references/ide-mermaid-rendering.md` |

When two branches seem to match, pick the one matching the *first* failure in the chain (a spawn failure that surfaces as MCP-not-loading is a spawn failure — start at the binary, then revisit MCP wiring). A remote-dev "connection" symptom whose network probes all pass belongs to the IDE-backend branch (a backend heap OOM), not the networking branch.

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

### Claude Code plugin & MCP gotchas

Diagnostic facts for "MCP not loading / hook never fires / agent missing its tools". Each maps to a failure class; check these before blaming the user's wiring.

| Symptom | Root cause | Read-only check | Classification |
|---|---|---|---|
| Agent spawns without its MCP tools (e.g. a devops agent comes up with only Read+Bash); a hook never fires | Plugin-provided MCP tools are namespaced `mcp__plugin_<plugin>_<server>__<tool>`, NOT bare `mcp__<server>__<tool>`. Hook matchers and agent `tools:` grants written in the bare form silently fail to resolve | Compare the tool names in the hook matcher / agent grant against the actual namespaced names emitted by the plugin | config-shadowing |
| Editing + pushing plugin source changes nothing in the running session; a stale version (e.g. 0.3.0/0.4.0) keeps running | Plugins and their hooks load from the CACHED copy under `~/.claude/plugins/` at SESSION START, not from the dev checkout | Inspect the installed/cached copy the session points at, not the dev tree; check its version | config-shadowing |
| A hook bound to `PostToolUseFailure` never fires | `PostToolUseFailure` is NOT a valid Claude Code hook event. (`PostToolUse` fires on success, not failures.) Valid events: `PreToolUse`, `PostToolUse`, `SessionStart`, `UserPromptSubmit`, `Stop`, `SubagentStop`, `PreCompact`, `Notification`, `SessionEnd` | Read the hook's event name and compare against the valid-events list | config-shadowing |
| A git write-gate hard-blocks a legitimate GitHub **wiki** push as "no access" | The gate parses `<owner>/<repo>.wiki.git` → `repo="<repo>.wiki"`, and `gh repo view <owner>/<repo>.wiki` returns 404 (a wiki is not a separate API repo); the naive gate misreads that 404 as "no access" | Strip the trailing `.wiki` and check the BASE repo's permission instead | auth failure (false positive) |
| A hand-edit to `.claude/settings.json` (a new permission, hook, or env var) is silently ignored and Claude Code falls back to defaults | `.claude/settings.json` is **strict JSON, not JSONC** — a single trailing comma before a `}`/`]` (or a `//` comment) makes the whole file fail to parse, so none of the settings load | Validate as strict JSON (e.g. `python -m json.tool < settings.json`); look for a trailing comma or a comment | config-shadowing |
| An "auto-run whenever X happens" behavior wired as a slash command never fires on its own | A slash **command** is user-invoked only. An **auto-invoked** capability is a directory `SKILL.md` (model-invoked by description match) **plus hooks** (deterministic, event-driven) — not a command | Check whether the behavior is a command (user-typed) vs a SKILL.md/hook (auto); confirm the hook event is a valid one | config-shadowing |
| A skill file exists under `.claude/skills/` but never appears in the available-skills list and is never auto-invoked | Only a **directory** skill registers: `.claude/skills/<name>/SKILL.md` with `name` + `description` frontmatter. A LOOSE `.md` sitting directly in `.claude/skills/` (e.g. `<topic>.md`) is a reference document — it does not register at all, so nothing can invoke it | List the skills directory and confirm the file is `<name>/SKILL.md`, not a bare `.md`; then confirm the name actually appears in this session's available-skills list rather than assuming it loaded | config-shadowing |
| A correctly-shaped directory skill registers but rarely fires on the situations it was written for | A `description` is **advisory** — the model matches against it, so a vague or purely descriptive one under-triggers. Determinism is not a description property: it comes from a **hook** (`SessionStart` for staleness/context, `Stop` for end-of-task work), which fires on the event regardless of what the model decides | Read the `description` for concrete trigger phrases and an explicit "invoke automatically when …"; if the behavior must be guaranteed rather than likely, check whether a hook backs it | expected state (not a fault) |
| An approval/opt-in env var set inline (`VAR=1 && <command>`) still fails the `PreToolUse` hook that reads it | A `PreToolUse` hook runs in **its own process, spawned before the command's shell**. It reads its own process environment, never the command text nor a variable exported inside that command — so an inline `export`/assignment can never reach it. Only the env of the Claude Code process itself (set before launch, or via a settings-file `env` block) is visible to the hook. This is by design: an agent cannot self-approve from a subprocess it spawns | Read the hook source for the exact variable name it checks, then check whether that variable is in the Claude Code process env — not whether the command sets it | config-shadowing |
| A plugin's per-plugin "Update now" control is disabled with "Local plugins cannot be updated remotely" | A plugin declared in a marketplace manifest with a **relative `source`** (e.g. `"./<dir>"`) is classified LOCAL — there is no remote to pull that one plugin from, so the control is disabled **by design**. It updates when its owning (remote, auto-updating) marketplace refreshes the subfolder, and the new version only runs after a session restart | Read the plugin's `source` in the marketplace manifest, then the owning marketplace's remote/auto-update setting and its cached version — not the per-plugin button | expected state (not a fault) |
| A `Stop`/`SubagentStop` hook documented as "never blocks, always exits 0" still force-ends the turn with "A hook blocked the turn from ending N consecutive times" | For `Stop`/`SubagentStop`, emitting `hookSpecificOutput.additionalContext` is precisely what *continues* the turn — the **exit code is irrelevant**. Each emission counts against the stop-hook block cap (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`, 9), then the turn is force-ended. The transcript records the hook as `hook_success`, which is why searching for a *failing* hook finds nothing. (`additionalContext` + `exit 0` is safe on `SessionStart`/`UserPromptSubmit`; it is NOT on `Stop`) | In the session transcript (`~/.claude/projects/<key>/*.jsonl`) search for `blocked the turn from ending`, then read the `stop_hook_summary` line immediately above it — it lists every Stop hook with its duration, separating the one that ran and emitted from the ones that no-op'd | config-shadowing |
| A gate hook reports success on every run but has never actually checked anything | The script `exit 0`s early when a dependency it needs is absent (a JSON/YAML CLI that only exists inside WSL, a linter not on the host `PATH`), silently converting a missing-binary failure into a passing gate. The tell is its recorded duration — a gate that genuinely runs a linter, a type-checker and a test suite cannot finish in ~100 ms | Read the hook script for guard clauses that `exit 0` on a missing dependency, check whether that dependency resolves in the hook's own process environment, and compare the recorded hook duration against what the real checks would cost | missing binary |

Fixes (propose, don't apply):

- **Namespacing mismatch (L1):** use namespace-agnostic matchers `mcp__(plugin_<plugin>_)?<server>__…` in hooks, and the full namespaced form `mcp__plugin_<plugin>_<server>__<tool>` in agent `tools:` grants.
- **Stale cache (L2):** to kill a misbehaving hook immediately, neutralize the exact cached script the session points at (make it `exit 0`) or restart the session; pushing the dev tree alone will not take effect mid-session.
- **Stop hook that emits context (L9):** read `stop_hook_active` from the stdin payload and `exit 0` while it is true — without it the hook re-fires identically on every retry, and a trigger the agent cannot clear by *talking* (e.g. "the working tree has uncommitted changes") is unsatisfiable by construction, so it always runs to the cap. Scope the trigger to real product code as well: an exclusion list covering only a docs path still fires on `.claude/agents/*.md` and `.claude/skills/**/SKILL.md`, so editing Claude's own configuration reads to the hook as "code changed, write a decision record".
- **A write that "won't go" usually has more than one gate on it:** enumerate **every** `PreToolUse` hook bound to the tool — an identity/access gate and a separate approval gate stack independently, and clearing one leaves the other blocking — *and* the remote's own answer. A genuine `403 … denied to <account>` comes from the remote, not a hook, so no hook change will clear it; the fix is to use the account that actually has access. Never dodge a gate by changing the working directory (or `git -C`) so its remote lookup cannot resolve the target — that blinds a security check instead of resolving it. Report the gate; let the user decide.

## Safety gates

- **Never** edit global git config (or any global config) as part of a diagnosis.
- **Never** print tokens, credentials, or env values — redact by key-name plus shape (e.g. `<JWT, 3 segments, redacted>`, `<opaque 40 chars, redacted>`).
- **Never** auto-mutate `~/.claude.json`, settings files, or MCP config without explicit per-change user confirmation.
- **Never** run a destructive repair (delete, reset, reinstall, kill) during diagnosis.
- **Never** assume an adapter value — probe for it read-only.
- **Never** chain multiple fixes at once — propose one, let the user apply, re-probe.
- **Never** restate a blocker from an earlier turn without re-probing it first. An environment finding is a **timestamped observation, not a standing fact** — a service restart, a VM restart, or a config reload between turns can clear it silently, and nothing announces that. Re-run the one-line probe before repeating "X is blocked", and *especially* before asking the user to run a privileged or elevated command; the cost is seconds, and the alternative is sending them after a workaround they no longer need.
- **Never** hand-edit a config file that a **running application owns**, even with the user's consent. A live desktop app rewrites its own config as its state changes, so the write either fails outright (`File has been modified since read` — the app rewrote it between your read and your write) or lands and is **clobbered** the next time the app saves. Consent does not change the race; only closing the app or letting the app make the change does. Give the user the in-app UI path (Settings -> …) instead, and say plainly that this is why. A *brand-new* config file the app does not yet hold open is safe to write, but needs an app reload before it applies — say so rather than reporting the change as live.
- **Never** infer a **version-sensitive schema or embed format** (a config block, a query/view definition, an embed syntax) from memory. These shift between releases of the host application, so a guessed shape ships a broken block into the user's working document while reading as authoritative. Verify the current syntax against official documentation for the installed version; if it cannot be verified, emit a clearly labelled placeholder that states the intended shape in plain text rather than a plausible-looking guess.
- **Never** echo the verbatim error if it embeds a secret — redact first.

## Validation checklist

- [ ] Symptom captured verbatim (with any secrets already redacted).
- [ ] Adapter values resolved or probed (`os_family`, `shell`, `wsl_involved`).
- [ ] Exactly one diagnostic branch selected via the router.
- [ ] Only read-only probes were run — zero writes, zero mutations.
- [ ] Each finding classified into exactly one of the seven classes.
- [ ] All secrets redacted by key-name + shape; no raw token anywhere.
- [ ] Exactly one safe next action proposed (not applied).
- [ ] Any blocker restated from an earlier turn was re-probed **this** turn before repeating it.
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
| Restate a blocker found in an earlier turn as still true | A restart, reload, or VM/service bounce between turns can clear it silently — the finding expired and nothing said so | Re-run the probe this turn before repeating it, above all before asking for an elevated command |
| Trust a hook's own header comment ("this hook never blocks — it only injects context and always exits 0") | A comment is documentation, not a contract, and it goes stale exactly where it matters; on `Stop` the blocking behavior comes from what the script *emits*, not from what it claims or what it returns | Read the script and its actual stdin/stdout contract, then confirm against the transcript's `stop_hook_summary` what really ran and for how long |
| Infer memory pressure when a process died leaving no crash artifact | No dump, no OS error record, no `hs_err`, no `OutOfMemoryError` means it was terminated from outside; the OS's "largest consumer" hint names a victim of system-wide pressure, not a culprit | Read the application's own telemetry first, then enumerate killers; instrument for the next occurrence instead of shrinking a heap on a guess |
| Treat "the app is running and listening" as proof its MCP bridge exists | The port proves the app side only; registration is a separate client-side fact, so the tools can be wholly absent | Confirm the expected `mcp__…` tools are callable in this session before relying on them |
| Take a quiet `pkill` / `taskkill` as proof the process is gone, then widen the pattern when it isn't | A kill only reports what it was permitted to signal — a differently-owned (root) process is skipped silently, and the pattern-based count that "proves" survivors can be matching the measuring shell itself. Widening or escalating the pattern is how unrelated processes die | Enumerate with owner and pid (`ps -eo pid,user,args`), verify with an exact-name match, and re-check the process list after any kill rather than reading the kill's exit code |
| Trust a daemon's config file to describe where it actually listens | A socket-activated or externally-supervised service inherits its listener from the supervisor, so the config's port/address directives are inert; the file can be edited, correct, and completely ignored | Read the live listener list (`ss -tlnp` / `Get-NetTCPConnection`) and the supervising unit, and treat the config as a claim to verify, not evidence |
| Conclude a capability "isn't working" without checking that it registered at all | A file in roughly the right place is not a loaded capability — wrong shape (loose `.md` vs `<name>/SKILL.md`), wrong event name, or a stale cached copy all present as "it just doesn't run", and the debugging then targets content that was never read | Validate the structure and confirm the capability appears in this session's available list before diagnosing its behavior |
| Hand-edit a running application's own config file (retrying, or forcing, after `modified since read`) | The app owns that file and rewrites it live — the write either loses the race or is clobbered at the app's next save, and the "fix" reads as applied while the app's own state says otherwise | Give the in-app UI path (Settings -> …); write only files the app does not hold open, and say a reload is required before they apply |
| Pause/resume — or force an override on — a sync folder because its pending count keeps climbing and minutes have passed | A count that grows and an elapsed clock are both non-diagnostic while a peer is still ingesting a bulk index change; intervening there restarts the exchange at best and resurrects the peer's deletions at worst | Compare the peer's consumed index cursor against the local one and wait while the gap closes; escalate only once the cursors are level and the list is still frozen with zero errors |
| Chase firewall, discovery, or overlay-network faults when a sync peer shows every shared folder disconnected | One folder's encryption-type mismatch aborts the whole cluster-config handshake, so all folders drop at once and the transport probes all pass — and the system *error* endpoint stays empty, because a refused link is a connection event | Read the connection log filtered on that peer's device id for the handshake reason before touching the network |
| Write a version-sensitive schema/embed block from memory because the shape "looks standard" | Embed and config schemas shift between host-app releases, so the guess ships a broken block into a document the user relies on — and it looks authoritative | Verify the syntax against official docs for the installed version, or emit a labelled placeholder stating the intended shape |
| Conclude "nothing references it any more" from a script that reported zero stale references | A verification pass can be broken in ways that only ever return zero — the tell is that it agrees with itself and with nothing else | Re-check with a differently shaped command before acting on a zero (see `references/mcp-not-loading.md`) |
| Re-implement these probes inside another plugin | Duplicated, drifting logic across plugins | Reference this skill for generic environment issues |

## Portability rationale

The router, taxonomy, safety gates, and report contract are OS- and shell-agnostic — they describe *how to reason*, not *what to type*. Every platform-specific command, path, and quirk lives in the eleven reference files, selected by the `os_family`/`shell`/`wsl_involved` adapter. Adding support for a new platform means adding probe variants to a reference file, not changing this skill.

Example (illustrative — not required): on `os_family=windows`, `shell=powershell`, a missing-binary probe might use `Get-Command`; on `linux`/`bash` it might use `command -v`. The skill picks the variant from the adapter; neither command is baked into the routing logic.

## Cross-references

- `references/mcp-not-loading.md` — MCP startup, wiring, and config-shadowing probes, plus the file-reorganization cause of a whole-server death (an import-time directory resolve against an empty directory a manifest-driven move dropped) and its three silent companions.
- `references/windows-wsl.md` — Windows/WSL networking, port, and DNS probes, including the in-WSL `EADDRINUSE` that is invisible from inside the distro because a Windows process owns the port; the socket-activated `sshd` whose `sshd_config` `Port`/`ListenAddress` are inert and whose `sshd -t` fails on a `/run/sshd` that only appears at first service start; and the owner / `pgrep -f` self-match traps that make a background pin look unkillable.
- `references/login-auth.md` — login-loop and 401 auth-flow probes.
- `references/lsp-node-spawn.md` — LSP and Node-CLI spawn / missing-binary / version probes.
- `references/python-encoding.md` — subprocess encoding and locale probes.
- `references/playwright-browser.md` — browser-binary discovery and headless-launch probes.
- `references/ide-remote-dev.md` — remote-dev backend heap-OOM diagnosis (the "connection" symptom that is really a JVM OOM), and its mirror image: a process that vanishes leaving no crash artifact was terminated from outside, so read the application's own telemetry before blaming memory.
- `references/doctor-command-ambiguity.md` — `/doctor` routing ambiguity, non-interactive CLI health checks vs. the hanging TUI, managed-connector auth, and permissions-allowlist hygiene.
- `references/syncthing.md` — Syncthing dev-folder sync operations: conflict resolution (diff by content first; receive-only + revert as the only "prefer remote"), the venv/`node_modules` delete-deadlock (`(?d)` ignore), `.stignore` locality, cached error lists (pause/resume, then judge on the status counters), the `sequence` vs `remoteSequence` gap that separates a busy peer from a wedged one, the encryption-mismatch device drop (read `/rest/system/log`, not `/rest/system/error`), and REST-API (`/rest/db/status`, `/rest/db/file`, `/rest/db/remoteneed`) diagnosis.
- `references/windows-powershell.md` — Windows shell & native-exe argument traps: PowerShell 5.1 quote-strip / pipe BOM, `Copy-Item -Exclude`, `kubectl exec`/`port-forward` (the `NameError`/`U+FEFF` signatures, the quote-free-or-file payload, and TCP-listen polling with a deterministic teardown), `head`/`tail` SIGPIPE + exit-0 mask, Git-Bash path mangling, `--parallel` test pickling, and binary resolution (Machine-before-User `PATH` shadowing, the stale in-process `PATH`, and the `REG_EXPAND_SZ`→`REG_SZ` downgrade).
- `references/ide-mermaid-rendering.md` — a missing Mermaid renderer in an IDE/editor (JetBrains Marketplace plugin / VS Code extension / native web rendering) and jsdom's missing SVG layout (`getBBox`) → headless Chrome. Cross-references docs-wiki `wiki-mermaid` for authoring.
- `env-probe-reporter` (agent) — runs the read-only probes and drafts the ENVIRONMENT REPORT.
- `env-doctor` (command) — user entry point; surfaces flags and invokes this skill.
- Consuming plugins (`rag-plugin`, `odoo-plugin`, `qa-browser-plugin`, `ui-ux-mechanics-plugin`) should REFERENCE this skill for generic environment issues instead of duplicating its probes or taxonomy.
