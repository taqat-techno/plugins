# IDE remote-dev backend diagnosis

A JetBrains-style remote-development session (a thin client on the local machine driving a backend
that runs where the code lives — over SSH, inside WSL, or in a container) has a failure shape that
looks like networking but usually is not. This reference owns that one trap: a "Connecting…" hang
or a mid-session "No connection to the IDE backend" is, far more often than not, the **backend
JVM running out of heap** — not a broken tunnel. Diagnose the backend, not the wire.

This doc is generic: no specific IDE build, host, path, or project. Every concrete value below is
illustrative; discover the real ones on the machine in front of you. Never print secrets, tokens,
or environment-variable values while diagnosing.

## Symptom

Two presentations, same root cause:

- **Connect-time hang** — the client shows "Connecting…" / "Starting IDE backend…" indefinitely,
  or connects and then immediately drops. The handshake appears to stall at the network layer.
- **Mid-session drop** — a working session suddenly shows "No connection to the IDE backend" /
  "the backend has been disconnected," often right after opening a large file, triggering a
  re-index, or running a heavy refactor/inspection.

The misleading part: the client frames both as a *connection* problem, which steers people toward
ports, tunnels, firewalls, and SSH config — the wrong branch. The tell that it is **not** the wire:
the network probes pass (the port is reachable, the tunnel is up) yet the session still will not
hold.

## Why it looks like networking but is a backend OOM

The backend is a JVM. When it exhausts its max heap during indexing or analysis, it does **not**
cleanly close the connection — it thrashes in GC, becomes unresponsive, or the OOM leaves the
process half-dead. Crucially, **the dead/wedged backend keeps its listening ports open**, so the
thin client happily re-attaches to a process that can no longer service requests. The client then
reports a connection problem because, from its side, the backend stopped answering — but the real
event was a heap exhaustion, not a dropped packet.

This is why "restart the tunnel" and "re-forward the port" never stick: they reconnect the client
to the same wedged JVM.

## Read the backend log first — it is the source of truth

Do not theorize from the client UI. The backend writes its own log on the remote side; read it.

- Locate the backend log on the **remote/host side** (where the backend runs), not the thin
  client's local log. It lives under the IDE's per-user system/log directory on that host.
- Look for the unambiguous heap signals: `java.lang.OutOfMemoryError: Java heap space`,
  `GC overhead limit exceeded`, long "Garbage Collector" pauses, or a heap-dump-written line.
- Correlate the timestamp of the last log activity with the moment the client lost the connection.
  A heap error immediately before the disconnect confirms the branch.

```bash
# Illustrative only — discover the real path on the host.
# Tail the backend log on the remote side and look for heap signals:
tail -n 200 "<backend-system-dir>/log/idea.log" | grep -iE "outofmemory|gc overhead|heap"
```

If the log shows an OOM, this is the backend-heap branch — stop chasing networking.

## The fix is two-sided: raise the ceiling AND cut the working set

Raising the heap alone is a half-fix; a large enough project will re-exhaust any ceiling. Cutting
the indexed working set alone may not be enough for a genuinely big codebase. Do **both**, and
make the next OOM fail fast instead of wedging.

### 1. Raise the backend max heap

Increase the backend JVM's maximum heap (the `-Xmx` value) in the **backend's** VM options — this
is a different setting from the local client's memory, and editing the client's heap does nothing
for the backend. Choose a ceiling that fits the host's available RAM with headroom for the OS and
any other processes; do not set `-Xmx` larger than physical RAM can back.

### 2. Cut the indexed working set

The cheapest durable win is to stop the backend indexing things it never needs to analyze. Mark
generated, vendored, and machine-translation trees as **excluded** so they leave the index:

- Generated/build output, compiled assets, and caches.
- Vendored dependency directories that are not part of analysis.
- Large **i18n / translation** trees (many near-identical message files balloon the index for no
  analysis value).

Excluding these shrinks heap pressure and index time at once. This is a per-project configuration
the user applies; propose the specific directories to exclude based on what the project actually
contains — do not guess a directory that may hold real source.

### 3. Add `-XX:+ExitOnOutOfMemoryError` so a future OOM fails fast

Add `-XX:+ExitOnOutOfMemoryError` to the backend VM options. Without it, an OOM leaves the JVM
limping with its ports still open, so the client re-attaches to a zombie and you re-diagnose the
"connection" mystery from scratch. With it, the backend **exits immediately** on OOM — the ports
close, the client gets a clean "backend stopped" instead of an endless wedge, and the next launch
starts a fresh process. Failing fast turns a confusing hang into an honest, restartable error.

## Safe action and discipline

- **Diagnose, don't mutate.** Read the backend log and confirm the heap signal before changing
  anything. Present the VM-option edits (raise `-Xmx`, add `ExitOnOutOfMemoryError`) and the
  exclude list as changes for the **user** to apply to the **backend** config, one set at a time,
  then re-test.
