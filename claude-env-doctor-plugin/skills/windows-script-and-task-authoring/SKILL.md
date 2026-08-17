---
name: windows-script-and-task-authoring
description: >-
  Authoring-time rules for any file or registration a Windows interpreter will later re-parse. Owns the
  ASCII-or-BOM rule for Windows PowerShell 5.1 (a BOM-less UTF-8 .ps1 containing one em-dash is re-decoded
  as Windows-1252 and dies in the parser before line 1, exiting 1 with no output), the
  encoding-on-both-sides rule for read-modify-write (Get-Content without -Encoding plus -Encoding utf8 on
  the way back silently double-encodes a long-lived file), the case-insensitive variable-name collision,
  the Scheduled Task Execute field is the whole program path rule, task XML being UTF-16 only and best
  captured by round-tripping what the OS itself emitted, the RunLevel/elevation and hidden-window and
  execution-time-limit choices a task registration must make deliberately, the 32-bit-host blind spot that
  makes a process audit silently under-report, the MSYS path-translation hazards that fabricate empty glob
  results and a repo-breaking reserved-device file, and the vary-one-dimension-at-a-time discipline when a
  capability is refused. Activates BEFORE the artifact exists - before writing or editing a
  .ps1/.psm1/.cmd/.bat/.vbs, before calling Register-ScheduledTask or schtasks or hand-writing task XML,
  before a script that appends to or rewrites an existing file, before a process or scheduled-task
  inventory sweep, before running a Windows-native tool from Git Bash or invoking wsl from the Bash tool,
  and when a permission error is about to be reported as an external blocker. Does NOT activate on a
  symptom that already happened (exit 1 with no output, mojibake, a spawn failure, a mangled argument) -
  that is the env-doctor skill.
version: 0.2.0
last_reviewed: 2026-08-10
owns:
  - the ASCII-only-or-emit-a-BOM rule for any .ps1/.psm1 that Windows PowerShell 5.1 will run
  - the encoding-on-both-sides rule for read-modify-write of an existing file (silent double-encoding)
  - the PowerShell case-insensitive variable-name collision (and the scalar .Count trap)
  - the Scheduled Task Execute-is-the-whole-path rule, and task XML being UTF-16 with an OS-owned shape
  - the deliberate task-registration choices (RunLevel, hidden-window wrapper, ExecutionTimeLimit, argv-over-environment)
  - the bitness rule for any process/module audit (a 32-bit host silently under-reports 64-bit processes)
  - the MSYS/WSL path-translation hazards at authoring time (empty glob, mangled rev:path, reserved-device file)
  - the pipeline-exit-status rule at authoring time (a pipe reports its LAST stage, so do not wrap a status-bearing command in one, and verify the side effect of anything irreversible)
  - the vary-one-dimension-at-a-time discipline on a refusal, and the privileged-environment blind spot
  - the pre-flight checklist run BEFORE a Windows script is written or a task is registered
defers_to:
  - the env-doctor skill for diagnosing an already-broken environment; it triggers on a SYMPTOM (exit 1 with no output, mojibake, a spawn failure) and therefore can never fire while a script is being composed - this skill is what prevents the symptom existing
  - env-doctor references/windows-powershell.md, which owns the RECOVERY side of the same shell boundary (MSYS_NO_PATHCONV, the stop-parsing token, BOM-on-pipe, Copy-Item -Exclude) - this skill owns only the authoring-time reflex that avoids reaching it
  - the git-safety skill (git-safety plugin) for staging discipline and the pre-commit status re-check; rule 8 supplies only the Windows-specific reason a reserved-device file appears in the tree
  - the test-result-evidence skill (agent-safety-guards plugin) for why a zero-collected run is not a pass; rule 8 supplies only the path-translation cause of one
  - the agent-safety skill (agent-safety-guards plugin) for the don't-route-around-a-permission-denial rule that bounds rule 9's probing
  - references/scheduled-task-authoring.md for the registration recipe, hidden-window wrapper, and backup/rollback contract
  - references/shell-boundary-hazards.md for command-level MSYS/WSL workarounds and the bitness-safe process query
  - the user for every elevation prompt, task deletion, and any change to a task they did not create
user-invocable: false
---

# windows-script-and-task-authoring

## Purpose

