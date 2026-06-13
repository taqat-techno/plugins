# LSP / Node CLI spawn diagnosis

A Node-based language server or CLI tool fails to start when a host launches it.
This reference explains why it happens, how to fix it durably, and what to
verify. It is platform-neutral; OS- and tool-specific details appear only in
clearly labeled illustrative blocks and are never required for the fix.

## Symptom

A host process (an editor, an LSP client, an MCP server launcher, a build
runner) tries to spawn a Node-based command and the child never starts. The
host surfaces a spawn-layer error rather than a program error, commonly:

- `spawn <command> ENOENT` — the host could not find the named executable.
- `Error: EINVAL` or `spawn EINVAL` — the host found a file but the OS refused
  to execute it directly.
- The server "exits immediately", "failed to start", or "connection closed"
  with no further output, and nothing reaches the tool's own logs.

The defining trait: the failure is at the moment of launch, before the tool
prints anything. The tool itself is installed and runs fine when you type its
name in an interactive terminal — only programmatic spawning fails. That gap
between "works in my terminal" and "fails when the host spawns it" is the
signature of this class of problem.

## Root cause

Hosts that spawn child processes often do so without a shell (the equivalent of
`shell: false`). A no-shell spawn passes the command straight to the operating
system's process-creation call, which can only execute a real binary — not a
text wrapper that a shell would otherwise interpret.

Global installs from a package manager frequently create a small wrapper
("shim") on `PATH` instead of a real binary. The shim is a script that locates
the runtime and forwards arguments. When a host spawns that shim with no shell,
two things go wrong:

- The OS has no interpreter for a script wrapper at the raw process-creation
  layer, so it returns an `EINVAL`/`ENOENT`-style error.
- Some runtimes have additionally tightened security so they refuse to execute
  certain script-wrapper file types unless a shell is explicitly involved,
  turning a previously-working setup into a hard failure after an upgrade.

> Example (illustrative — not required): On Windows, a global npm install of a
> Node CLI creates `tool.cmd` (a batch shim) and `tool.ps1` alongside an
> extensionless `tool` script in the npm prefix directory. A host using
> `shell: false` cannot run `tool.cmd`, and recent Node releases refuse to spawn
> `.cmd`/`.bat` wrappers without a shell for security reasons — so the language
> server reports `spawn ... EINVAL` even though `tool --version` works in the
> terminal.

## Fix pattern

Do not point the host at the bare shim. Instead, give the host the real runtime
binary plus the package's JavaScript entrypoint as an argument, along with
whatever transport flag the host needs (commonly a stdio flag for language
servers and MCP-style servers).

Generic shape:

```
command: <absolute-or-on-PATH path to the real runtime executable>
args:    [ <path to the package's JS entrypoint>, <transport/stdio flag> ]
```

Why this works: the runtime executable is a genuine binary the OS can launch
with no shell, and the JS entrypoint is plain data passed to it as an argument —
no wrapper interpretation is needed at the process-creation layer.

To find the entrypoint without hardcoding a path, ask the package manager or the
runtime where the package lives, then resolve its declared `bin` entry (the JS
file the shim would have executed). Prefer values the host or a small resolver
computes at runtime over paths copied from one machine.

> Example (illustrative — not required): Instead of `command: "pyright-langserver"`
> (a shim), configure `command: "node"` with
> `args: ["<resolved>/pyright/langserver.index.js", "--stdio"]`, where
> `<resolved>` comes from querying the global package location. The same shape
> applies to a TypeScript server: point `node` at the package's server JS plus
> its stdio flag rather than at the `tsserver`/`typescript-language-server` shim.

## PATH and binary-resolution checks

If the fix still fails, confirm the host can actually resolve the binaries it is
being asked to run:

1. Verify the runtime executable is on the `PATH` the host inherits. A host
   launched from a desktop session, a service manager, or a daemon may have a
   different, smaller `PATH` than your interactive shell — the binary you see in
   the terminal may be invisible to the host.
