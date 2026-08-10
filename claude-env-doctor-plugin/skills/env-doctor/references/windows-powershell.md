# Windows shell & native-exe argument traps (PowerShell / Git-Bash)

Diagnostic notes for the class of Windows failures where a command is *correct* but the **shell
between you and the program mangles it** — quotes stripped, a BOM prepended, an "excluded"
directory copied anyway, a piped payload garbled, a path mistranslated, or a test runner that
cannot fork. These are not application bugs; they are shell/marshalling quirks, and the fix is to
change how the argument or stream is passed, never to rewrite the program. Every section follows
**observe → localize → safe action**. All paths, ports, and names are illustrative; never echo
secrets or environment values while reproducing one of these.

## PowerShell 5.1 strips embedded double-quotes passed to a native exe

Windows PowerShell 5.1 re-parses arguments before handing them to a native `.exe`. An argument
that contains **embedded double quotes** — a JSON blob, an SQL string, a `--flag={"k":"v"}` — has
its inner quotes silently stripped or collapsed, so the exe receives `{k:v}` (invalid) instead of
`{"k":"v"}`. The command looks right on your screen and fails inside the program.

Observe → localize:

- The failing arg contains `"` inside it, the program reports a parse error on input you know is
  well-formed, and the same string works when written to a file and passed by path.
- Confirm by echoing the arg through a quote-faithful probe:

  ```powershell
  # Shows exactly what a child process actually receives, quotes and all
  $args_seen = & cmd /c echo {"k":"v"}   # inspect how PS marshalled it
  ```

Safe action (pick one, least-invasive first):

- Use the **stop-parsing token** `--%` so PowerShell passes the rest of the line verbatim:
  `mytool.exe --% --data={"k":"v"}`.
- Or write the payload to a temp file and pass the **path** (`--data-file <path>`) — this also
  sidesteps the BOM trap below.
- PowerShell 7.3+ fixes this generally via `$PSNativeCommandArgumentPassing = 'Standard'`; that
  knob does **not** exist in 5.1, so on 5.1 prefer `--%` or a file.

## Piping a string into a native exe prepends a UTF-8 BOM

When you pipe a PowerShell string into a native program (`$json | mytool`), 5.1 encodes the pipe
using an encoding that can emit a **UTF-8 byte-order mark** (`EF BB BF`) at the front of the
stream. The receiver sees a leading `﻿` before the first real character and rejects it — a
JSON/YAML parser errors on "unexpected character", `kubectl apply -f -` complains about the
document, a hash comes out wrong.

Observe → localize:

```bash
# Dump the first bytes of whatever the pipe produced; EF BB BF == BOM
printf '%s' "$piped_output" | head -c 3 | xxd
```

- Leading `EF BB BF` (or the parser naming position 0 / `﻿`) → BOM on the pipe, not a payload
  defect.

Safe action:

- Force a BOM-less UTF-8 pipe encoding before the call:
  `$OutputEncoding = New-Object System.Text.UTF8Encoding $false`.
- Note the sibling trap: `Out-File -Encoding utf8` and `Set-Content -Encoding utf8` **also** write
  a BOM in 5.1. To produce a BOM-free file, use
  `[System.IO.File]::WriteAllText(<path>, $text, (New-Object System.Text.UTF8Encoding $false))`.

## `Copy-Item -Recurse -Exclude` does not filter directories

`-Exclude` matches **leaf items by name**, not directory subtrees. With `-Recurse`,
`Copy-Item -Recurse -Exclude node_modules` still copies `node_modules` wholesale — the exclude is
ignored for the directory, and you get the very tree you meant to skip (often huge and slow).

Observe → localize: the destination contains a directory you named in `-Exclude`; the copy took
far longer / far more space than expected.

Safe action: exclude directories with a tool that actually supports it —

```powershell
# robocopy /XD excludes whole directories (also /XF for files); robocopy exit codes 0-7 are success
robocopy <src> <dst> /E /XD node_modules .venv .git

# or filter explicitly, then copy what survives
Get-ChildItem <src> -Recurse -Directory |
  Where-Object { $_.FullName -notmatch '\\node_modules(\\|$)' } | ...
```

