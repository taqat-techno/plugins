# RAG Plugin — UserPromptSubmit Hook Failure Investigation

**Date:** 2026-06-29 · **Investigator pass:** read-only, no fixes implemented · **Repo:** `taqat-techno/plugins` → `plugins/rag-plugin`

---

## Executive summary

The teammate's root-cause chain is **mechanically sound and the vulnerable pattern is present in the CURRENT version (v0.15.0), unchanged since v0.3.0 — it is NOT a v0.13.2-only / stale issue.** Four of the five causal links are **proven by repo code + the official hook spec + empirical tests**; only the trigger ("Cowork on headless Windows fails to expand `${CLAUDE_PLUGIN_ROOT}`") is a **host behavior that cannot be proven from the plugin repo** and needs Cowork runtime logs.

The dangerous coincidence is real and documented:

- Python's exit code for *"can't open the script file"* is **2** (proven empirically, every variant).
- Claude Code's hook spec defines **exit `2` = "Blocking error"** for hooks, including `UserPromptSubmit` (proven from the official `plugin-dev/hook-development` spec).
- The plugin registers **two `UserPromptSubmit` hooks** invoked as the raw `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/<script>.py` (proven from `hooks.json`).
- The scripts' own fail-safe (`sys.exit(0)` on every error) **cannot run if the script file never loads** — confirmed: the failure happens at the `python3-can't-find-file` layer, before any script code executes.

**Verdict: PARTIALLY VALID** (strong) — a genuine, present, prompt-blocking design vulnerability whose *occurrence in Cowork specifically* is unconfirmed without logs. **A real enhancement is recommended regardless**, because the failure is possible, the blast radius is catastrophic (every prompt silently blocked → "spinner / no response / no model call"), and the mitigation is cheap and pure-upside. The old `P-012` issue was the wrong, generic signal and **should be replaced** with a precise hook-blocking issue, plus a new report-engine detector.

---

## Current repo / version inspected

| Item | Value |
|---|---|
| Repo | `taqat-techno/plugins` (origin), branch `main` |
| Plugin | `rag-plugin`, **manifest version `0.15.0`** (`.claude-plugin/plugin.json`) |
| Old report's version | `v0.13.2` (2026-06-02) |
| Hook wiring file | `hooks/hooks.json` |
| Hook scripts | `hooks/prompt_retrieval_reminder.py` (v0.4.0), `hooks/project_focus_inject.py` (v0.10.0), `hooks/lock_conflict_check.py` |
| Cowork detection in plugin | **None** (`grep` for `Cowork` / `CLAUDE_CODE_IS_COWORK` → 0 hits) |
| Official hook spec consulted | `claude-plugins-official/plugins/plugin-dev/skills/hook-development/SKILL.md` (read-only reference clone) |

**Stale-vs-current:** `git log -p -- rag-plugin/hooks/hooks.json` shows the `command` strings have **only ever** been the three `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/<script>.py` variants — introduced in commit `e87b4d0` (v0.3.0) and **never changed**. The pattern in v0.13.2 is byte-identical to v0.15.0. **→ NOT a stale, already-fixed issue.**

---

## Old report claims being validated

| # | Old-report / teammate claim | Status |
|---|---|---|
| 1 | Bundled hooks: `hooks.json`, `lock_conflict_check.py`, `project_focus_inject.py`, `prompt_retrieval_reminder.py` | ✅ **Confirmed** — all present, current |
| 2 | `hooks.json` registers **two** `UserPromptSubmit` hooks running `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/…` | ✅ **Confirmed** (`hooks.json:21`, `:30`) |
| 3 | In Cowork headless Windows, `${CLAUDE_PLUGIN_ROOT}` was **not expanded** | ❓ **NOT PROVEN from repo** — host behavior, needs Cowork logs |
| 4 | Python then receives a literal/bad path and **exits code 2** | ✅ **Proven empirically** (exit 2 in every variant) |
| 5 | Claude Code/Cowork treats hook exit `2` as **blocking**, cancelling the prompt | ✅ **Proven from official spec** (`SKILL.md:294–298`) |
| 6 | This explains "spinner / no response / no model call" | ✅ **Consistent** — blocking before model request is exactly this symptom |
| 7 | Old generated issue only reported `P-012 — MCP error phrases`, too weak | ✅ **Confirmed** — `P-012` is the `mcp-error` session-scan signal, unrelated to hook-fatal failure; engine has **no** detector for the real failure |

---

## Current hook inventory

From `hooks/hooks.json` (description line 2 asserts *"None of these hooks block or deny"* — true only **after** a script loads):

| Event | matcher | command (`hooks.json` line) | Script exit behavior once loaded |
|---|---|---|---|
| `PreToolUse` | `Bash` | `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/lock_conflict_check.py` (**:10**) | always `exit 0` (`emit_silent_pass`/`emit_ask` → `sys.exit(0)`, lines 119, 143) |
| `UserPromptSubmit` | `*` | `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/prompt_retrieval_reminder.py` (**:21**) | always `exit 0` (`silent_pass`/`inject_reminder` → `sys.exit(0)`) |
| `UserPromptSubmit` | `*` | `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/project_focus_inject.py` (**:30**) | always `exit 0` (`_silent` → `sys.exit(0)`, lines 57–58, 244) |

The two `UserPromptSubmit` hooks are the dangerous ones: a non-zero exit there is consumed by the prompt-processing path. (The `PreToolUse` one fires only on Bash tool calls and its exit-2 semantics affect a tool call, not the prompt itself — separate, lesser blast radius.)

---

## `UserPromptSubmit` analysis

**Invocation form is raw and interpreter-specific:** `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/<script>.py`.

Two independent fragilities:

1. **`${CLAUDE_PLUGIN_ROOT}` resolution.** The official spec (`SKILL.md:327, 331`) says `$CLAUDE_PLUGIN_ROOT` is available in all command hooks and to *"Always use `${CLAUDE_PLUGIN_ROOT}` … for portability"* — i.e., the plugin uses the **documented, correct** mechanism. Claude Code expands it. **If a host (e.g. Cowork desktop/headless) does not**, the shell receives a literal `${CLAUDE_PLUGIN_ROOT}`:
   - On a **POSIX shell** (`sh`/bash) with the env var unset → expands to empty → `python3 /hooks/<script>.py` → file not found.
   - On **cmd.exe** (which uses `%VAR%`, not `${VAR}`) → passes literal `${CLAUDE_PLUGIN_ROOT}` to `python3` → file not found.
   - Either way → **`python3` exits 2** (see proof below).

2. **`python3` vs `python`.** On Windows, `python3` is not guaranteed; if absent, the command fails to *spawn* → exit `127` → **"Other = Non-blocking error"** (safe — prompt proceeds, just no injection). The **dangerous** case requires `python3` to *resolve* **and** the path to be bad → exit 2 → blocking. On the test machine `python3` **does** resolve (`…\WindowsApps\python3`, Python 3.12.10), so the dangerous exit-2 branch is reachable on real Windows.

**The symptom fingerprint matches the dangerous branch, not the safe one.** "Spinner / no response / no model call" = the prompt was *blocked before the model request* = a blocking (exit 2) hook result. A missing-`python3` (127) failure would surface as a visible non-blocking hook error and the prompt would still run. So the reported symptom specifically implicates the exit-2 path.

---

## Cross-platform / Cowork risk analysis

| Host | Shell | `${CLAUDE_PLUGIN_ROOT}` outcome | `python3` | Likely hook result |
|---|---|---|---|---|
| Claude Code CLI (any OS) | sh / cmd, var expanded by Claude Code | resolved | present | ✅ script runs, exit 0 |
| Git Bash on Windows, var **unset** | bash | expands to **empty** → bad path | present | ⛔ **exit 2 → blocking** |
| cmd.exe, var **not expanded** | cmd | **literal** `${…}` → bad path | present | ⛔ **exit 2 → blocking** |
| Windows, `python3` absent | any | (moot) | **missing** | ⚠️ exit 127 → non-blocking (no injection) |
| Cowork desktop/headless Windows | unknown | **claimed not expanded** (unproven) | likely present | ⛔ if claim holds → **exit 2 → blocking** |
| WSL / Linux / macOS, var expanded | sh | resolved | `python3` usual | ✅ runs, exit 0 |

**Unsafe cross-platform assumptions in the current plugin:**
- Assumes the host always expands `${CLAUDE_PLUGIN_ROOT}` in hook `command` strings. The maintainers **explicitly flagged this exact dependency** as a known (judged "unlikely") risk: `docs/decisions.md:434` — *"The `${CLAUDE_PLUGIN_ROOT}` variable stops being expanded by the Claude Code plugin loader … Unlikely — the variable is documented and used by multiple official plugins."*
- Assumes `python3` is the right interpreter name on every host.
- Assumes a hook failure is non-blocking. **It is not** — exit 2 is blocking by spec, and a missing-file error is exactly exit 2.
- No remote/headless gating. The documented env var for remote context is **`CLAUDE_CODE_REMOTE`** (`SKILL.md:329`); there is **no** documented `CLAUDE_CODE_IS_COWORK` in the official spec (the teammate's suggested gate variable is unverified).

---

## Script exit-code / fail-safe analysis

**Runtime fail-safe (once the script loads): excellent.** Empirically every script exits `0` under malformed/empty input:

```
retrieval-reminder empty-stdin exit=0      retrieval-reminder malformed exit=0
project-focus      empty-stdin exit=0      lock-conflict       malformed exit=0
```

This matches the code: `silent_pass`/`inject_reminder` (`prompt_retrieval_reminder.py`), `_silent` (`project_focus_inject.py:57`), `emit_silent_pass`/`emit_ask` (`lock_conflict_check.py:119,143`) all `sys.exit(0)`, and each `main()` wraps everything in try/except → silent-pass. Service-down, missing config, unresolved focus, malformed payload, missing state file → **all exit 0**.

**The gap the teammate identified is correct and decisive:** *a script can be fail-safe only after it starts.* If `python3` cannot open the file (unresolved `${CLAUDE_PLUGIN_ROOT}`, wrong path), **none of that exit-0 logic ever runs** — Python aborts at file-open with exit **2**. Empirical proof, all three variants:

```
${CLAUDE_PLUGIN_ROOT} UNSET  (bash → empty path)   → exit=2
LITERAL ${CLAUDE_PLUGIN_ROOT} (simulates cmd.exe)  → exit=2
plainly missing path                               → exit=2
```

stderr of the literal case (the log signature a detector should match):

```
…python3.exe: can't open file '…\rag-plugin\${CLAUDE_PLUGIN_ROOT}\hooks\prompt_retrieval_reminder.py': [Errno 2] No such file or directory
```

So: **script-level fail-safe is necessary but NOT sufficient.** The failure mode lives one layer above the script, in the command-invocation layer, which is currently unguarded.

---

## Evidence table (files + lines)

| Claim | Evidence | Location |
|---|---|---|
| Two `UserPromptSubmit` hooks, raw `python3 ${CLAUDE_PLUGIN_ROOT}` | repo | `hooks/hooks.json:21`, `:30` (PreToolUse at `:10`) |
| Pattern unchanged since v0.3.0 (not stale) | git | `git log -p -- rag-plugin/hooks/hooks.json` → only `python3 ${CLAUDE_PLUGIN_ROOT}/…` variants; introduced `e87b4d0` |
| Plugin uses documented `${CLAUDE_PLUGIN_ROOT}` mechanism | official spec | `hook-development/SKILL.md:327, 331, 336` |
| **Exit 2 = Blocking error** (incl. UserPromptSubmit) | official spec | `hook-development/SKILL.md:294–298`; UserPromptSubmit "block prompts" `:219`, field `user_prompt` `:317` |
| Python exits **2** when it can't open the script | empirical | unset-var, literal-var, missing-path → all `exit=2` |
| Literal `${CLAUDE_PLUGIN_ROOT}` appears in stderr on failure | empirical | `can't open file '…${CLAUDE_PLUGIN_ROOT}…': [Errno 2]` |
| `python3` resolves on real Windows (exit-2 path reachable) | empirical | `…\WindowsApps\python3`, Python 3.12.10 |
| Scripts fail-safe (exit 0) **only once loaded** | empirical + code | empty/malformed → exit 0; `project_focus_inject.py:57`, `lock_conflict_check.py:119,143` |
| Maintainers knew of the `${CLAUDE_PLUGIN_ROOT}`-non-expansion risk, judged it "unlikely" | repo | `docs/decisions.md:434` |
| Report engine has **no** hook-fatal detector | repo | `rag_report.py` `_SIGNAL_PATTERNS:660–686` (no `${CLAUDE_PLUGIN_ROOT}` / exit-2 / hook-block pattern) |
| Engine blind via hook log when hook never runs | repo | `rag_report.py:560 inspect_hook_log` reads `hook-decisions.log`, only written when the hook executes |
| No Cowork detection in plugin | repo | `grep Cowork\|CLAUDE_CODE_IS_COWORK` → 0 hits |
| Cowork actually fails to expand the var | **MISSING** | needs Cowork runtime logs (literal `${CLAUDE_PLUGIN_ROOT}` + Python exit 2 + prompt cancelled) |

