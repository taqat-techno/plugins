# Shell-boundary hazards reference

Command-level detail for rules 7 and 8 of the `windows-script-and-task-authoring` skill: the
Git-Bash/MSYS boundary, the WSL boundary, and process-host bitness. The skill owns the rules; this file
owns the workarounds.

## MSYS path translation — what gets rewritten

Git Bash rewrites arguments **before** the native tool sees them:

| Argument shape | Rewritten to | Symptom |
|---|---|---|
| `/c/Users/...` | left as-is for MSYS tools; **not resolved** by native Windows tools | `FileNotFoundError`; `glob.glob()` returns `[]` with no error |
| `origin/dev:path/to/file` | `origin\dev;path\to\file` (`:`→`;`, `/`→`\`) | git reports the object missing — looks like "never committed" |
| a leading-slash selector (`--test-tags=/module`) | a Windows path | the selector matches nothing; runner reports **"0 of 0 tests" and exit 0** |
| `/dev/null` | `nul` (a **relative path**, not the null device) | a 4-7 KB file named `nul` appears in the working tree |
| a **backslash** Windows path handed to a native exe (`node C:\dir\x.mjs`) | components mangled before the exe resolves them | `MODULE_NOT_FOUND` / `Cannot find module` — reads as a deleted or mis-pathed script |

The dangerous property is shared: **none of these raise.** Every one produces a plausible empty or
successful result, so it is read as a fact about the repository or the disk. The last row is the partial
exception and the one that bites while composing a one-liner — it *does* raise, but with a message that
points at the script rather than at the argument. Quote it **and** use forward slashes
(`node "C:/dir/x.mjs"`) so neither the shell nor the converter has anything to rewrite.

## Workarounds, in order of robustness

Ordered by robustness for **choosing a command shape up front**. The recovery-side catalogue for a command
that has already misbehaved (including the `--%` stop-parsing token and the BOM-on-pipe trap) is owned by
env-doctor's `references/windows-powershell.md`; this list is not a second copy of it.

1. **Pipe through stdin** — sidesteps translation entirely:
   `cat "$f" | python -c 'import sys; ...sys.stdin...'`
2. **Drive-letter paths** for anything a native tool will open: `C:/Users/...`, not `/c/Users/...`.
3. **Relative paths after `cd`, within a single invocation** — nothing to translate. This holds only
   *inside one command*: do not carry the assumption across calls. Each tool invocation may start in a
   directory a previous call left behind, and a relative path then resolves somewhere you did not intend —
   creating a stray file at the drifted location instead of editing the one you meant, with a success
   status either way. Across calls, pass **absolute paths to every file operation**, regardless of where
   the previous command ended up. If an edit reports success but the target looks unchanged, look for a
   stray file at the drifted directory before re-running.
4. **`MSYS_NO_PATHCONV=1`** as a prefix on the single offending command. Use it surgically; disabling
   translation for a whole script breaks the MSYS tools that depend on it.
5. **Move the redirect inside the target shell**: `wsl -- bash -lc "curl ... -o /dev/null"` — the POSIX path
   is then interpreted by the POSIX shell, which is the only interpreter that should see it.
6. **Reshape the command** to avoid a colon: `git ls-tree -r <rev> --name-only -- <path>` instead of
   `git cat-file -e <rev>:<path>`.
7. **Run it from PowerShell** when the tool is Windows-native and the arguments are POSIX-shaped.

## Verification discipline

- A "file not found", an empty glob, or a zero-match test run from a cross-boundary tool is a
  **path-translation suspect first**. Confirm with a second, **differently shaped** command before drawing
  any conclusion about the repository, the disk, or a sync daemon.
- Any test invocation reporting **"of 0 tests"** is a failed invocation. (`test-result-evidence` in the
  agent-safety-guards plugin owns that rule; what this file adds is that a mangled selector is one of its
  causes, and that the runner's own output cannot show it.)
- `ls` succeeding in the same shell where `open()` fails is the signature of case 1, not of a race.
- **Do not test for CRLF with `grep` on an escape sequence.** `grep -c $'\r'` collapses to an *empty*
  pattern in Git Bash, which matches every line — so it reports "249 of 249 lines are CRLF" against a file
  that is pure LF, and the resulting line-ending "defect" is an artifact of the test. Count raw bytes
  instead: `tr -dc '\r' < "$f" | wc -c`. Then be explicit about **which object** you measured: under
  `core.autocrlf=true` the working tree legitimately holds CRLF while the committed blob holds LF, so when
  the question is "what will be committed", measure the staged blob — `git show :<path> | tr -dc '\r' | wc -c`.
- **Never deliver multi-line content through a heredoc.** Quoting misbehaves at the boundary for large
  markdown or code blocks, and long content additionally runs into the command-length limit; both fail by
  writing something subtly different from what you wrote, not by erroring. Write the file with a dedicated
  file-writing tool, or stage the content to a scratch file and have the shell consume it.
- **A pipeline's exit status is the LAST stage's**, so an upstream failure is reported as success. Every
  hazard in the table above already fails silently; wrapping the command in `| tail`, `| head`, or
  `| grep` hides even the ones that would have raised — a mangled `node` path exits non-zero with
  `MODULE_NOT_FOUND` and the compound command still reports **exit 0**. Do not compose a pipe around a
  command whose status matters: run it unpiped and read its output, or set `pipefail` and check
  `${PIPESTATUS[0]}`. (env-doctor's `references/windows-powershell.md` owns the sibling case where the
  pipe additionally **kills** a long-running producer via SIGPIPE.)
- **For anything irreversible — a send, a publish, a move, a delete — verify the side effect, not the
  exit code.** Confirm the artifact reached its destination (the file is in the target directory, the
  message is in the sent log). A background task reporting "completed successfully" while nothing was
  sent is the exact shape this produces, and the transcript will agree with the exit code, not with
  reality.

## The `nul` file (why this one is worse than stray output)

`nul`, `con`, `prn`, and `aux` are **reserved device names** on Windows. A repository containing a file with
one of those names **cannot be checked out on any Windows machine**, so committing it breaks the clone for
every teammate — not just the author. The file appears untracked at exactly the moment of committing, one
`git add .` away from being permanent.

- Keep `nul`, `con`, `prn`, `aux` in `.gitignore` as a backstop. It guards against a mistake the tooling
  makes for you, not against carelessness.
- Removing one afterwards may require a device-namespace path (`\\?\<full path>`), because ordinary tools
  cannot address a reserved name.
- The staging rules that keep it out of a commit (explicit paths, a full `git status` re-check immediately
  before committing) belong to the **`git-safety`** skill — do not restate them here. What is specific to
  this boundary is only that the file is *generated by the tooling*, appears untracked, and appears at
  exactly the moment of committing.

## Process-host bitness

`Process.Path` and `Process.Modules` both route through `EnumProcessModules`, which cannot enumerate a
64-bit process from a 32-bit host. It **returns `$null` and `@()` rather than raising**, so `try/catch`
never fires and the caller sees "no processes matched".

How you end up in a 32-bit host without asking for one:

- An installer or launcher built without a 64-bit architecture declaration resolves `powershell.exe`
  through WOW64 to `SysWOW64\WindowsPowerShell` — the 32-bit host.
- Any parent process that is itself 32-bit passes that host down to its children.

```
# bitness-independent, out-of-process
Get-CimInstance Win32_Process |
  Where-Object { $_.ExecutablePath -like "$root*" } |
  Select-Object ProcessId, Name, ExecutablePath

# confirm which host you are in
[Environment]::Is64BitProcess
```

- Use `Get-CimInstance Win32_Process` for executable paths whenever bitness is not guaranteed.
- Treat an **empty module list as "could not read"**, never as "holds nothing" — the difference decides
  whether an upgrade stops the running engine before deleting its files, or leaves it running and aborts
  mid-write on a locked DLL.
- Print `[Environment]::Is64BitProcess` at the top of any inventory sweep so its output is self-describing.
