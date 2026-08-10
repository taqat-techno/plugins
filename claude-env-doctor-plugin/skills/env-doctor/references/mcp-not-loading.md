# MCP server not loading — diagnosis ladder

A reusable, platform-neutral procedure for diagnosing why a Model Context Protocol (MCP) server fails to load in a Claude client. Work the ladder top to bottom: each rung either resolves the problem or tells you which rung to try next. Never print secrets, tokens, or environment values while diagnosing.

## Where MCP configuration actually lives

There are two distinct sources of MCP servers, and confusing them is the most common reason a server "won't load."

- **User-scope MCP servers** are configured through the Claude CLI (the `claude mcp` family of subcommands) and persisted into the **user dotfile in the home directory**. This is a single per-user file, not a per-project file. A frequent mistake is editing a same-named file *inside the config folder* and expecting it to take effect — that is not where user-scope servers are read from. The CLI owns this file; prefer editing through the CLI over hand-editing.
- **Plugin-declared MCP servers** are declared by the plugin itself in the plugin's `.mcp.json`. This file lives with the plugin's other assets and defines the server name plus the exact spawn command, arguments, and any environment the server needs. When a plugin's MCP tools are missing, this file — not the user dotfile — is the source of truth for *how* the server is supposed to start.

Decide which source you are debugging before touching anything. User-scope problems live in the home-directory dotfile; plugin problems live in the plugin's `.mcp.json`.

## The diagnosis ladder

### Rung 1 — List what is actually configured

Ask the CLI what it believes is configured:

```
claude mcp list
```

If the expected server is **absent** from the list, the problem is upstream of the server itself: the configuration was never registered, was registered in the wrong scope, or was lost (see "Concurrent-session clobber"). Fix registration before anything else — there is no point debugging a spawn that the client never attempts.

If the server **is** listed but its tools still do not appear, continue to Rung 2: the client knows about it but the process is failing to come up.

### Rung 2 — Read the plugin's `.mcp.json` to find the exact spawn command

For a plugin server, open the plugin's `.mcp.json` and read the precise command, argument vector, and declared environment for the failing server. Do not paraphrase it — you need the literal command the client runs so you can reproduce it. For a user-scope server, derive the same details from the CLI's view of the entry.

### Rung 3 — Run the spawn command manually in a terminal

Execute that exact command yourself in a plain terminal. The client usually swallows the server's startup output, so running it by hand is what surfaces the **real error**. Reproduce the command faithfully (same binary, same arguments). This single step resolves most cases because it converts a silent "didn't load" into a concrete, readable failure.

### Rung 4 — Classify the failure

Map the real error from Rung 3 to one of these categories:

- **Missing binary** — the command interpreter or executable is not found at all (e.g., "command not found" / "is not recognized"). The launcher named in the spawn command is not on `PATH` or not installed. Install it or correct the command.
- **Spawn failure (binary present but not runnable)** — the binary is found but the process exits immediately or refuses to start: wrong runtime version, bad arguments, missing dependency, or a non-executable script. The process never reaches a working MCP handshake.
- **Auth failure** — the process starts but rejects credentials or reports an unauthorized/expired-token condition. The wiring is correct; the server cannot authenticate. Re-establish credentials through the proper channel (never echo them).
- **Wrong CLI version** — the Claude CLI is too old (or mismatched) to support the MCP feature or config shape in use. Confirm the installed CLI version and upgrade if it predates the capability you are relying on.

Once classified, the fix follows directly from the category. Re-run Rung 3 to confirm the manual spawn now succeeds before returning to the client.

## Concurrent-session clobber

The user dotfile is **rewritten on session events**. If two clients are open at once, one instance can overwrite the other's server entries when it saves — so a server you just registered can silently vanish, and `claude mcp list` (Rung 1) will then show it missing.

Before editing MCP configuration or registering a server, **close other client instances** so a single writer owns the file. After editing, re-run `claude mcp list` to confirm the entry survived.

## Restart discipline

After changing MCP configuration, **fully restart the client** rather than relying on an in-place reload or reconnect. MCP servers are spawned at startup; a partial reload may keep stale state or skip re-reading the dotfile/`.mcp.json`. A clean restart guarantees the new configuration is read and the server is spawned fresh. Verify with `claude mcp list` and by confirming the server's tools appear.