---

## Verdict — PARTIALLY VALID (strong; design vulnerability present in current code)

Per-link breakdown:

- **Link 1 — two UserPromptSubmit hooks, raw `${CLAUDE_PLUGIN_ROOT}`/`python3`:** **VALID / PROVEN** (current code, unchanged since v0.3.0).
- **Link 2 — Cowork doesn't expand `${CLAUDE_PLUGIN_ROOT}`:** **NOT PROVEN** from repo (host behavior; needs Cowork logs).
- **Link 3 — Python exits 2 on bad path:** **VALID / PROVEN** (empirical, all variants; `python3` resolves on Windows).
- **Link 4 — exit 2 blocks UserPromptSubmit:** **VALID / PROVEN** (official spec 294–298).
- **Link 5 — script fail-safe can't help (it never runs):** **VALID / PROVEN** (empirical + code).

**Therefore:** the failure is a real, present, *prompt-blocking* design vulnerability in the current plugin; the only unconfirmed element is whether Cowork is the host that triggers it. Calling it merely "stale/v0.13.2-only" would be **wrong** — the pattern is identical today. Calling it fully "VALID/confirmed-in-Cowork" would **overstate** — the Cowork trigger isn't in the repo evidence. Hence **PARTIALLY VALID**: *VALID mechanism + present fragility, trigger NOT PROVEN without logs.*