- **Do not restart the tunnel/port as the fix** — that reconnects to the same wedged JVM and
  proves nothing. Restart the backend process only after the config change, so the new heap and
  exclusions take effect.
- **Right side, right setting.** Backend heap and excludes live on the host where the backend
  runs; the local client's memory settings are a separate, ineffective knob for this symptom.
- **Never** print secrets or environment values pulled from the host while reading logs or config.

## A CPU spike right after the backend starts is indexing, not a fault

A different symptom with the opposite verdict: if the only complaint is that the host's load
average jumps and every core pegs **immediately after the remote backend launches**, that is
first-time indexing of the whole project tree — normally stacked with language servers, completion
daemons, and whatever else the session starts at the same moment. It is transient. Load falls
steadily on its own within minutes as the index completes, and the backend log shows indexing
progress with **no heap error** — that pairing is the tell that separates it from the OOM branch
above.

Do not classify it as a fault, and do not kill or restart the backend to "fix" it: an interrupted
first index simply starts over on the next launch, so the intervention costs more than it saves.
Observe, name it as expected startup cost, and wait.

What legitimately reduces it is the same exclude list as above — **vendored, read-only source
trees** kept on disk for reference but never analyzed are usually the bulk of a first index.
Propose excluding them so the *next* startup is cheaper. That is a tuning change to hand to the
user, not a repair for a broken system.

## A process that vanishes leaving no crash artifact was killed from outside — not starved

Everything above is about a backend that *announces* its heap exhaustion in a log. The silent case
needs the opposite verdict, and it is easy to get backwards: an IDE or backend that **disappears
with no trace at all** — no crash dump, no OS application-error record, no JVM `hs_err_pid*.log`, no
`OutOfMemoryError` in its own log — is not evidence of memory pressure. It is evidence against it. A
JVM that dies of OOM leaves artifacts; a process terminated from outside (another program calling
`TerminateProcess`, a forced kill, a session or host teardown, an over-eager cleanup task) leaves
none. **The absence of the crash artifact is itself the finding** — it says "terminated
externally", so enumerate candidate killers instead of assuming exhaustion.

The circumstantial signals that pull people toward the memory theory are all weak:

- A Windows resource-exhaustion detection event (`RADAR_PRE_LEAK_64`) naming the process. That event
  names the **largest memory consumer while the system as a whole was under pressure** — a browser,
  a chat client, and the IDE take turns holding that title on ordinary days. It is not an accusation
  against the named process.
- A large configured `-Xmx` next to a modest amount of free RAM. A ceiling is not consumption: the
  heap can be nearly empty at the instant of death.

**Read the application's own telemetry before trusting an OS-level pressure heuristic.** JetBrains
platform IDEs write per-minute OpenTelemetry meter snapshots under the IDE's per-user log directory
(`<log-dir>/telemetry/open-telemetry-meters.*.json`, illustrative — discover the real path),
carrying `JVM.usedHeapBytes`, `JVM.maxHeapBytes`, `MEM.ramBytes`, `LowMemory.gcLoad` and
`LowMemory.gcOverloaded`. The snapshot written in the final minute before the kill settles the
question outright: a small used fraction of a large max heap, process RAM flat for the preceding
half hour, and GC essentially idle mean the process was **healthy at the instant it died** — and
every memory remedy (cutting `-Xmx`, resizing the VM's memory cap) is aimed at a cause that was
never there.

A second cheap check needs no telemetry: **did the shutdown hooks run?** Orphaned child processes
the app normally reaps on exit — language servers, helper daemons — accumulating one per lost
session prove the parent was killed rather than asked to exit, which rules out a clean
`System.exit()` and an OOM-triggered self-shutdown in a single observation.

When retrospective evidence is exhausted, stop theorizing and **instrument for the next
occurrence** rather than applying a speculative fix: arrange to capture the process's **exit code**
and its **parent chain** at death. A self-exit, an external `TerminateProcess`, and a forced kill
are distinguishable by exit code alone, which turns an unfalsifiable memory theory into one
observation you can actually classify.

Safe action: report "no crash artifact, therefore externally terminated" as the finding, propose the
telemetry read and the orphaned-child check as the next two read-only steps, and do **not** lower a
heap ceiling or resize a VM on circumstantial pressure signals — that mutates a working
configuration to treat a cause that has not been shown to exist.

## Cross-references

- `references/windows-wsl.md` — when the remote-dev backend runs inside WSL, the mirrored-mode /
  stale-port-forward and idle-stop sections explain genuine wire faults to rule out *after* the
  backend log shows no heap error.
- `references/lsp-node-spawn.md` — for a non-JVM language server that fails at spawn (a different
  class: launch-layer, not heap).