## `kubectl exec -- <interpreter> -c` mangles the payload; `port-forward` races startup

Two independent `kubectl` traps on Windows shells:

- **`exec … -- python -c "<code>"` / `sh -c "<code>"`** stacks three quoting layers (your shell →
  kubectl → the in-container shell). Multi-line scripts, quotes, `$`, and backslashes get eaten,
  so the code that runs is not the code you wrote. **Feed the script over stdin** instead of `-c`:

  ```bash
  kubectl exec -i <pod> -- python - < script.py      # '-' reads program from stdin
  # or copy it in, then run it
  kubectl cp script.py <pod>:/tmp/script.py && kubectl exec <pod> -- python /tmp/script.py
  ```

  **The two failure signatures name which layer ate the payload**, and they are easy to misread as
  application faults inside a perfectly healthy pod:

  - `NameError: name '<word>' is not defined`, where `<word>` was a **string literal** you wrote —
    the quote-strip above (`print("ready", …)` arrived as `print(ready, …)`), so the literal became
    a bare identifier. The interpreter is reporting your own text back at you without its quotes.
  - `SyntaxError: invalid non-printable character U+FEFF` on **line 1** — the BOM-on-pipe above. The
    payload is intact; only its first three bytes are not.

  **On 5.1 the two standard workarounds cancel each other:** feeding over stdin is the documented fix
  for quote-stripping, and stdin is exactly what prepends the BOM. So on 5.1 either fix the
  `$OutputEncoding` first (see the BOM section), or take one of the two routes that avoid both layers:

  - **Make the inline payload quote-free** — no string literals at all, e.g.
    `import sys, <mod>; print(<mod>.get_version()); print(sys.version.split()[0])`, using `.split()`
    rather than `.split(" ")`. Nothing is left for the shell to strip.
  - **Put the script in a file** and `kubectl cp` + exec it, which is the only form that survives every
    layer unchanged.

  When handing a command to a **human**, give the **interactive** form (`kubectl exec -it <pod> -- python
  manage.py shell`, no `-c`) — a terminal-attached session has no argument-marshalling layer to corrupt,
  so it is unaffected by both traps. The `-c` form is for automation, and only in one of the two shapes
  above.

- **`kubectl port-forward` returns before the local listener is accepting.** A fixed
  `Start-Sleep 2` (or `sleep 2`) then-connect races the forward's readiness and fails
  intermittently. **Poll for the TCP listener** instead of sleeping a fixed interval:

  ```powershell
  do { Start-Sleep -Milliseconds 200 }
  until (Test-NetConnection 127.0.0.1 -Port <PORT> -InformationLevel Quiet)
  ```

  The delay is not noise to be waited out with a bigger number: a kubeconfig **`exec` credential
  plugin** (a cloud CLI fetching a token) runs before the tunnel binds, so the first seconds have no
  listener by design. **Poll the real TCP listen state** rather than probing the app —
  `Get-NetTCPConnection -LocalPort <PORT> -State Listen` in a loop up to ~25 s is decisive and
  typically satisfied in ~2 s once it is polled instead of slept through.

  Three more things this validation gets wrong:

  - **Capture the forwarder's stderr, not just stdout.** The credential-plugin and bind errors are on
    stderr; a validation reading only stdout reports "no output, must be fine" for a forward that
    never came up.
  - **Do not require a 200.** Use `Invoke-WebRequest -MaximumRedirection 0` so a **307/302 counts as
    tunnel-proven** — an app that redirects on `/` is answering, which is the only thing the probe is
    testing. Following the redirect turns a working tunnel into a confusing failure at some other URL.
  - **Tear down deterministically.** `Stop-Process` the `-PassThru` pid **and** kill any stray
    forwarder whose `CommandLine -like '*port-forward*'`, then re-assert nothing is still listening on
    the port. A survivor holds the port and makes the *next* run's probe pass against the old tunnel.