**Is an enhancement needed? YES** — independent of confirming the Cowork trigger. Severity is critical (silent total prompt blocking), the failure is reachable on real Windows, the maintainers already flagged the dependency, and the fix is small and risk-free.

---

## Recommended GitHub issue (replace the generic `P-012`)

**Target repo:** `taqat-techno/plugins` (plugin behavior). *Also* consider a companion issue to the Claude Code / Cowork product team for the host-side non-expansion (link 2), since the plugin uses the documented mechanism correctly.

**Title:**
`UserPromptSubmit hooks can block the prompt (Python exit 2) if ${CLAUDE_PLUGIN_ROOT} is unexpanded — make advisory hooks fail-open`

**Body (skeleton):**
> **Severity:** High/Critical (silent prompt blocking — "spinner / no response / no model call").
> **Affected:** all versions with the UserPromptSubmit hooks (≥ v0.3.0, **including current v0.15.0**) — `hooks/hooks.json:21,30`.
>
> **Root cause.** The two `UserPromptSubmit` hooks run `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/<script>.py`. If the host does not expand `${CLAUDE_PLUGIN_ROOT}` (reported on Cowork headless Windows) **and** `python3` resolves (Microsoft Store alias / launcher), Python cannot open the script and exits **2**. Per the Claude Code hook spec, **exit 2 = blocking error**, so the prompt is cancelled before the model request. The scripts' own `sys.exit(0)` fail-safe cannot run because the file never loads.
>
> **Evidence.** Exit-2 reproduced for unset/empty/literal `${CLAUDE_PLUGIN_ROOT}` and missing paths; stderr shows literal `${CLAUDE_PLUGIN_ROOT}` + `[Errno 2]`; `python3` present on Windows; pattern unchanged since v0.3.0; maintainers flagged the dependency in `docs/decisions.md:434`.
>
> **Fix.** Make the advisory hooks fail-open by construction (any non-zero → 0), and/or route through a resilient launcher; switch interpreter resolution to be portable. See "Recommended fix strategy."
>
> **Not the same as old `P-012`** (`mcp-error phrases`), which is a session-text signal unrelated to this hook-fatal failure. Recommend closing/superseding the P-012-only report.

