# Syncthing sync-operation diagnosis

Diagnostic ladders for the Syncthing failure classes that surface while syncing a **dev folder**
(source tree, dotfiles, notes) between machines: conflicts, delete-deadlocks, ignore files that
"don't take", stale error lists, a device that drops after an encryption change, and a folder
that parks just under 100%. Every section follows the same shape: **observe → localize → safe
action**. The observe/localize steps read the local Syncthing state through its REST API; the
mutating steps (revert, pause/resume, override, edit ignores) are called out explicitly and gated
behind "only once the diagnosis confirms it". Never blindly force-sync or hand-delete under a
running syncer.

All folder IDs, paths, ports, and device names below are **illustrative only**. Discover the real
values on the machine in front of you. The REST API key is a secret — read it to authenticate the
probe, but never echo it into the transcript or logs.

## Read-only probe surface — the local REST API

Syncthing exposes its full state on a loopback REST API (default `http://127.0.0.1:8384`). Every
diagnosis below is a `GET`; the key lives in the config and is required as an `X-API-Key` header.

```bash
# Locate the API key WITHOUT printing it. Config lives at:
#   Linux/macOS: ~/.local/state/syncthing/config.xml (older: ~/.config/syncthing/config.xml)
#   Windows:     %LOCALAPPDATA%\Syncthing\config.xml
# Read <gui><apikey>…</apikey> into a variable; never echo the variable.
KEY="$(sed -n 's:.*<apikey>\(.*\)</apikey>.*:\1:p' "<config.xml path>")"

# Per-folder sync status (the single most useful probe)
curl -sS -H "X-API-Key: $KEY" "http://127.0.0.1:8384/rest/db/status?folder=<folder-id>"

# The global-vs-local record for ONE file (is it flagged deleted? ignored? which version wins?)
curl -sS -H "X-API-Key: $KEY" \
  "http://127.0.0.1:8384/rest/db/file?folder=<folder-id>&file=<relative/path>"

# The folder's current error list (see "cached error list" below)
curl -sS -H "X-API-Key: $KEY" "http://127.0.0.1:8384/rest/folder/errors?folder=<folder-id>"
```

`/rest/db/status` returns the fields the rest of this doc keys on: `state` (e.g. `idle`,
`syncing`, `scanning`), `globalBytes` / `localBytes` / `inSyncBytes`, and the out-of-sync
breakdown — `needBytes`, `needDeletes`, `needDirectories`, `needFiles`, `needSymlinks`,
`needTotalItems`. The `need*` split is what distinguishes a real transfer stall from a pending
deletion.

## "95% synced, 0 bytes pending" is a pending deletion, not a stall

The completion percentage in the UI is **byte-weighted for downloads**. A pending *deletion* moves
zero bytes, so it never advances the percentage — the folder parks just under 100% with
`needBytes: 0` and looks wedged, when in fact it is waiting to *apply a delete* (often one blocked
by an open file handle, a permission, or an ignore rule).

Observe → localize:

```bash
curl -sS -H "X-API-Key: $KEY" "http://127.0.0.1:8384/rest/db/status?folder=<folder-id>"
```

- `needBytes: 0` **and** (`needDeletes > 0` or `needTotalItems > 0`) → this is a pending deletion
  or metadata change, **not** a transfer that stalled. Do not go hunting for a network/bandwidth
  fault.
- Identify the specific item with `/rest/db/file` to see whether the global version is flagged
  deleted while the local copy persists.

Safe action: find *why* the delete cannot apply (a file held open by an editor/venv process; a
read-only attribute; an ignore rule pinning the entry — see the delete-deadlock section). Resolve
the blocker; do **not** force the percentage by overriding or re-scanning blindly.

## Conflicts: there is no per-conflict "prefer remote" toggle

When both sides change the same file, Syncthing keeps both and renames the loser to
`<name>.sync-conflict-<date>-<time>-<deviceid>.<ext>`. There is **no** per-file "always take the
remote copy" button. Two mechanisms resolve conflicts, and you pick by *intent*:

1. **Manual, when either side might hold the wanted edit** — diff the `.sync-conflict-*` file
   against the live file, keep the correct content, and move the other to a **dated backup name**
   (not delete-in-place, which can re-trigger a conflict). This is the default for source trees.

   ```bash
   diff -u "<file>" "<file>.sync-conflict-<...>.<ext>"
   ```

2. **Make one device authoritative, when a whole folder should follow one side** — set the folder
   to **Receive Only** on the device that should **not** win, then use **Revert Local Changes** on
   that device to discard its local deviations and pull the other side's copy. "Receive only +
   revert" is the closest thing to "prefer the remote" and it is a *folder-level* choice, applied
   on the losing device — not a per-conflict flag.