Restart discipline has a process-level half that is easy to miss. Plugin-reload cycles can leave **several stale server processes alive at once**, and a process's argument vector is fixed at spawn time — each survivor is frozen with the flags, paths, and environment it was launched with, no matter what the config file says now. A reconnect can bind to one of those survivors, so an edit to the launch flags looks like it had no effect however many times you reconnect.

Localize by listing the running server processes and reading their **command lines**: more than one instance of the same server, or an argv that does not match the current config, is the tell. Safe action: report the stale PIDs and their argv and propose stopping them so the next connect spawns a clean process — plus clearing any persistent-profile lock artifacts a killed browser server left behind (see `references/playwright-browser.md`). Note the MCP *connection* is owned by the client and cannot be restarted from a shell; killing the process only guarantees that whatever spawns next reads the current config.

## Platform note (labeled examples only)

The ladder is platform-neutral. Concrete launcher and path forms differ per OS; treat the following as illustrative only.

> Example (illustrative — not required): On Windows, the spawn command in a plugin's `.mcp.json` may invoke a `.cmd`/`.exe` launcher, and "missing binary" surfaces as `'<name>' is not recognized as an internal or external command`. On Unix-like systems the same condition surfaces as `command not found`, and the launcher is typically resolved from `PATH`.

The diagnostic *behavior* — list, read the spawn command, run it manually, classify — does not change across platforms. Only the literal command text and path syntax do.

## User MCP servers live in the user-level Claude JSON config — not a separate `mcp.json`

A recurring dead end: looking for a standalone `mcp.json` to hold **user-scope** servers. There
isn't one. User-scope MCP servers are stored as an `mcpServers` block **inside the single
user-level Claude JSON config in the home directory** (the same dotfile the CLI owns). Creating or
editing a separate `mcp.json` for user servers has no effect — the client never reads it for that
scope.

Decision rule restated for this trap:

- **User-scope** server missing → inspect the `mcpServers` object inside the **user-level Claude
  JSON config**, and prefer changing it through the `claude mcp` CLI rather than hand-editing.
- **Plugin-declared** server missing → inspect the plugin's own `.mcp.json` (that file *is* the
  right place for a plugin's servers; it is not the user-scope store).

If you cannot find a user server's entry, you are almost certainly reading the wrong file. Confirm
the user-level config path for the platform and look for the `mcpServers` key there before
concluding the server was never registered.

## Concurrent instances race-write the user config and drop each other's `mcpServers`

The "Concurrent-session clobber" above has a sharper edge worth stating explicitly: two Claude
Code instances open at once **race-write the same user-level JSON config**. Because each instance
serializes its whole in-memory view of the file on a session event, the last writer wins and can
**silently drop the `mcpServers` entries the other instance added** — there is no merge. A server
you just registered in one window disappears when the other window saves.

Localize before re-registering:

- If a previously-working server vanished from `claude mcp list` (Rung 1) with no config edit of
  your own, suspect a concurrent instance overwrote the file rather than a spawn fault.
- Confirm whether another instance is (or recently was) open.

Safe action: **close other instances so a single writer owns the config**, re-register the missing
server, then re-run `claude mcp list` to confirm the entry survived. Do not script repeated
re-writes while a second instance is live — they will keep clobbering each other.

## A plugin MCP failing with `-32000` almost always means its spawned CLI isn't runnable

A plugin MCP server that surfaces a JSON-RPC `-32000` (server/connection) error is rarely a
protocol bug — it almost always means **the CLI command the plugin spawns cannot actually run**:
the binary is missing from the host's `PATH`, the runtime version is wrong, an argument is bad, or
a wrapper script can't be executed at the no-shell spawn layer (see `references/lsp-node-spawn.md`
for the shim/`EINVAL` variant).

This is exactly Rungs 2–4 above, applied to a `-32000`:

1. Read the plugin's `.mcp.json` for the **literal** `command` + `args` of the failing server
   (Rung 2). Do not paraphrase.
2. **Run that exact command yourself in a plain terminal** (Rung 3). The client swallows the
   server's startup output; running it by hand converts the opaque `-32000` into the real,
   readable error.
3. Classify the real error (Rung 4): missing binary / spawn failure / auth / wrong version.

Safe action: report the manual-spawn output and the classification; propose the single matching
fix (correct the command path, install the binary, point at the real runtime + JS entrypoint).
Never echo any environment value the `.mcp.json` injects — report only its key names.

## "The app is running" is no evidence its MCP bridge is registered

