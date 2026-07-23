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

- **`kubectl port-forward` returns before the local listener is accepting.** A fixed
  `Start-Sleep 2` (or `sleep 2`) then-connect races the forward's readiness and fails
  intermittently. **Poll for the TCP listener** instead of sleeping a fixed interval:

  ```powershell
  do { Start-Sleep -Milliseconds 200 }
  until (Test-NetConnection 127.0.0.1 -Port <PORT> -InformationLevel Quiet)
  ```

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

## Summary

| Symptom | Section | First safe move |
|---------|---------|-----------------|
| Native exe gets `{k:v}` from `{"k":"v"}` | PS 5.1 quote-strip | pass via `--%` or a file |
| Piped payload rejected at char 0 | UTF-8 BOM on the pipe | BOM-less `$OutputEncoding`; `WriteAllText` no-BOM |
| Excluded dir copied anyway | `Copy-Item -Exclude` | `robocopy /XD` (or filter then copy) |
| `kubectl exec -c` code garbled | exec payload mangling | feed via stdin / `kubectl cp` |
| `port-forward` connects flakily | port-forward startup race | poll TCP-listen, don't fixed-sleep |
| Server dies / test "passes" under `\| head` | SIGPIPE + exit-0 mask | capture to a file; `pipefail` + `PIPESTATUS` |
| `node C:\…` MODULE_NOT_FOUND | Git-Bash path conversion | forward-slash path or `MSYS_NO_PATHCONV=1` |
| `git HEAD:path` rejected in Git-Bash | Git-Bash path conversion | `MSYS_NO_PATHCONV=1` + quote |
| `cannot pickle` only on Windows tests | `--parallel` spawn/pickle | run serially (or inside WSL) |