Safe action: decide the direction first (which device is authoritative for this folder), then
apply receive-only+revert on the *other* device — or resolve file-by-file with a dated backup.
Never bulk-delete `.sync-conflict-*` files before diffing; each one is unmerged work.

## venv / node_modules delete-deadlock — ignore with a `(?d)` prefix, don't hand-delete

Syncing a build-artifact tree (`node_modules`, `.venv`, `__pycache__`, `target/`) is a mistake on
its own — thousands of churny files — but the trap is what happens when you try to *remove* one.
By default an ignored file is treated as immovable: it **blocks deletion of the directory that
contains it**. So a parent-directory delete propagated from a peer can never complete while an
ignored artifact still sits inside — a permanent "Failed to sync" / never-finishing deletion
deadlock.

Per the Syncthing ignore docs: *"A pattern beginning with a `(?d)` prefix enables removal of these
files if they are preventing directory deletion."*

Safe action:

- Add the artifact subtree to `.stignore` **with the `(?d)` prefix** so Syncthing is permitted to
  clean it up when a containing directory is being removed:

  ```gitignore
  (?d)node_modules
  (?d).venv
  (?d)__pycache__
  ```

- Do **not** hand-delete the artifact on each peer to "break" the deadlock — a manual delete races
  the syncer and manufactures more conflicts/errors. Let the `(?d)` rule authorize Syncthing to do
  the removal.

## `.stignore` does NOT sync — apply the pattern on every peer

The ignore file is **local device state**. Per the docs: *"The `.stignore` file itself will never
be synced to other devices, although it can `#include` files that _are_ synchronized between
devices."* So adding an ignore on one machine does nothing on the others — the peer keeps syncing
the artifact and can re-introduce the very files (or deadlock) you just cleared.

Observe → localize: a pattern you "already added" still shows the artifact syncing → check whether
the ignore exists on **the peer**, not just locally.

Safe action: replicate the same patterns in each device's `.stignore` (or factor shared rules into
an `#include`-d file that *is* synced, keeping only the `#include` line in each local `.stignore`).
Treat "did I set this on every peer?" as the first question, not the last.

## A folder's error list is CACHED until a pull — pause/resume, not rescan

The error list on a folder (`/rest/folder/errors`, and the UI's "Failed Items") is a **snapshot
from the last pull attempt**. A **rescan** re-hashes local files but does **not** re-attempt the
pull, so it leaves stale errors sitting there — you fix the underlying cause and the folder still
shows the old failure, making it look unresolved.

Observe → localize:

```bash
curl -sS -H "X-API-Key: $KEY" "http://127.0.0.1:8384/rest/folder/errors?folder=<folder-id>"
```

Safe action: to force a fresh pull and refresh the error list, **pause and resume the folder**
(which restarts its puller), rather than triggering a rescan. Only after the resume-driven pull
should you trust the error list as current.

## An encryption-type mismatch on one folder kills the WHOLE device link

Syncthing can share a folder to an untrusted device with encryption-at-rest. If the two sides
disagree on the encryption for **one** shared folder — one expecting plaintext where the other
sends encrypted, or a mismatched folder password — the **device connection itself is refused**,
not merely that one folder. The symptom is disproportionate: a single folder's misconfiguration
takes **every** folder shared with that peer offline, and the device shows as disconnected /
repeatedly reconnecting.

Observe → localize:

```bash
# Is the peer actually connected, and why not?
curl -sS -H "X-API-Key: $KEY" "http://127.0.0.1:8384/rest/system/connections"
curl -sS -H "X-API-Key: $KEY" "http://127.0.0.1:8384/rest/system/error"
```

- Device shows disconnected / flapping **right after** an encryption or password change on one
  shared folder → suspect the folder-level encryption mismatch, not the network.

Safe action: reconcile the encryption type/password on the affected folder so both sides agree
(plaintext↔plaintext, or the identical folder password on the encrypted side). This is a config
correction the user confirms; do not disable encryption or drop the device to "make it connect".

## Summary

| Symptom | Section | First safe move |
|---------|---------|-----------------|
| Folder parked <100%, `needBytes: 0` | 95%/0-bytes = pending deletion | read `/rest/db/status`; find why the delete can't apply |
| `.sync-conflict-*` files appearing | Conflicts | diff first; dated-backup the loser, or receive-only+revert the non-authoritative device |
| Directory delete never completes | venv/node_modules deadlock | add a `(?d)`-prefixed ignore; don't hand-delete |
| Ignore added but artifact still syncs | `.stignore` doesn't sync | replicate the pattern on every peer |
| Errors persist after fixing the cause | Cached error list | pause/resume the folder (not a rescan) |
| Peer disconnected after an encryption change | Encryption-type mismatch | reconcile the folder's encryption/password on both sides |