2. Resolve the executable the same way the OS will: locate it by name on `PATH`
   and confirm it is a real binary, not another shim, and that the path has no
   surprising spaces or quoting that the no-shell spawn would mishandle.
3. Confirm the package's JS entrypoint exists at the resolved location and is the
   file the package's `bin` field names.
4. Watch for package managers that install scripts to a directory not on the
   default `PATH`. Some platform/system package managers place executables or
   user-level scripts in a location the user's shell — and therefore the host —
   does not include by default. If the binary "exists" but the host cannot find
   it, an off-`PATH` install directory is a likely cause; add that directory to
   the `PATH` the host sees, or point the host at the absolute path.

> Example (illustrative — not required): A user-scope install may drop scripts
> into a per-user bin directory that the login shell adds but a background host
> does not, so `which`/`where` finds the tool interactively while the host's
> spawn reports `ENOENT`.

## Reload discipline

Many hosts read server and tool configuration once, at load time, and cache it
for the life of the session. Editing the config has no effect until the host
re-reads it. After applying any change:

- Reload or restart the host (reload window / restart the editor / restart the
  service), or use its explicit "restart server" action if one exists.
- Re-trigger the exact action that failed and confirm the spawn now succeeds.
- Check the host's own logs for the new launch line to verify it is using the
  updated command and args, not a stale cached entry.

Skipping the reload is the most common reason a correct fix appears not to work.

## Durable config vs. self-modification

When choosing where to apply the fix, prefer a configuration scope that you own
and that survives updates:

- Editing a cached, bundled, or marketplace-managed manifest (a file installed
  and owned by a tool, extension, or plugin distribution) is self-modification.
  Those files are overwritten on the next update or reinstall, so the fix
  silently disappears and the symptom returns.
- Instead, set the command and args in a durable user-scope configuration the
  host supports for overrides — for example a user settings file, a per-project
  config the host reads, or an environment the host inherits. This keeps the fix
  outside any tool-managed file so it persists across upgrades.

If the only place a setting can live is a tool-managed file, treat that as a
limitation to report rather than a fix to bake in, and document the override so
it can be re-applied after an update.

## Windows specific: LSP plugins can't launch an npm shim under `shell: false`

On Windows this class bites hardest. A global npm install of a language server puts a `.cmd`
batch shim (plus a `.ps1` and an extensionless script) on `PATH` — not a real executable. An LSP
plugin that spawns its server with `shell: false` (the safe default) hands that `.cmd` straight to
the OS process-creation call, which cannot interpret a batch wrapper; recent Node releases also
**refuse** to spawn `.cmd`/`.bat` without a shell for security. The result is `spawn ... EINVAL`
(or `ENOENT`) at launch even though `<server> --version` works fine when you type it in a terminal.

Localize: confirm the configured `command` points at a `.cmd`/`.ps1`/extensionless npm shim rather
than at the runtime, and that the host spawns with no shell.

Safe action: **point the command at `node` and pass the package's JS entrypoint as an argument**
(plus the stdio/transport flag), per the Fix pattern above — never at the bare `.cmd` shim.
Resolve the entrypoint via the package's declared `bin` (query the npm global location) instead of
hardcoding a per-machine path. Apply this in a durable user-scope config, then reload the host.
Do not "fix" it by re-enabling a shell spawn globally — that re-introduces the security exposure
Node closed; correct the command target instead.

## Quick checklist

- Identify whether the host spawns with no shell (the usual default).
- Replace any bare shim command with the real runtime binary plus the JS
  entrypoint and transport flag.
- Confirm the runtime binary is on the `PATH` the host inherits, not just your
  interactive shell.
- Confirm the JS entrypoint resolves to the package's declared `bin` file.
- Put the fix in a durable user-scope config, never in a tool-managed manifest.
- Reload or restart the host, then re-run the failing action to verify.
- Never print or log secrets, tokens, or environment values during diagnosis.
