# Syncthing sync-operation diagnosis

Diagnostic ladders for the Syncthing failure classes that surface while syncing a **dev folder**
(source tree, dotfiles, notes) between machines: conflicts, delete-deadlocks, ignore files that
"don't take", stale error lists, a device that drops after an encryption change, a peer whose
need list keeps growing without ever clearing, and a folder that parks just under 100%. Every section follows the same shape: **observe → localize → safe
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

# What a specific peer still needs from us — call this one BARE (see the gotcha below)
curl -sS -H "X-API-Key: $KEY" \
  "http://127.0.0.1:8384/rest/db/remoteneed?folder=<folder-id>&device=<device-id>"

# The connection event log — where a refused device link states its actual reason
curl -sS -H "X-API-Key: $KEY" "http://127.0.0.1:8384/rest/system/log"
```

`/rest/db/status` returns the fields the rest of this doc keys on: `state` (e.g. `idle`,
`syncing`, `scanning`), `globalBytes` / `localBytes` / `inSyncBytes`, the error counters
`errors` / `pullErrors`, and the out-of-sync breakdown — `needBytes`, `needDeletes`,
`needDirectories`, `needFiles`, `needSymlinks`, `needTotalItems`. The `need*` split is what
distinguishes a real transfer stall from a pending deletion. The same response also carries the
index cursors `sequence` (how far the local index has advanced) and `remoteSequence` (how much of
that index the peer has consumed) — the pair that separates a peer still ingesting from a peer
that is genuinely wedged.

**`/rest/db/remoteneed` pagination gotcha.** Called bare it answers `{files:[…]}`. Add a `page`
parameter (`&page=1&perpage=30`) and it silently switches to the legacy
`{progress:[],queued:[],rest:[]}` shape — all three empty **even when items are pending**, which
reads as "nothing stuck" and hides a real backlog. A `perpage` alone, without `page`, is safe.
When this probe disagrees with `/rest/db/status`, re-run it bare before believing it.

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
- An idle wire is the *expected* reading here, not corroboration of a stall: applying a deletion
  transfers no blocks, so no throughput ever appears no matter how long you watch. Diagnose the
  **peer that has to apply the delete**, not the transfer.
- Identify the specific item with `/rest/db/file` to see whether the global version is flagged
  deleted while the local copy persists.

Safe action: find *why* the delete cannot apply (a file held open by an editor/venv process; a
read-only attribute; an ignore rule pinning the entry — see the delete-deadlock section). Resolve
the blocker; do **not** force the percentage by overriding or re-scanning blindly. If the state
persists, the usual cause is that the other device keeps re-creating the very file it was asked to
remove — a running application rewriting its own session/log/transcript file inside the synced
tree is the classic case. That is fixed **on that machine** (stop the writer or ignore the path,
then rescan there), never by forcing the percentage from this side.

## A GROWING peer need-count is a busy peer, not a wedge — read the `sequence` gap

The intuitive stuck-detector — "the peer's need list keeps climbing and never clears an item" — is
wrong on its own, and so is elapsed time. After a bulk change (a large directory move, a mass
delete, a newly-ignored artifact tree) the peer must consume the *index updates queued ahead* of
those files before it can pull anything new, so its need count can climb monotonically for many
minutes while everything is healthy: `state=idle`, `needFiles: 0`, `errors: 0`, `pullErrors: 0` on
the sending side the whole time.

Observe → localize:

```bash
curl -sS -H "X-API-Key: $KEY" "http://127.0.0.1:8384/rest/db/status?folder=<folder-id>"
```

- `remoteSequence` trailing local `sequence` by roughly the size of the recent bulk change → the
  peer is **still ingesting the index**. Poll the gap; it closes on its own and the whole need
  list then transfers at once.
- Need list frozen **with `remoteSequence` already level with `sequence`**, `errors: 0` → that is
  the wedged signature, and only then does escalation apply.

Two measurement traps that each manufacture a false "stuck" verdict:

- **Byte counters in `/rest/system/connections` are per-DEVICE, not per-folder.** Watching
  `inBytesTotal`/`outBytesTotal` climb while the folder under investigation sits still proves
  nothing — the traffic may belong entirely to another folder shared with the same peer. Confirm
  attribution in `/rest/system/log` before reading throughput as progress on *this* folder.
- **`lastConnectionDurationS` in `/rest/stats/device` is not connection uptime.** A tiny value
  there is not evidence of a reconnect loop; read `startedAt` on the entries in
  `/rest/system/connections` for how long the current links have actually been up.

Safe action: while the gap is closing, **do nothing**. A pause/resume — or worse, an override —
issued during an active index ingestion restarts the exchange at best, and at worst makes the
local side authoritative and resurrects the peer's deletions. Verify completion on sustained
samples (`completion: 100`, remote need items `0`, `globalFiles == inSyncFiles`), not one reading.

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

   Triage by **content**, before choosing a winner — most conflict files turn out to have nothing
   worth accepting:

   - **Per-machine logs / state files** (append-only session or activity logs): the live file is
     usually a strict newer superset of the conflict copy. Keep the live file.
   - **Stale version-control internals** copied in from a retired or re-imaged device: promoting
     one of these over the live repo metadata **corrupts the repository**. Never accept a VCS
     internal from a conflict copy — re-derive it from the repo instead.
   - **Expired version-history copies** kept by the versioning feature: these age out on their own
     retention schedule and are not conflicts at all.

   Check the **live sync index first** (`/rest/db/status`): if the folder already reports nothing
   pending, the merge has resolved globally and the remaining `.sync-conflict-*` files are litter,
   not a decision waiting on you. Conflict litter on the *other* machine is invisible from here
   (the `*.sync-conflict-*` ignore pattern stops the copies propagating), so clean each device on
   its own.

2. **Make one device authoritative, when a whole folder should follow one side** — set the folder
   to **Receive Only** on the device that should **not** win, then use **Revert Local Changes** on
   that device to discard its local deviations and pull the other side's copy. "Receive only +
   revert" is the closest thing to "prefer the remote" and it is a *folder-level* choice, applied
   on the losing device — not a per-conflict flag.

   Through the REST API the same sequence is: `PATCH /rest/config/folders/<folder-id>` with
   `{"type":"receiveonly"}` → let it pull → `POST /rest/db/revert?folder=<folder-id>` → `PATCH`
   the type back to `"sendreceive"` for ongoing two-way sync (or leave it receive-only if that
   device is a permanent follower). **`needBytes` going UP after the type change is the mechanism
   working, not a fault** — the folder is reclassifying every locally-divergent file as "pull the
   remote version". Staggered versioning keeps the superseded local copies recoverable for the
   retention window.

   Hazard: doing this to a folder that holds the *running* tool's own live files — a session
   transcript, a lock or cleanup marker, a per-session scratch file — will always show those as
   locally-changed, because the process is writing them while you look. They are ephemera that
   regenerate instantly, not deviations; never revert them chasing a zero counter.

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

Observe → localize — confirm the diagnosis on the index before editing any ignore file:

```bash
# the directory the error names
curl -sS -H "X-API-Key: $KEY" \
  "http://127.0.0.1:8384/rest/db/file?folder=<folder-id>&file=<dir/path>"