## Piping a running server / long test into `head` or `tail` kills or masks it

`long-running-cmd | head -n 20` closes the pipe once `head` has its 20 lines; the writer then takes
a **SIGPIPE and dies** — so `npm run dev | head` (or `pytest -x | head`) silently kills the server
or truncates the run. Worse, the pipeline's exit status is **`head`'s** (0), so a crash or non-zero
exit of the real command is **masked** — you conclude "it passed" when it died.

Observe → localize: the process you piped into `head`/`tail` exits early or "succeeds" implausibly
fast; the same command run without the pipe behaves differently.

Safe action: never pipe a long-lived or status-bearing command straight into `head`/`tail`.

```bash
# Capture, then read the file — the real exit status is preserved
long-running-cmd > out.log 2>&1 &
# ... then inspect
head -n 40 out.log
# If you must pipe, surface the real status
set -o pipefail          # bash: pipeline fails if ANY stage fails
cmd | head    # and check ${PIPESTATUS[0]} for the producer's code
```

## Git-Bash mistranslates Windows paths and `<rev>:<path>` arguments

Git-Bash (MSYS2) runs a POSIX→Windows **path-conversion** pass on arguments, which backfires two
common ways:

- **`node C:\path\to\script.js` → `Error: Cannot find module` / MODULE_NOT_FOUND.** The `C:\…`
  form gets munged (backslashes, drive prefix), so Node resolves the wrong path. Use a
  forward-slash path or a relative one:

  ```bash
  node C:/path/to/script.js      # forward slashes survive
  node ./script.js               # relative, run from the dir
  MSYS_NO_PATHCONV=1 node "C:\path\to\script.js"   # or disable conversion for the call
  ```

- **`git show HEAD:src/app.js` (any `<rev>:<path>`) breaks.** The `:` + `/` trip the path
  converter, which rewrites the argument into a bogus `C:/…` path and Git rejects it. Disable
  conversion for that invocation:

  ```bash
  MSYS_NO_PATHCONV=1 git show 'HEAD:src/app.js'
  ```

Observe → localize: the error names a path with an unexpected drive prefix or a `Program Files`
fragment you never typed → path conversion, not a missing file/rev.

## `manage.py test --parallel` pickles on Windows — run serially

Django's `--parallel` runner uses `multiprocessing`, which on Windows starts workers with **spawn**
(not fork). Spawn re-imports and **pickles** the test setup across the process boundary; test
databases, connections, and some fixtures do not pickle cleanly, so the run dies with a
`cannot pickle …` / `PicklingError` that never appears on Linux.

Observe → localize: `PicklingError` / `cannot pickle` only on Windows; the same suite is green on a
Linux CI runner or in WSL.

Safe action: run the suite **serially** on native Windows —

```powershell
py manage.py test --parallel 1     # or simply omit --parallel
```

Keep `--parallel` for the Linux/WSL/CI path where fork is available; this is a platform limit, not
a test defect. (If parallelism on Windows is truly needed, run the suite **inside WSL** instead.)

## Machine `PATH` always beats User `PATH`, and `where` cannot verify a PATH change

Windows composes a new process's `PATH` as the **Machine** entries first, then the **User**
entries. So when the wrong binary wins a bare-name lookup, the deciding question is which half the
shadowing directory sits in: if it is on the *Machine* PATH, **no edit to the User PATH can ever
un-shadow it** — reordering the User half, removing its duplicates, or prepending the correct
directory all leave the Machine hit earlier in the search. The edit looks completely correct and
changes nothing.

The verification trap is worse than the bug. A running shell holds the `PATH` **copied into it at
launch**, so `where <tool>` / `Get-Command <tool>` in the session where you made the edit reports
the pre-edit resolution — before a correct fix and after one alike. Both readings agree and both
are meaningless.

Observe → localize: reconstruct the search order as a *new* process will see it, and walk it —

