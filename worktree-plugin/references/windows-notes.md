# Windows, macOS, and Linux notes

Windows is a first-class target. **WSL is not required** and must not be
assumed. Every item below was verified on Windows 11 with git 2.49 and
Claude Code 2.1.229.

## `bash` on PATH may be WSL

On a typical Windows box `bash` resolves to `C:\Windows\System32\bash.exe`,
which is **WSL**, not Git Bash. Git Bash lives at
`C:\Program Files\Git\bin\bash.exe`.

Never emit a bare `bash …` command into settings or documentation. Claude
Code's own Bash tool runs MSYS/MINGW (`uname -s` reports `MINGW64_NT-…`), so
the plugin's scripts get the right shell when Claude invokes them; the hazard
is only in strings the plugin *writes* for later execution.

## MSYS rewrites leading-slash arguments

Git Bash converts an argument that starts with `/` into a Windows path, so

```sh
tasklist /FI "PID eq 1234" /NH     # -> ERROR: Invalid argument/option - 'C:/Program Files/Git/FI'
```

Disable the conversion for such calls:

```sh
MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*' tasklist /FI "PID eq 1234" /NH
```

`scripts/wt-inventory.sh` depends on this for PID liveness checks.

## Three path spellings for the same directory

| Source | Spelling |
|---|---|
| `git worktree list --porcelain` | `C:/Users/me/repo` |
| `claude agents --json` (`cwd`) | `C:\\Users\\me\\repo` |
| Git Bash `pwd` | `/c/Users/me/repo` |

Normalise before comparing: backslashes to slashes, `C:/x` to `/C/x`, drop a
trailing slash, and compare case-insensitively on Windows (`shopt -s
nocasematch`). This is the single most likely source of a silent Windows bug.

Related: Claude Code's own worktree containment check is case-sensitive, so a
working directory that differs from the canonical on-disk path only in case is
rejected. Always pass canonical paths.

## Status line

- Claude Code runs status-line commands through Git Bash when it is installed
  and through PowerShell when it is not.
- Paths inside the `command` string must use **forward slashes** or `~`. Git
  Bash consumes unquoted backslashes and the command fails with no visible
  error.
- Prefer the `.sh` script even on Windows: measured ~80ms per render versus
  ~600ms for `powershell -NoProfile -File`. Claude Code re-runs the status line
  on a 300ms debounce and cancels renders still in flight.
- Process spawns are expensive here (~100ms each). Both shipped scripts read
  `.git/HEAD` directly instead of calling git.

## Performance

`scripts/wt-inventory.sh` uses fork-free bash string helpers that assign to
globals rather than being called through `$(...)`. An earlier version using
`sed`/`tr` helpers took 23s on an 8-worktree repository; the current one takes
about 2.5s, and about 4s with `claude agents --json` session discovery.

## Other Windows specifics

- `--tmux` is not supported on Windows (`Error: --tmux is not supported on Windows`).
- Cross-session **messaging** is not offered on native Windows (macOS and Linux
  only, including WSL 2). Session **discovery** via `claude agents --json` does
  work on Windows — the two are separate mechanisms.
- Removing a worktree deletes only a junction or directory symlink, not its
  target.
- Quote every path: spaces are normal on Windows.
- Inside a worktree, Claude Code blocks Bash commands it cannot statically
  trace — brace expansion and heredocs with unquoted delimiters. Keep emitted
  commands plain and separate. For PowerShell commands only the
  working-directory check applies.

## macOS and Linux

Nothing special. Note that macOS ships bash 3.2, so the scripts avoid
`${var,,}`, associative arrays, and `mapfile`.