# a file still living inside it
curl -sS -H "X-API-Key: $KEY" \
  "http://127.0.0.1:8384/rest/db/file?folder=<folder-id>&file=<dir/path/child>"
```

`global.deleted: true` on the directory while a **child** reports `global.deleted: false` **is**
the signature: a self-contradictory global index that Syncthing can never reconcile, so it refuses
the delete, retries on a backoff, and never self-heals. Any package manager that rewrites a
dependency tree (an install/uninstall run) can leave exactly these directory tombstones with live
children. The error wording narrows the sub-case — *"is not empty"* / *"contains ignored files"*
points at this deadlock, while *"contains **changed** files"* points at entries the local platform
cannot index at all — a distinct sub-case, covered at the end of this section.

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
- Do **not** reach for a plain (un-prefixed) ignore and expect it to clear the error: a plain
  pattern only takes the subtree out of scope for *future* transfers, it does not grant permission
  to remove already-synced entries that are blocking a parent delete. The `(?d)` prefix is the
  part that resolves the deadlock.
- Hand-deleting also fixes only the *instance*, not the *class* — the tombstones reappear on the
  next dependency install. Ignoring the whole subtree makes Syncthing **skip** the delete rather
  than execute it, so the local files stay on disk. Verify with `pullErrors` dropping to `0`
  **and** a file-count/byte check proving nothing was removed.

**Sub-case — `delete dir: … contains changed files`.** Same shape, different cause: entries the
local platform cannot represent in the index. On Windows, symlinked cache entries (a model or
package cache whose files are links into a shared blob store) are unindexable — they show zero
length with a link attribute, and `/rest/db/file` answers *"No such object in the index"* for
them. Syncthing cannot verify the directory is safe to empty, so it refuses forever on a
multi-minute backoff. The remedy is the same `(?d)`-prefixed ignore of the cache subtree; the
verification differs — see the cached-error-list section, because this one will not clear on a
rescan.

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

### Comments are `//` — a bare `#` line is a PATTERN