When the MCP server is hosted by a desktop application (an IDE plugin, a local daemon with a UI), a specific trap sits in front of Rung 1: the app can be **installed, open, and listening on its port** while the client has no bridge to it at all. A port check proves only the *app* side. Registration is a separate, client-side fact, and nothing surfaces the gap — the tools are simply absent. A *different* integration from the same vendor makes it worse: an editor companion that supplies only diagnostics can be present and connected, which makes "the IDE is wired up" feel true while none of the app's real tools exist.

Verify from the tool list, not from the process list:

- Confirm the expected `mcp__…` tools are actually **callable in this session**. If the name is absent, the bridge was never registered — restarting the app adds nothing. (Any instruction that says to prefer a named tool is only satisfiable if that tool is in the list; check before assuming it is. Saying so up front rather than silently substituting a shell command is an agent-conduct rule — see `agent-safety-guards-plugin`'s `agent-safety` skill — not a diagnostic step.)
- Match the **transport** to what the endpoint actually speaks. An app-hosted endpoint commonly serves **SSE** on an `/sse` path; a `POST` to a streamable-HTTP path returning 404 is a transport mismatch, not a dead server. Registering with the wrong transport produces a server that lists but never connects.
- Register at **user scope** when the bridge should be available in every project. A project-scoped registration silently does not exist anywhere else, so the tools appear and disappear as the working directory changes.
- Remember an app-hosted server **only answers while the app is open**. Headless, cron, and CI sessions will never have those tools, so any rule depending on them needs a stated fallback.
- Registration takes effect only after a full client restart (see "Restart discipline" above) — registering mid-session and then concluding it did not work is a common false negative.

## A file reorganization can kill a whole server — the missing artifact is usually an empty directory

When **every** tool of one server disappears at once, immediately after a file move or migration,
the server is not misconfigured — it is dying during module load. The specific cause worth checking
first: a library that resolves a working directory **at import time** (`realpathSync` /
`resolve()` / an `os.path.realpath` on a mailbox, inbox, cache, or state directory) **throws if that
directory does not exist**, and the throw happens before any tool is registered, so the process
exits with every tool gone rather than one tool broken.

The directory goes missing because **a move driven by a file manifest silently drops empty
directories**. A manifest enumerates files; a directory holding no files is in no manifest entry, so
it is never recreated at the destination and never reported as skipped. The migration reports 100%
success.

Localize (read-only):

- Run the server's spawn command by hand (Rung 3) — an import-time resolve failure prints the exact
  path it could not resolve, which the client swallows entirely.
- Compare the directory *tree* before and after the move, not the file list. An empty directory is
  the only thing a file-count reconciliation cannot see.

Safe action: propose recreating the missing directories explicitly (keep a `.gitkeep`-style marker
so the next move carries them), then re-run the manual spawn before returning to the client.

### Three companions of the same migration

The same operation hides three more silent failures, and none of them raises:

- **Files moved under a dot-directory drop out of an index.** Indexers, search tools, and
  knowledge-base ingesters commonly ship a **built-in ignore set that excludes dot-directories**,
  and that set is applied before any project-level configuration is consulted. Documentation moved
  into one is still on disk and still openable, but is no longer retrievable — searches return
  nothing with no error. Keep indexed content outside built-in-ignored paths, or verify after the
  move that the content is still returned by a query, not merely present on disk.
- **Rewrite references from the manifest's old→new map, never by a blind prefix substitution.** A
  prefix `sed` flattens `<old-root>/<bucket>/x.md` to `<new-root>/x.md`, so the rewritten reference
  points at a path that exists nowhere while the file itself landed correctly in its real bucket. The
  manifest already holds the exact old→new pairing — use it.
- **A JavaScript `RegExp` carrying the `g` flag is STATEFUL across `.test()` calls.** `.test()`
  advances `lastIndex` on a match and resets it only on a miss, so reusing one `/…/g` regex for
  boolean checks returns **alternating** results — roughly half the real hits are reported as
  clean. A "0 stale references" verification built on one is not evidence of anything. Use a
  non-global regex (or reset `lastIndex` before each call) for boolean checks, and confirm a zero
  with a differently shaped command before believing it.

## For domain plugins: reference this ladder, do not copy it

Domain-specific plugins that ship their own MCP server should **point their troubleshooting docs at this ladder** rather than restating it. Copying the steps into each plugin leads to drift: when the diagnosis procedure improves, copies go stale. Keep the single owning copy here and link to it; add only the plugin-specific facts (the server name, the binary it spawns, and its auth channel) in the plugin's own docs.