```powershell
# Machine half first, then User half — the order a freshly launched process gets
$machine = (Get-Item 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Environment').GetValue('Path',$null,'DoNotExpandEnvironmentNames')
$user    = (Get-Item 'HKCU:\Environment').GetValue('Path',$null,'DoNotExpandEnvironmentNames')
($machine + ';' + $user) -split ';' | Where-Object { $_ } |
  ForEach-Object { Join-Path ([Environment]::ExpandEnvironmentVariables($_)) '<tool>.exe' } |
  Where-Object { Test-Path $_ } | Select-Object -First 1
```

Read the **unexpanded** value (`DoNotExpandEnvironmentNames`) so an already-expanded copy is never
round-tripped back into the registry.

Safe action:

- If the shadowing entry is on the Machine PATH and elevation is not available, **rename the
  shadowing binary** (`<tool>.exe` → `<tool>-dev.exe`) rather than fighting the search order. Both
  binaries stay reachable under distinct names and no PATH is touched.
- If a User-PATH write is genuinely required (user-confirmed), preserve its registry **type**.
  `HKCU:\Environment\PATH` is `REG_EXPAND_SZ`; `[Environment]::SetEnvironmentVariable(…,'User')`
  writes it back as **`REG_SZ`**, which permanently breaks every `%VAR%` reference inside it — the
  entries survive as literal text and silently resolve to nothing. Write the type explicitly and
  assert it afterwards:

  ```powershell
  Set-ItemProperty 'HKCU:\Environment' -Name Path -Value $new -Type ExpandString
  (Get-Item 'HKCU:\Environment').GetValueKind('Path')   # must be ExpandString
  ```

- Broadcast `WM_SETTINGCHANGE` afterwards so newly launched apps pick the change up without a
  logoff — and remember **already-running processes keep the old PATH until they restart**,
  including a live MCP server, IDE, or shell. A tool still resolving the old way inside an existing
  process is not evidence the fix failed.

## Summary

| Symptom | Section | First safe move |
|---------|---------|-----------------|
| Native exe gets `{k:v}` from `{"k":"v"}` | PS 5.1 quote-strip | pass via `--%` or a file |
| Piped payload rejected at char 0 | UTF-8 BOM on the pipe | BOM-less `$OutputEncoding`; `WriteAllText` no-BOM |
| Excluded dir copied anyway | `Copy-Item -Exclude` | `robocopy /XD` (or filter then copy) |
| `kubectl exec -c` code garbled | exec payload mangling | feed via stdin / `kubectl cp` |
| `NameError: name '<word>' is not defined` for a word you wrote as a string literal | PS 5.1 quote-strip inside an inline `-c` payload | make the payload quote-free, or pass a file |
| Stdin fixes the quotes and then the payload fails at line 1 | the two workarounds cancel on 5.1 (stdin adds the BOM) | quote-free payload or a file; or BOM-less `$OutputEncoding` first |
| `port-forward` connects flakily | port-forward startup race | poll TCP-listen, don't fixed-sleep |
| Forward "fails" though the tunnel is up, or the next run passes against a dead one | probe follows a redirect / no deterministic teardown | `-MaximumRedirection 0`, read stderr, kill the pid **and** strays, re-assert not listening |
| Server dies / test "passes" under `\| head` | SIGPIPE + exit-0 mask | capture to a file; `pipefail` + `PIPESTATUS` |
| `node C:\…` MODULE_NOT_FOUND | Git-Bash path conversion | forward-slash path or `MSYS_NO_PATHCONV=1` |
| `git HEAD:path` rejected in Git-Bash | Git-Bash path conversion | `MSYS_NO_PATHCONV=1` + quote |
| `cannot pickle` only on Windows tests | `--parallel` spawn/pickle | run serially (or inside WSL) |
| Wrong binary still wins after a User-PATH fix | Machine-before-User PATH | rename the shadowing binary; walk Machine+User from the registry |
| `%VAR%` entries in PATH stop resolving after an edit | `REG_EXPAND_SZ` → `REG_SZ` downgrade | write with `-Type ExpandString`; assert `GetValueKind` |