**Replace the old `github-plugins-issue.md`? YES.** `P-012` (the `mcp-error` session scan) does not describe — and could not have detected — this failure. A precise hook-blocking issue should supersede it.

---

## Recommended fix strategy (NO code changes in this pass)

1. **Make every advisory hook command fail-open (primary, minimal, cross-platform).** Append a guard so any failure yields exit 0, e.g. conceptually `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/<script>.py" || exit 0` (the `||` short-circuit works in both POSIX `sh` and `cmd.exe`; verify the host shell). This directly neutralizes the exit-2→block path *regardless* of whether `${CLAUDE_PLUGIN_ROOT}` expands, because these hooks are injectors that must never block. **Safe by design** — the scripts never legitimately emit exit 2.
2. **Resilient launcher (defense-in-depth).** A tiny committed launcher that (a) resolves the plugin root from the `CLAUDE_PLUGIN_ROOT` *environment variable* with a fallback to its own `__file__` dirname, (b) resolves an interpreter (`python3` → `python` → `py`), (c) **exits 0 on any resolution/spawn failure**, then execs the real script. Pair with guard #1 so the launcher's own invocation is also fail-open.
3. **Portable interpreter.** Stop hard-coding `python3`; let the launcher pick `python3`/`python`/`py`. (Secondary — the missing-`python3` case is already non-blocking, but inconsistent UX.)
4. **Host bug (root cause of link 2).** If Cowork logs confirm non-expansion, file it to the Claude Code/Cowork product — the plugin follows the documented spec. Optionally gate injection hooks in remote/headless context using the **documented** `CLAUDE_CODE_REMOTE` (not the unverified `CLAUDE_CODE_IS_COWORK`).
5. **Keep the runtime fail-safes** — they remain correct and necessary; they just need the invocation-layer guard above them.

