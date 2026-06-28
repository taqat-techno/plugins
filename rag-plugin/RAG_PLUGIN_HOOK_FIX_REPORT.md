# RAG Plugin — Hook-Blocking Vulnerability Fix Report

**Date:** 2026-06-29 · **Pass:** implementation (fix applied, no commit/push/release) · **Repo:** `taqat-techno/plugins` → `plugins/rag-plugin` · **Version:** 0.15.0 → **0.15.1**

Fixes the vulnerability diagnosed in `RAG_PLUGIN_HOOK_INVESTIGATION_REPORT.md` (verdict: PARTIALLY VALID — strong).

---

## Executive summary

The two advisory `UserPromptSubmit` hooks could **silently cancel the user's
prompt**. They were invoked as the raw `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/<x>.py`;
when the host fails to expand `${CLAUDE_PLUGIN_ROOT}` (reported on Cowork/headless
Windows), the var is unset, or the script is missing, **Python exits 2**, which
the Claude Code hook spec treats as a **blocking** error on `UserPromptSubmit` —
the prompt is dropped before the model request. The scripts' own `sys.exit(0)`
fail-safe never runs because the file never loads.

The fix moves the fail-open guarantee **above** the script. `hooks.json` now runs
an inline `python3 -c` bootstrap (no script-file argument → the "can't open
file → exit 2" branch is structurally impossible) that locates and runs a new
`hooks/hook_launcher.py`, which runs the real target in-process and returns exit
`0` in every failure case. A report-engine detector **`P-013`** now flags any
advisory hook that is not fail-open and **supersedes the generic `P-012`**.

**Acceptance criteria — all met:**

| Criterion | Status |
|---|---|
| Raw `UserPromptSubmit` commands can no longer return blocking exit 2 on path failure | ✅ structurally impossible (`-c`, no script-file arg) + launcher normalizes all exits |
| Advisory hook failures return 0 | ✅ 16 launcher tests, every failure scenario → exit 0 |
| Normal hook success path still works | ✅ target runs in-process; stdout (`additionalContext`) passes through (tested) |
| New tests cover the dangerous failure mode | ✅ 16 launcher tests + 14 report-engine tests |
| Report engine detects the old risky pattern as P-013 | ✅ static High / runtime Critical; end-to-end verified |
| No unrelated behavior changes | ✅ target scripts, thresholds, lock hook untouched |
| Delivered to `main` (user-directed `/goal`) | ✅ committed + pushed to `taqat-techno/plugins` `main` (v0.15.1) |

---

## Files changed

**New (5):**

| File | Purpose |
|---|---|
| `hooks/hook_launcher.py` | Resilient launcher: advisory (normalize to 0) + guarded (pass exit code through, fail open on infra failure) modes. |
| `hooks/test_hook_launcher.py` | 24 failure-mode tests (exit 0 / never 2; guarded exit-2 passthrough). |
| `rules/hook-failopen.md` | The binding contract (advisory hooks must be fail-open). |
| `docs/issues/P-013-advisory-hook-blocking.md` | Curated GitHub issue draft (supersedes P-012). |
| `RAG_PLUGIN_HOOK_FIX_REPORT.md` | This report. |

**Modified (6):**

| File | Change |
|---|---|
| `hooks/hooks.json` | All three commands → inline `-c` bootstrap + `python3\|\|python\|\|py -3` interpreter chain. Lock hook routed in guarded mode (was raw). Description updated. |
| `scripts/rag_report.py` | `analyze_advisory_hook_safety()`, `unsafe_advisory_hooks` field, `hook-path-fatal` signal, **P-013** finding, fail-open status line, `hook_launcher.py` in expected-hooks set. |
| `scripts/test_rag_report.py` | +14 tests (analyzer, P-013, signal precision, real-plugin regression guard). |
| `docs/decisions.md` | **D-031** (advisory hooks must be fail-open by construction). |
| `CHANGELOG.md` | `[0.15.1]` entry. |
| `.claude-plugin/plugin.json` | `version` 0.15.0 → 0.15.1. |

The prior `RAG_PLUGIN_HOOK_INVESTIGATION_REPORT.md` is also present (untracked, from the investigation pass).

---

## Exact old risk

`hooks/hooks.json` (pre-fix), two entries — byte-identical since v0.3.0 (`e87b4d0`):

```
python3 ${CLAUDE_PLUGIN_ROOT}/hooks/prompt_retrieval_reminder.py
python3 ${CLAUDE_PLUGIN_ROOT}/hooks/project_focus_inject.py
```

Failure chain (4/5 links proven by repo + official spec + empirical tests; only
the Cowork-specific non-expansion *trigger* needs runtime logs):

1. Host does not expand `${CLAUDE_PLUGIN_ROOT}` (or var unset / script missing).
2. `python3` receives a non-existent path → **can't open file → exit 2**.
3. Spec: **exit 2 = "Blocking error"** for `UserPromptSubmit`.
4. Prompt cancelled before the model request ("spinner / no response").
5. Script `sys.exit(0)` fail-safe never runs — the file never loaded.

---

## Fix strategy

1. **Remove the fragile dependency from the executable path.** The `python3`
   command line no longer names a script file. It runs `python3 -c "<bootstrap>"`.
   Because `-c` carries no script-file argument, Python's "can't open file →
   exit 2" path is **structurally impossible**, regardless of how
   `${CLAUDE_PLUGIN_ROOT}` resolves.
2. **Resolve from the runtime environment, not host text substitution.** The
   bootstrap reads `os.environ["CLAUDE_PLUGIN_ROOT"]` at runtime; if absent it
   falls back to the host-expanded `${CLAUDE_PLUGIN_ROOT}` path passed as a
   trailing arg; if both fail it does nothing and exits 0. It runs
   `hook_launcher.py` **only if the file actually exists** (`os.path.isfile`).
3. **A resilient launcher one layer above the script.** `hook_launcher.py`
   resolves the real target *beside its own* `__file__` (no env var needed at
   that layer), runs it in-process via `runpy` (stdin/stdout pass through), and
   returns exit `0` in **every** case — target missing, unknown name, target
   raises, target `sys.exit(n)` (normalized to 0), malformed payload, service
   down/timeout.
4. **Two launcher modes (v0.15.1).** Advisory hooks (`UserPromptSubmit`
   injectors) use **normalize** mode (every exit → 0). The PreToolUse
   lock-conflict hook is routed in **guarded** mode: its own exit code passes
   through (so its `ask` and any deliberate block survive — D-007 preserved), but
   a path-resolution failure or unexpected exception still fails open. This fixes
   the worse-than-advisory false-block where an unresolved `${CLAUDE_PLUGIN_ROOT}`
   would make the PreToolUse Bash hook exit 2 and block **every Bash tool call**.
5. **Portable interpreter (v0.15.1).** Each command chains
   `python3 -c … || python -c … || py -3 -c …` so the hook runs where `python3`
   is not the interpreter name. Safe by spec: only exit `2` blocks, so a missing
   interpreter (127) or a stray parse error is non-blocking; and the bootstrap
   exits 0 on every fail-open path, so the chain only advances when an interpreter
   is genuinely absent (no double execution of the real hook logic).
6. **Detection to prevent regression.** `P-013` flags any advisory `hooks.json`
   command that is not fail-open and supersedes the generic `P-012`.

The bootstrap payload contains **no shell metacharacters** (`$`, backticks,
quotes, pipes) other than its own double-quote delimiters, so it parses
identically under cmd.exe, PowerShell, Git Bash, and POSIX `sh` — verified on
this platform by a `shell=True` smoke test.

---

## Why the fix is fail-open

The only **blocking** hook exit code is exactly `2`. The fix makes `2`
unreachable for advisory hooks at three layers:

- **Bootstrap layer:** `python3 -c` cannot exit 2 from a missing-file (no
  file arg). A syntax error / uncaught exception in `-c` is exit `1`
  (non-blocking). Path resolution that fails → does nothing → exit `0`.
- **Launcher layer:** `main()` wraps everything; it catches `SystemExit` (any
  code, including a hypothetical target `sys.exit(2)`) and `BaseException`, and
  always returns `0`.
- **Target layer (unchanged):** the scripts still `sys.exit(0)` on every internal
  error — now correctly *reachable* because the file always loads when present.

Net: a path-resolution failure degrades to "the reminder silently doesn't fire,"
never "the prompt is blocked." That is the correct posture for an injector.

---

## Current limitations

- **If `CLAUDE_PLUGIN_ROOT` is neither set as an env var nor expandable by the
  host** (worst-case Cowork), the bootstrap cannot locate the launcher and
  **fails open silently** — the reminder/injection does not fire, but the prompt
  is **never blocked**. This is strictly better than the old behavior and is the
  best achievable without a host-provided path. (In normal Claude Code the env
  var is available, so the hook runs as before.)
- **Interpreter portability is best-effort.** The `python3 || python || py -3`
  chain covers Unix (`python3`), python.org Windows (`python`), and py-launcher
  Windows (`py`). If *none* resolve, the hook does not run — but that case is
  non-blocking by spec (exit 127), so it is a functionality gap, not a safety gap.
- **P-013 emits only on static evidence** (current `hooks.json` actually risky).
  Runtime log signatures only *escalate* to Critical — they never independently
  raise P-013, because the same stderr text (`${CLAUDE_PLUGIN_ROOT}`, `[Errno 2]`)
  also appears in transcripts that merely *discuss* the failure. A bare
  "exit code 2" is intentionally **not** matched (it collides with ordinary
  shell output and would regress the existing false-positive guards).
- **The lock hook is guarded, not fully fail-open.** A *path-resolution* failure
  or internal crash fails open (no false block), but if the script loads and
  deliberately exits non-zero, that decision passes through (by design). The lock
  hook currently only ever `ask`s (exit 0), so today this is observationally
  identical to "always exit 0" — guarded mode is future-proofing for a deliberate
  block. The P-013 detector remains scoped to advisory (`UserPromptSubmit`) hooks.

---

## Tests added / updated

**`hooks/test_hook_launcher.py` (new, 24 tests)** — runs the *real* `hooks.json`
bootstrap and asserts exit `0` (never `2`):

- unset root · literal `${CLAUDE_PLUGIN_ROOT}` · nonexistent root · missing target
- target raises · target `sys.exit(2)` (normalized) · malformed payload · empty payload
- service down (real target) · Windows-style root · project-focus target · fallback-arg recovery
- **guarded lock hook:** intentional `sys.exit(2)` passes through · missing/exception/path-failure fail open · `ask` stdout passes through · real lock target silent-passes
- success path: target stdout passes through · wiring guards (every command uses `-c` + interpreter chain; lock hook guarded) · `shell=True` full-string parse smoke test

**`scripts/test_rag_report.py` (+14 tests, 40 → 54)** —

- `analyze_advisory_hook_safety`: flags raw advisory command; treats `-c`
  bootstrap and `|| exit 0` as safe; ignores PreToolUse; safe on missing/malformed
  `hooks.json`; **this plugin's own hooks are fail-open** (regression guard).
- `P-013`: High when present, Critical with runtime signal, absent when fail-open,
  outranks `P-012` in the generated issue title.
- `hook-path-fatal` signal: matches the real `can't open file …hooks…py` /
  `[Errno 2]` stderr; does not match the existing false-positive strings.

---

## Commands run and results

```
python -m py_compile hooks/hook_launcher.py hooks/test_hook_launcher.py \
       scripts/rag_report.py scripts/test_rag_report.py        → OK
python hooks/test_hook_launcher.py                              → Ran 24 tests — OK
python scripts/test_rag_report.py                              → Ran 54 tests — OK
python scripts/rag_report.py --self-test                      → self-test OK
python validate_plugin.py rag-plugin                          → exit 0; "hooks.json is valid";
                                                                 0 errors (20 pre-existing warnings,
                                                                 10 suggestions)
# end-to-end (--dry-run, never creates issues):
#   fixed plugin    → no P-013; "Advisory hook fail-open: OK"
#   synthetic risky → P-013 leads github-plugins-issue.md (actionable)
```

The validator warnings are **pre-existing** (command frontmatter `author`/`version`
on `reset`/`setup`/`sync-docs`; and the validator naively flagging the top-level
`description`/`hooks` keys of `hooks.json` as "unknown hook events" — the same
keys the original file had). None were introduced by this change.

---

## Git diff summary (delivered to `main`)

```
 rag-plugin/.claude-plugin/plugin.json              |   2 +-
 rag-plugin/CHANGELOG.md                            |  26 ++
 rag-plugin/RAG_PLUGIN_HOOK_FIX_REPORT.md           | 285 ++++++++++++++++
 rag-plugin/RAG_PLUGIN_HOOK_INVESTIGATION_REPORT.md | 235 ++++++++++++++
 rag-plugin/docs/decisions.md                       | 101 ++++++
 rag-plugin/docs/issues/P-013-advisory-hook-blocking.md | 105 ++++++
 rag-plugin/hooks/hook_launcher.py                  | 140 ++++++++
 rag-plugin/hooks/hooks.json                        |   8 +-
 rag-plugin/hooks/test_hook_launcher.py             | 361 +++++++++++++++++++++
 rag-plugin/rules/hook-failopen.md                  |  69 ++++
 rag-plugin/scripts/rag_report.py                   | 125 ++++++-
 rag-plugin/scripts/test_rag_report.py              | 152 +++++++++
 12 files changed, 1603 insertions(+), 6 deletions(-)
```

Committed and pushed to `taqat-techno/plugins` `main` at the user's `/goal`
request. Active `gh` account `a-lakosha` (has write access to `taqat-techno/*`);
switched back to the default `ahmed-lakosha` after the push.

---

## Recommended replacement GitHub issue body

The curated, ready-to-file issue body lives at
**`docs/issues/P-013-advisory-hook-blocking.md`** (target `taqat-techno/plugins`,
title *"advisory UserPromptSubmit hooks can block prompts when hook script path
resolution fails"*). It includes: affected version, why v0.15.0 was still
affected, why v0.13.2 was not stale, the proven mechanism, the still-needed
Cowork runtime logs, the fix summary, tests added, and privacy-safe reproduction
notes. The `/report` engine will also auto-generate the same issue as its lead
plugin finding whenever the risky pattern is present.

**Old `github-plugins-issue.md` superseded? YES.** That file is a *generated*
artifact (it is not committed). Its lead finding/title is the highest-severity
non-info plugin finding; with `P-013` (High/Critical) present it now leads
instead of the `medium` `P-012`. P-012 ("MCP error phrases") is a session-text
signal that could never have detected this hook-fatal failure.

---

## Whether Cowork runtime logs are still needed

**Not for the fix** — the fix is justified by the proven blocking mechanism and
is pure-upside regardless of the trigger. Logs are still needed only to upgrade
the *diagnosis* from PARTIALLY VALID → fully VALID-for-Cowork, and to file the
**host-side** bug (the `${CLAUDE_PLUGIN_ROOT}` non-expansion) with the Claude
Code / Cowork product team. Capture (privacy-safe): hook **stderr** with literal
`${CLAUDE_PLUGIN_ROOT}` + `[Errno 2]`, the recorded **exit code 2**, and evidence
the **prompt was cancelled before the model request**.

---

## Release recommendation

- **Version `0.15.1`** (patch / bugfix) per repo convention; CHANGELOG `[0.15.1]`
  covers the full hook-invocation hardening (advisory fail-open + lock-hook
  guarded + portable interpreter).
- **Delivered to `main`** (direct-to-main, accepted in this workspace) at the
  user's request; the marketplace updater will pick up `0.15.1`.
- **Follow-ups (1) and (2) are now DONE** in this release: the PreToolUse lock
  hook is routed in guarded mode (path-resolution fail-open, `ask` preserved),
  and the interpreter is portable (`python3 || python || py -3`).
- **Remaining follow-up:** file the host-side `${CLAUDE_PLUGIN_ROOT}`
  non-expansion bug with the Claude Code / Cowork product team once Cowork
  runtime logs are available (the plugin already uses the documented variable
  correctly; this is a host issue, not a plugin issue).