Every rule here exists because a file that looked correct in the editor was later re-read by a second interpreter that disagreed about its encoding, its argument boundaries, or its bitness. The author never sees the failure; it surfaces hours later as an unexplained `ExitCode=1`, a corrupted long-lived file, a dozen healthy tasks flagged broken, or a repository nobody on Windows can clone. These are authoring reflexes, not repairs — seconds up front to remove a class of silent, delayed, confidently-wrong results.

## When to use

Activate before, not after, any of these:

- Writing or editing a `.ps1`, `.psm1`, `.cmd`, `.bat`, or `.vbs` a Windows host will execute.
- Writing a script that **reads an existing file and writes it back** (append, patch, migrate, dedupe).
- Registering, modifying, or auditing a **Scheduled Task** (`Register-ScheduledTask`, `Set-ScheduledTask`, `schtasks`, or hand-written task XML).
- Writing a **process inventory** sweep that reads executable paths or loaded modules.
- Invoking a native Windows tool, `git <rev>:<path>`, or `wsl` from the **Bash tool / Git Bash** on Windows.
- A capability just returned `Access is denied` and you are about to call it an external blocker.

Do NOT activate this to debug an environment that is already misbehaving — that is **env-doctor**. This one fires while the artifact is still being composed.

## Pre-flight checklist (BEFORE writing the file or registering the task)

1. **Which interpreter re-parses this file?** `powershell.exe` (5.1) is ANSI-defaulting; `pwsh` assumes UTF-8. If 5.1 is possible, the file must be pure ASCII or carry a BOM.
2. **Any non-ASCII in it?** Em-dash, smart quotes, arrows, box-drawing, accents, emoji — in code, strings, *or comments*. Replace with `-`, `'`, `->`.
3. **Does it read a file it will write back?** Pin `-Encoding` on **both** sides — and decide separately **who parses the output**, because under 5.1 `-Encoding utf8` also writes a BOM that a `.ps1` needs and a `.json` chokes on.
4. **Do any two variables differ only by case?** `$T` and `$t` are one variable.
5. **Registering a task?** Decide RunLevel, window visibility, `ExecutionTimeLimit`, `MultipleInstances`, and whether configuration rides in **argv** rather than the environment.
6. **Enumerating processes or modules?** Host bitness matters — use an out-of-process query.
7. **Which shell launches it?** If Git Bash, audit every argument for a leading `/`, an embedded `:`, or a backslash Windows path — and check that nothing whose success matters is inside a pipe.
8. **Is there a backup and a rollback** for anything registered, deleted, or rewritten?

## The authoring rules

### 1. A `.ps1` for PS 5.1 must be pure ASCII, or carry a BOM

A file written as **UTF-8 without a BOM** — what most editors and file-writing tools emit — is decoded by `powershell.exe` (5.1) as **Windows-1252**. An em-dash (`E2 80 94`) becomes three CP1252 characters, and the trailing `0x94` is a curly closing quote that **pre-terminates the enclosing string literal**, cascading into bogus parser errors many lines below the real one. The parser aborts before line 1 runs: exit code 1, no output, no log. Launched via `Start-Process -Verb RunAs -Wait -PassThru` that reads exactly like a UAC or argument-quoting failure, and attempts get burned on the launcher instead.

- Replace `—`/`–` with `-`, curly quotes with `'`/`"`, arrows with `->`; or write the file **with a BOM** (`Out-File -Encoding utf8` under 5.1 emits one). Markdown and `.txt` are unaffected.
- Syntax-check without executing: `[System.Management.Automation.Language.Parser]::ParseFile($path,[ref]$null,[ref]$errs)`.
- Diagnose "exit 1, zero output" by running the script **directly** (`& $script`) — parser errors print immediately and name the line.

### 2. Pin `-Encoding` on BOTH sides of a read-modify-write

`Get-Content -Raw` with **no** `-Encoding` falls back to Windows-1252 under 5.1. Handing that result to `Set-Content`/`Add-Content -Encoding utf8` re-encodes the mis-decoded characters as UTF-8 — classic double-encoding. Unlike rule 1, which fails loudly at parse time, **this corrupts data silently**: the command reports success and the terminal renders it plausibly.