Syncthing's ignore syntax comments with `//`. `#` is **not** a comment character: `#include` is a real
directive (above), and any other `#`-prefixed line is parsed as an ordinary **pattern**. A line like
`# vendored deps` therefore silently becomes a rule matching a path starting `# vendored deps` — inert
only for as long as nothing happens to match it, and actively misleading to anyone reading the file.
Mixed `#`/`//` styles inside one `.stignore` are common and worth normalising to `//` on sight.

Two more properties that change how you edit the file:

- Prefix an entry with `(?d)` for a tree Syncthing is allowed to **delete** — the right marker for a
  vendored or generated directory that is fully reproducible from a lock file, e.g.
  `(?d)**/<vendored-dir>`. Without it, the delete-deadlock in the section above is what you get.
- A `.stignore` at a **workspace root governs every project beneath it**. Editing it is a cross-project
  change, not a local tweak: back the file up first and get explicit approval before changing it.

Replicating live `.git` directories is worth avoiding on its own — replication mid-operation can corrupt
git objects, and a reproducible checkout should be re-fetched on the second machine rather than synced.

## A folder's error list is CACHED until a pull — pause/resume, not rescan

The error list on a folder (`/rest/folder/errors`, and the UI's "Failed Items") is a **snapshot
from the last pull attempt**. A **rescan** re-hashes local files but does **not** re-attempt the
pull, so it leaves stale errors sitting there — you fix the underlying cause and the folder still
shows the old failure, making it look unresolved.

Scanning and pulling are **separate phases**: only a *pull* re-runs the failing operation and
rewrites the error list. So an ignore or config change made to unblock a folder can be entirely
correct — and verifiably loaded, e.g. `GET /rest/db/ignores` showing the parsed pattern — while
the error count sits unchanged through a full scan of a large tree and many minutes of
`state=scanning`. Judging the fix on the error count before a pull cycle has run yields a false
"it didn't work" verdict, and both tempting escalations from there are harmful: stacking more
config changes on top, or forcing `/rest/db/override`, which makes the local side authoritative
and **resurrects the peer's deletions**.

Observe → localize:

```bash
curl -sS -H "X-API-Key: $KEY" "http://127.0.0.1:8384/rest/folder/errors?folder=<folder-id>"
# what the folder actually parsed from the ignore file
curl -sS -H "X-API-Key: $KEY" "http://127.0.0.1:8384/rest/db/ignores?folder=<folder-id>"
```

Safe action: to force a fresh pull and refresh the error list, **pause and resume the folder**
(`PATCH /rest/config/folders/<folder-id>` `{"paused":true}` then `{"paused":false}`, or the UI
equivalent) — which restarts its puller — rather than triggering a rescan. Then judge the outcome
on `/rest/db/status` (`state=idle`, `errors: 0`, `pullErrors: 0`, `needFiles: 0`,
`needDeletes: 0`), **never on the error list alone**; the status counters are recomputed by the
pull, the list is a display of what the last one found.

## An encryption-type mismatch on one folder kills the WHOLE device link

Syncthing can share a folder to an untrusted device with encryption-at-rest. If the two sides
disagree on the encryption for **one** shared folder — one expecting plaintext where the other
sends encrypted, or a mismatched folder password — the **device connection itself is refused**,
not merely that one folder. The symptom is disproportionate: a single folder's misconfiguration
takes **every** folder shared with that peer offline, and the device shows as disconnected /
repeatedly reconnecting.

The diagnostic trap follows from that breadth: the symptom presents as a transport problem — peer
powered on and reachable over the LAN or an overlay network, the sync port open both ways, and yet
"Disconnected / N% out of sync" with a reconnect flap every few seconds. Nothing in that picture
points at one folder's config, so the investigation goes to firewalls, discovery and the overlay
network and stays there.

Observe → localize:

```bash
# Is the peer actually connected, and why not?
curl -sS -H "X-API-Key: $KEY" "http://127.0.0.1:8384/rest/system/connections"
# The real per-attempt reason — filter on the peer's device id
curl -sS -H "X-API-Key: $KEY" "http://127.0.0.1:8384/rest/system/log"
```

- `/rest/system/log` carries the actual handshake failure, e.g. *"handling cluster-config: remote
  expects to exchange plain data, but is configured to be encrypted"*. **Read the log before
  blaming the network** — this is the single probe that names the culprit.
- `/rest/system/error` is typically **EMPTY** for this failure: a refused device link is a
  connection event, not a system error, so an empty error endpoint is not evidence of health.
- `/rest/system/connections` shows the peer `connected: false` with an empty address — which looks
  identical to a firewall/discovery problem and tells you nothing about the cause.
- Device shows disconnected / flapping **right after** an encryption or password change on one
  shared folder → suspect the folder-level encryption mismatch, not the network.

Safe action: reconcile the encryption type/password on the affected folder so both sides agree
(plaintext↔plaintext, or the identical folder password on the encrypted side). **Pausing** the
offending folder on the encrypted side is the least invasive way to restore the link — a paused
folder is dropped from the cluster-config check — and it buys time to fix the config properly.
This is a config correction the user confirms; do not disable encryption or drop the device to
"make it connect". Verify on the log: the `cluster-config: remote expects…` lines must stop, and
only benign reconnect churn (`reason: replacing connection`, from multipath) should remain.

## Summary

| Symptom | Section | First safe move |
|---------|---------|-----------------|
| Folder parked <100%, `needBytes: 0` | 95%/0-bytes = pending deletion | read `/rest/db/status`; find why the delete can't apply |
| Peer need-count climbing for minutes, never clearing | Growing need-count = busy peer | compare `remoteSequence` against local `sequence`; wait while the gap closes |
| `.sync-conflict-*` files appearing | Conflicts | diff first; dated-backup the loser, or receive-only+revert the non-authoritative device |
| Directory delete never completes | venv/node_modules deadlock | add a `(?d)`-prefixed ignore; don't hand-delete |
| Ignore added but artifact still syncs | `.stignore` doesn't sync | replicate the pattern on every peer |
| Errors persist after fixing the cause | Cached error list | pause/resume the folder (not a rescan), then judge on `/rest/db/status` |
| Peer disconnected after an encryption change | Encryption-type mismatch | reconcile the folder's encryption/password on both sides |
| EVERY folder to one peer shows disconnected, network probes pass | Encryption-type mismatch | read `/rest/system/log` for the cluster-config error before touching the network |
| `remoteneed` reports nothing while items are clearly pending | REST probe surface | re-call it **without** a `page` parameter |
