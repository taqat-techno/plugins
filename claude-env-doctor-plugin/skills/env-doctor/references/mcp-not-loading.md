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

## For domain plugins: reference this ladder, do not copy it

Domain-specific plugins that ship their own MCP server should **point their troubleshooting docs at this ladder** rather than restating it. Copying the steps into each plugin leads to drift: when the diagnosis procedure improves, copies go stale. Keep the single owning copy here and link to it; add only the plugin-specific facts (the server name, the binary it spawns, and its auth channel) in the plugin's own docs.