- Pass `-Encoding UTF8` to the **read** as well as the write, or do the round-trip in .NET (`[IO.File]::ReadAllBytes` + `UTF8.GetString`).
- `Set-Content`/`Add-Content` default to the **system ANSI codepage** — pass `-Encoding utf8` explicitly for any file another tool will read. Never rely on the default of `>`/`>>`/`Out-File`; it varies by host.
- **`-Encoding utf8` is not BOM-neutral under 5.1, and the BOM is a fix for rule 1 but a defect here.** The same switch that saves a `.ps1` (rule 1) prepends `EF BB BF` to whatever else you write with it, and a data file is read by a parser that does not skip it — a strict JSON/YAML reader errors at position 0, a checksum diverges, and a config loader sees a first key named `﻿key`. So: BOM for a `.ps1`/`.psm1` the 5.1 parser will re-read; **no BOM** for any `.json`/`.yaml`/`.csv`/`.md`/`.txt` a non-PowerShell consumer will parse — write those with `[IO.File]::WriteAllText($path, $text, (New-Object Text.UTF8Encoding $false))`. Decide which of the two the file is *before* picking the writer.
- Verify by **re-reading as UTF-8 and diffing a known character class**, not by eyeballing terminal output, which lies in both directions. The damage inverts exactly if caught early: `UTF8.GetString([Text.Encoding]::GetEncoding(1252).GetBytes($text))` — and the byte arithmetic proves it.

### 3. PowerShell variable names are CASE-INSENSITIVE

`$T` and `$t` are the **same variable**. A master collection `$T = Get-ScheduledTask | ...` is destroyed by a later `foreach ($t in $others) { ... }`; after the loop `$T` holds the loop's **last element** — a single object. Every downstream `foreach`/`Where-Object` then works on one item and returns near-zero counts, while a section that ran *before* the collision printed correct data.

- Name a collection and its loop variable distinctly (`$AllTasks` + `$task`). The same case-insensitivity extends to the **automatic** variables the runtime populates for you (`$args`, `$input`, `$error`, `$host`, `$matches`): assigning one does not create a private name, it overwrites the runtime's — so `$input` set by hand empties the pipeline enumerator the next `process` block reads, and a hand-set `$error` destroys the error history a later `catch` inspects. Both fail far from the assignment. Use `$argStr` and friends.
- **All-zero aggregates beside a detail dump with real hits is a collision signature**, not "no findings".
- In PS 5.1 `.Count` on a single-element `Where-Object` result is `$null` (a scalar, not an array) — wrap in `@(...)` or use `Group-Object` for reliable counts.

### 4. A task's `Execute` field is the WHOLE program path

`<Command>` (the `Execute` field) is the **entire program path**; `<Arguments>` is a separate field. Splitting `Execute` on whitespace and taking `[0]` turns `C:\Program Files\nodejs\node.exe` into `C:\Program`, so a `Test-Path` check false-negatives a dozen healthy tasks as "missing executable" — tasks that had just run with `LastTaskResult` `0x0`.