**Do NOT** weaken any existing safety: keep the lock-conflict `ask`, the operational-intent gate, and the redaction posture.

---

## Tests that should be added

A new **hook-invocation smoke test** asserting *the command never exits 2 under any failure*:

- ✅ `${CLAUDE_PLUGIN_ROOT}` set correctly → script runs, exit 0.
- ✅ `${CLAUDE_PLUGIN_ROOT}` **unset / empty** → exit 0 (with fix).
- ✅ **literal** `${CLAUDE_PLUGIN_ROOT}` (cmd.exe simulation) → exit 0 (with fix).
- ✅ script file **missing** → exit 0 (with fix).
- ✅ `python3` **missing** simulation → non-blocking (exit ≠ 2).
- ✅ **malformed** hook payload → exit 0.
- ✅ **service down** → exit 0.
- ✅ Windows path with spaces / backslashes → exit 0.
- ✅ run via **`sh`** *and* **`cmd`** (where available) to prove the `|| exit 0` guard works cross-shell.
- ✅ **structural lint** (extend `validate_plugin.py` / a CI check): assert every `command` in `hooks.json` is fail-open (carries a guard) — prevents regression.

**Report-engine detection to add** (`rag_report.py`):

- New `_SIGNAL_PATTERNS` entries: literal `\$\{CLAUDE_PLUGIN_ROOT\}`, `can't open file .*hooks[/\\].*\.py`, `\[Errno 2\] No such file or directory.*hooks`, `UserPromptSubmit.*hook.*(exit|failed|block)`, hook `exit code 2`.
- A new finding (e.g. **`P-013` — "fatal/blocking UserPromptSubmit hook failure"**, HIGH/CRITICAL, routed to `taqat-techno/plugins`) — the finding that *should* have fired instead of `P-012`.
- Note the **blind spot**: `inspect_hook_log` can't see a hook that never ran (no log line). Detection must come from session/stderr transcripts — add the signals above to the session scanner.

---

## Open questions / evidence still needed

1. **Cowork runtime logs (the one missing link).** Need: the hook stderr showing literal `${CLAUDE_PLUGIN_ROOT}` + `[Errno 2]`, the recorded **exit code 2**, and evidence the **prompt was cancelled before the model request**. This converts the verdict from PARTIALLY VALID → VALID for Cowork specifically.
2. **Does Cowork run hook commands via `cmd.exe`, `sh`, or PowerShell?** Determines whether `${CLAUDE_PLUGIN_ROOT}` becomes empty vs literal — and whether a `|| exit 0` guard is honored (PowerShell 5.1 lacks `||`).
3. **Does Cowork set `CLAUDE_PLUGIN_ROOT` as an env var even when it doesn't substitute the `${…}` literal?** If yes, a launcher reading `os.environ` fixes it cleanly.
4. **Is there a real `CLAUDE_CODE_IS_COWORK` env var?** Not in the official spec; `CLAUDE_CODE_REMOTE` is the documented remote-context flag.
5. **Confirm the exit-2 blocking behavior in Cowork** (vs. CLI), since Cowork is a distinct product surface — the spec quoted is Claude Code's.

---

*Investigation only — no source files were modified except creating this report. No commit, no push, no PR.*