- Resolve with `Test-Path -LiteralPath ($exe.Trim().Trim('"'))` after environment expansion — strip only surrounding quotes, never space-split. Fall back to `Get-Command` only when the value has **no path separator** (a bare `wsl`/`node` on PATH).
- **Cross-check**: a task whose `LastTaskResult` is `0x0` almost certainly has a resolvable exe. If your check disagrees with the scheduler, the check is wrong. Same family — a COM handler missing from `HKCR\CLSID\...\InprocServer32` is not orphaned; packaged apps register under `HKLM\SOFTWARE\Classes\PackagedCom\`, and a classic lookup false-flags them.

### 5. Task XML is UTF-16 only, and the OS owns its canonical shape

`schtasks /create /xml` accepts **UTF-16 only**. A UTF-8 file — even with a BOM — is rejected as `The task XML is malformed`, which reads like a schema error and is not one. Worse, the **emitted element order and the documented order disagree**, and the scheduler is the party that must accept the file.

- Never hand-write task XML from the published schema. **Round-trip the canonical XML**: register once with `Register-ScheduledTask`, then `schtasks /query /xml` (or `Export-ScheduledTask`) and edit that.
- `schtasks.exe` is **not** the Task Scheduler API — the COM/PowerShell surface expresses things the CLI cannot, so "the CLI can't" is never "the OS won't". Concretely, `schtasks /sc onlogon` emits a `<LogonTrigger>` with **no `<UserId>`** ("at logon of *any* user"), which only an administrator may register, while `Register-ScheduledTask -AtLogOn -User $env:USERNAME` succeeds unelevated.
- **Registration is a replace, not a patch, and there is no undo.** `Register-ScheduledTask -Force` (and `schtasks /create /f`) rewrites the whole task definition from what you supplied, so every trigger, principal, and setting you did **not** restate is dropped rather than preserved, and the scheduler keeps no prior version to roll back to. The pre-change export is therefore the only surviving copy of what the task was: `Export-ScheduledTask` into a hash-manifested backup before any change, and ship a `rollback.ps1` that restores each original with `Register-ScheduledTask -Xml`. (Hash-manifested because a task XML that was silently re-encoded on the way to disk restores something other than what you exported — see rule 2.)

### 6. Registration choices a task must make deliberately

Each is a default that is wrong for a common case (recipes in `references/scheduled-task-authoring.md`):

- **RunLevel decides whether elevation is needed to touch your own task.** `Set-ScheduledTask` / `Unregister-ScheduledTask` on tasks you created succeed **unelevated for `RunLevel=Limited`** (the task DACL grants the creating user FullAccess) and return `Access is denied` for **`RunLevel=Highest`** (admin-only DACL). Registering `Highest` needlessly buys a UAC prompt for every future edit.
- **A console payload needs a hidden-window wrapper.** A task running `node`/`python`/`cmd`/a `.ps1` flashes a console window. Point the action at `wscript.exe //B //Nologo "<wrapper>.vbs"`, where the VBS does `CreateObject("WScript.Shell").Run "<cmd>", 0, True` then `WScript.Quit rc` — style **0 = hidden**, wait **True** plus `WScript.Quit` propagates the child's real exit code into `LastTaskResult`. `wscript` is a GUI host so no console host appears; `-WindowStyle Hidden` on powershell still flickers. Keep wrappers outside the repo and outside `%TEMP%` — **the task stores an absolute path and never re-resolves it**, so a wrapper under a synced/cloned tree or a temp directory that a cleaner sweeps leaves a registered task pointing at nothing, failing on a schedule with no code change to blame.
- **A pin / watchdog task needs `ExecutionTimeLimit` unlimited** — a time limit **kills** a task whose whole job is to stay attached. Pair with `MultipleInstances=IgnoreNew` so self-heal triggers cannot stack duplicates, and trigger on **AtLogon plus a short repeating interval**, since AtLogon-only never fires again after first login. A keepalive that starts something and **returns** is a no-op.
- **Put configuration in argv, not the environment.** A task's `<Exec>` element has **no environment child**, so a cross-platform spec field that a systemd unit and a launchd plist both carry is dropped without a word on Windows, and the process comes up on different defaults than the one that registered it.

### 7. A 32-bit host silently under-reports 64-bit processes

`Process.Path` and `Process.Modules` both route through `EnumProcessModules`, which **cannot enumerate a 64-bit process from a 32-bit one**. It does not raise — it returns `$null` and `@()`, so a `try/catch` never fires. A 32-bit launcher (an installer built without a 64-bit architecture declaration resolves `powershell.exe` through WOW64 to `SysWOW64`) therefore runs a path-scoped sweep that finds **zero** owned processes on a machine running four, so nothing is stopped and the file deletion that follows hits a locked DLL and aborts mid-write.

- Use `Get-CimInstance Win32_Process` for executable paths whenever bitness is not guaranteed — it is out-of-process and bitness-independent. Print `[Environment]::Is64BitProcess` at the top of any sweep, and treat an **empty module list as "could not read"**, never as "holds nothing".

### 8. The MSYS/Git-Bash boundary fabricates results — and one repo-breaking file

Translation rewrites arguments before the native tool ever sees them, and none of these raise:

- **Native Windows Python cannot resolve an MSYS `/c/...` path.** `open('/c/Users/...')` raises FileNotFoundError and `glob.glob('/c/...')` returns `[]` **silently**, in the same shell where `ls /c/Users/...` lists the file — which reads as "the files are gone". Use a drive-letter path, a relative path after `cd`, or **pipe the file into stdin**, which sidesteps translation entirely.
- **A colon-bearing argument is treated as a path LIST.** `git cat-file -e origin/dev:.claude/x.md` becomes `origin\dev;.claude\x.md` (`:`→`;`, `/`→`\`), failing for some paths while identical checks on others pass — which looks exactly like "those files were never committed". Reshape the command so no colon reaches the boundary (`git ls-tree -r <rev> --name-only -- <path>`). A leading-slash test selector is mangled the same way, so the selector matches nothing and the runner **exits 0 having collected nothing** — for why that is not a pass, `test-result-evidence` (agent-safety-guards) owns the rule; what this skill adds is that path translation is a *cause* of one, and it is invisible in the runner's own output.
- **`wsl -- <cmd> -o /dev/null` writes a FILE named `nul` into the working tree.** The POSIX argument is rewritten to the device name `nul` before `wsl.exe` sees it, so the redirect target becomes a relative path, not a null sink. `nul` (like `con`, `prn`, `aux`) is a **reserved device name**: a repository containing one **cannot be checked out on any Windows machine**, so committing it breaks the clone for every teammate, and removing it afterwards needs a device-namespace path (`\\?\<full path>`) because ordinary tools cannot address the name. Write the redirect *inside* the WSL shell (`wsl -- bash -lc "... -o /dev/null"`), and keep `nul|con|prn|aux` in `.gitignore` as a backstop against a mistake the tooling makes for you rather than one you made. The staging discipline that keeps it out of a commit is `git-safety`'s rule, not this skill's — the point here is that this artifact appears **untracked, unbidden, and at the moment of committing**, which is precisely the case a broad add captures.

- **A Windows path with backslashes handed to a native exe is mangled the same way.** `node C:\dir\x.mjs` from Git Bash fails `MODULE_NOT_FOUND` — which reads as a deleted or mis-pathed script, not as an argument that never arrived intact. Quote it and use forward slashes: `node "C:/dir/x.mjs"`.
- **Do not wrap a status-bearing command in a pipe — the pipeline reports the LAST stage's exit code.** `<cmd> | tail` exits **0** when `<cmd>` died, so the one hazard on this boundary that *does* raise gets converted into a silent success alongside all the ones that never did. Run it unpiped and read the output, or set `pipefail` and check `${PIPESTATUS[0]}`. The companion rule for irreversible work — verify the **side effect**, never the exit code — is stated in full under *Verification discipline* in `references/shell-boundary-hazards.md`.

**General rule: on Windows a "file not found" or empty result from a cross-boundary tool is a path-translation suspect FIRST** — confirm with a second, differently-shaped command before concluding anything about the repo or the disk. Once a command has already misbehaved, the workaround catalogue (`MSYS_NO_PATHCONV=1`, the `--%` stop-parsing token, stdin feeding, BOM-on-pipe) belongs to env-doctor's `references/windows-powershell.md`; what this rule buys is not composing the argument that needs it.

### 9. When a capability is refused, vary ONE dimension at a time

`Access is denied` from a single command says nothing about *which part* is privileged. Probing dimensions separately turns an assumed external blocker into a locatable defect: on the same non-admin account, `schtasks /sc onlogon` is denied, `/sc onlogon /ru <me>` is denied, but `/sc once` **works** in the same namespace and the PowerShell API **works**, including into a newly created folder. Neither the library root nor folder creation was privileged — the trigger shape was.

- Vary **trigger type, target scope, and API surface** independently before concluding anything.
- **This is locating a boundary, NOT shopping for a way past one — and the two look identical from the outside.** The distinction is what the refusal came from. An **OS access check on a capability the design gets to choose** (which trigger shape, which folder, which API) is a design input: the succeeding variant tells you the feature should have been built that way, and you adopt it. A **harness permission denial, or a refusal of the operation the user actually asked for**, is not a dimension to vary — retrying it through another transport is the route-around that `agent-safety` (agent-safety-guards) forbids, and finding a surface that happens not to be gated does not mean you were authorized. If you cannot name which of the two you are probing, you are shopping. Stop and report.
- **The privileged environment is the one that hides this bug class.** Elevating would have made the checks pass and shipped a per-user feature that cannot start itself; a CI runner that is administrator by default would not have caught it either. Reproduce under the *least* privileged realistic identity.
- Complete all permission-independent work, then report the gated step as a named blocker with the exact surface and permission required.

## Decision framework

| Question at authoring time | Answer | Consequence if ignored |
|---|---|---|
| PS 5.1 may run this `.ps1`? | ASCII-only, or emit a BOM | Parser dies before line 1 — exit 1, no output |
| Reads a file and writes it back? | `-Encoding` on **both** sides | Silent double-encoding of a long-lived file |
| Who parses the file you are writing? | PS 5.1 -> BOM; anything else -> `WriteAllText` + `UTF8Encoding $false` | A BOM the consumer does not skip: parse error at position 0 |
| Two names differ only by case? | Rename to distinct names | Collection collapses to the loop's last element |
| Need the exe out of `Execute`? | `Trim().Trim('"')` + `-LiteralPath` | Space-split false-flags healthy tasks as broken |
| Writing task XML? | Round-trip the OS-emitted XML, save UTF-16 | `The task XML is malformed` for an encoding reason |
| CLI can't express it? | Use the PowerShell/COM API | "CLI can't" mistaken for "OS won't" |
| Task edits should not need UAC? | `RunLevel=Limited` | Every later self-edit returns `Access is denied` |
| Payload is a console app? | `wscript.exe //B` VBS wrapper, `Run cmd,0,True` | Window flash, or a lost real exit code |
| Task must stay attached? | `ExecutionTimeLimit` unlimited + `IgnoreNew` | The time limit kills the pin |
| Config must reach the task? | Put it in **argv** | `<Exec>` has no environment child — dropped silently |
| Enumerating processes/modules? | `Get-CimInstance Win32_Process` | 32-bit host returns `$null`/`@()` with no error |
| Arg starts with `/` or holds `:`? | Drive-letter path, stdin, or `MSYS_NO_PATHCONV=1` | Empty glob, mangled rev, `0 of 0 tests`, a `nul` file |
| Passing a Windows path to a native exe from Git Bash? | Quote it, forward slashes: `node "C:/dir/x.mjs"` | `MODULE_NOT_FOUND` misread as a missing script |
| The command's success matters? | Run it unpiped, or `pipefail` + `${PIPESTATUS[0]}` | The pipe returns the last stage's 0 over an upstream failure |
| The command is irreversible? | Verify the **side effect** at its destination | "Completed successfully" while nothing happened |
| Got `Access is denied`? | Vary one dimension; retest unprivileged | A product defect reported as an external blocker |

## Validation checklist

- [ ] `Select-String -Pattern '[^\x00-\x7F]'` over the script returns nothing, or the file carries a BOM.
- [ ] `[Parser]::ParseFile(...)` reports zero syntax errors, and the script was run **directly** once (`& $script`), not only through its elevated launcher.
- [ ] Every `Get-Content` feeding a later write carries `-Encoding`, every write carries `-Encoding utf8`, and the rewritten file was re-read as UTF-8 and diffed on a known character class.
- [ ] Each written file's BOM state matches its consumer: BOM only where the 5.1 parser re-reads it, no BOM on anything a non-PowerShell parser opens.
- [ ] No two in-scope variables differ only by case; no automatic variable is shadowed; any `.Count` read off a `Where-Object` result is wrapped in `@(...)`.
- [ ] Task `Execute` resolution uses `-LiteralPath` on the trimmed, unquoted, env-expanded whole string, and no check disagrees with a `LastTaskResult` of `0x0`.
- [ ] Task XML is UTF-16 and came from an OS round-trip, not from the published schema.
- [ ] RunLevel, window visibility, `ExecutionTimeLimit`, and `MultipleInstances` were each chosen on purpose, and the task's configuration rides in argv rather than an environment field the backend may drop.
- [ ] Process/module enumeration uses an out-of-process, bitness-independent query.
- [ ] Every Git-Bash-launched argument was audited for a leading `/` or an embedded `:`, and no `nul`/`con`/`prn`/`aux` was created in the tree (`git-safety` owns the pre-commit status re-check that would catch one).
- [ ] No status-bearing command is wrapped in a pipe (or `pipefail` + `${PIPESTATUS[0]}` is in place), and every irreversible action was confirmed by its side effect rather than its exit code.
- [ ] A hash-manifested export and a working `rollback.ps1` exist before any task is changed or deleted.

## Anti-patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Em-dash in a `.ps1` comment | PS 5.1 re-decodes UTF-8 as CP1252; `0x94` closes a string early | ASCII-only, or write with a BOM |
| Blame the launcher for `ExitCode=1` with no output | The parser aborted before line 1; the launcher was fine | Run `& $script` directly; errors name the line |
| `$t = Get-Content -Raw f; Add-Content -Encoding utf8 $t` | CP1252 read + UTF-8 write = silent double-encoding | `-Encoding` on both sides, or round-trip in .NET |
| Eyeball terminal output to confirm an append | The console misrenders in both directions | Re-read as UTF-8, diff a known character class |
| `$T = @(...)` then `foreach ($t in ...)` | Same variable; `$T` becomes the loop's last element | `$AllTasks` + `$task` |
| Report "0 findings" from all-zero aggregates | A detail dump with real hits means a scope collision | Suspect the collision; re-run the aggregate |
| `$exe = $task.Execute.Split(' ')[0]` | `C:\Program Files\...` becomes `C:\Program` | `Test-Path -LiteralPath ($exe.Trim().Trim('"'))` |
| Hand-write task XML from the docs, save as UTF-8 | Emitted element order differs from the documented one, and UTF-8 is rejected as `The task XML is malformed` | Round-trip `schtasks /query /xml`; save UTF-16 |
| "`schtasks` can't, so it needs admin" | The CLI is not the API; COM expresses more | Try `Register-ScheduledTask` with explicit `-User` |
| Action points straight at `node`/`python`/a `.ps1` | Console window flashes on every run; a bare wrapper also loses the real exit code | `wscript.exe //B` VBS wrapper, `Run cmd,0,True` |
| Leave the default `ExecutionTimeLimit` on a pin | The limit kills the long-lived process | Unlimited, plus `MultipleInstances=IgnoreNew` |
| Pass config via an `environment` field | `<Exec>` has no environment child; dropped silently | Encode it in argv |
| Audit processes from whatever host launched you | A 32-bit host returns `$null`/`@()` with no exception | `Get-CimInstance Win32_Process`; empty = unreadable |
| Conclude "the files are gone" from an empty glob | Native Python cannot resolve an MSYS `/c/...` path | Drive-letter path, stdin, or `MSYS_NO_PATHCONV=1` |
| `node C:\dir\x.mjs` from Git Bash | Backslash components are mangled; `MODULE_NOT_FOUND` reads as a missing script | Quote it with forward slashes: `node "C:/dir/x.mjs"` |
| Append `\| tail` to a command whose success matters | The pipeline reports `tail`'s status, so an upstream failure exits 0 | Run it unpiped, or `pipefail` + `${PIPESTATUS[0]}` |
| Report an irreversible action done because it exited 0 | Exit code proves the last stage ran, not that the send/move/publish landed | Verify the side effect at its destination |
| `-Encoding utf8` on a `.json`/`.yaml` a non-PowerShell tool parses | Under 5.1 that switch also emits a BOM; a strict parser errors at position 0 and a checksum diverges | `[IO.File]::WriteAllText(..., UTF8Encoding $false)` — BOM saves a `.ps1`, breaks a data file |
| `wsl -- curl -o /dev/null` from Git Bash | Creates a real file named `nul`; a repo holding one cannot be cloned on Windows, and ordinary tools cannot even delete it | Redirect inside the WSL shell; `.gitignore` the device names (staging discipline is `git-safety`'s) |
| Call one `Access is denied` an external blocker, then verify the fix elevated | One failing command cannot locate the privileged part, and the privileged environment hides the whole bug class | Vary trigger/scope/API one at a time; reproduce under the least privileged identity |

## Cross-references

- `references/scheduled-task-authoring.md` — registration recipes, the hidden-window VBS wrapper, the elevation escape hatch, and the export/rollback contract.
- `references/shell-boundary-hazards.md` — command-level MSYS/WSL translation workarounds and the bitness-safe process query.
- `env-doctor` (skill, same plugin) — owns diagnosis of an environment that is **already** broken; it triggers on symptoms and cannot fire while a script is being written. This skill is the upstream half.
- `env-doctor` → `references/windows-powershell.md` — owns the **recovery** catalogue for the same boundary this skill's rules 1, 2, and 8 avoid: the `--%` stop-parsing token, BOM-on-pipe, `Copy-Item -Exclude`, and the `MSYS_NO_PATHCONV=1` workarounds. Read it when a command has already misbehaved; read this skill before writing one.
- `git-safety` (skill, git-safety plugin) — owns staging discipline (`never git add .`) and the pre-commit full-status re-check. Rule 8 supplies only the Windows-specific way a reserved-device file arrives in the tree unbidden.
- `test-result-evidence` (skill, agent-safety-guards plugin) — owns why a zero-collected run is not a pass. Rule 8 supplies only the path-translation cause of one.
- `agent-safety` (skill, agent-safety-guards plugin) — owns the don't-route-around-a-permission-denial rule that **bounds** rule 9: probing locates which dimension is privileged, it never authorizes reaching the denied operation by another surface.
