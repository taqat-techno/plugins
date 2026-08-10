# Windows / WSL environment diagnosis

Diagnostic ladders for the most common Windows + WSL (Windows Subsystem for Linux) failure
classes. Every section follows the same shape: **observe → localize → safe action**. Diagnosis
commands are read-only; mutating commands are called out explicitly and gated behind a clear
"only if the diagnosis confirms it" condition. Never blindly mutate the environment.

All concrete distro names, IPs, ports, hostnames, and interface metrics shown below are
**illustrative only**. Discover the real values on the machine in front of you; never hard-code
them into plugin behavior. Never print secrets, tokens, or environment-variable values.

## WSL distro discovery — use the exact reported name

An unqualified `wsl` invocation runs the *default* distro, which may not be the one the user
means. Multiple distros can be installed side by side, and aliases are not guaranteed to resolve
the way you expect. Enumerate first, then address distros by their exact reported name.

List installed distros, their state, and which one is default:

```powershell
wsl --list --verbose
```

The output lists each distro's `NAME`, `STATE` (Running / Stopped), and `VERSION` (1 or 2). The
default distro is marked with `*`.

> Example (illustrative — not required):
>
> ```text
>   NAME              STATE           VERSION
> * Distro-A          Running         2
>   Distro-B          Stopped         2
> ```

Run a command in a specific distro using the **exact** name from the list:

```powershell
wsl --distribution "<EXACT-NAME-FROM-LIST>" -- <command>
```

Diagnosis rules:

- Do not assume the bare alias (`wsl -- <cmd>`) targets the distro the user is working in —
  confirm against the default marker first.
- Names are case-sensitive in some WSL builds; copy the name verbatim from `--list --verbose`.
- A `STATE` of `Stopped` is normal for an idle distro and is not itself a fault.

## DNS-vs-TCP isolation ladder for "can't reach an external API"

"Can't reach the API" can break at any of three layers: IP routing, TCP transport, or DNS name
resolution. Walk the layers from the bottom up; the point where behavior diverges is the broken
layer. Run these from **inside** the affected WSL distro, since that is usually where the app runs.

### Step 1 — IP routing (ping a known-good IP)

```bash
ping -c 3 <PUBLIC-IP>
```

- Replies → routing and basic egress work; move to Step 2.
- No replies → routing/egress problem (interface down, no route, firewall dropping ICMP). Some
  networks block ICMP even when TCP works, so do not stop here on failure — corroborate with
  Step 2 before concluding.

### Step 2 — TCP transport (raw connect to host:port)

Open a TCP connection to the service port, bypassing any application logic:

```bash
# Bash / WSL
timeout 5 bash -c '</dev/tcp/<HOST>/<PORT>' && echo "tcp-open" || echo "tcp-failed"
```

```powershell
# Windows side, for comparison
Test-NetConnection -ComputerName <HOST> -Port <PORT>
```

- Connects → transport is fine; if the app still fails, the fault is higher up (DNS, TLS, or app
  config). Continue to Step 3.
- Connection refused → something answered but rejected the port (wrong port, service down).
- Connection times out → packets are being dropped (firewall, network path, or wrong address).

### Step 3 — DNS layer (resolve-by-name vs connect-by-IP)

Compare a fetch that must resolve the hostname against the same fetch pinned to a literal IP. If
by-IP succeeds but by-name fails, DNS resolution is the broken layer.

```bash
# By name — exercises the resolver
curl -sS -o /dev/null -w "%{http_code}\n" https://<HOST>/<path>

# By IP — skips the resolver (send the hostname as a Host header / SNI)
curl -sS -o /dev/null -w "%{http_code}\n" --resolve <HOST>:443:<PUBLIC-IP> https://<HOST>/<path>
```

Also check what the resolver actually returns:

```bash
getent hosts <HOST>     # uses the system resolver path
nslookup <HOST>         # queries DNS directly
```

Interpretation:

| By name | By IP | Localized layer |
|---------|-------|-----------------|
| fails   | works | DNS resolution (see VPN/DNS section) |
| fails   | fails | routing/transport (re-check Steps 1–2) |
| works   | works | network healthy — fault is in app/TLS/auth config |

Safe action: this ladder only reads. Do not edit `/etc/resolv.conf`, firewall rules, or routes
until a specific layer is confirmed broken — and even then, back up the file first.

## VPN / DNS conflict

Multiple active VPN tunnels (or a corporate VPN plus a personal one) can each install their own
DNS servers. If a tunnel's interface sits at a **low metric** (higher priority), Windows and WSL
may send public-name lookups down that tunnel, where they are dropped or time out — even though
unrelated traffic still flows.

Diagnose by comparing resolution latency against a known public resolver versus the system
default:

```powershell
# Inspect interface metrics — lower metric = higher priority
Get-NetIPInterface | Sort-Object InterfaceMetric |
  Select-Object InterfaceAlias, AddressFamily, InterfaceMetric, ConnectionState

# See which DNS servers each interface advertises
Get-DnsClientServerAddress | Select-Object InterfaceAlias, ServerAddresses

# Compare latency: system default vs an explicit public resolver
Measure-Command { Resolve-DnsName <HOST> } | Select-Object TotalMilliseconds
Measure-Command { Resolve-DnsName <HOST> -Server <PUBLIC-RESOLVER-IP> } |
  Select-Object TotalMilliseconds
```

From inside WSL:

```bash
time getent hosts <HOST>
time nslookup <HOST> <PUBLIC-RESOLVER-IP>
```

Interpretation:

- System default is slow / times out **and** the explicit public resolver is fast → a tunnel's
  DNS is intercepting public-name resolution. The offending interface is typically the lowest-metric
  VPN adapter in the `Get-NetIPInterface` listing.
- Both are slow → the problem is broader than DNS (re-run the isolation ladder above).

Safe action: report the conflicting interface and its metric to the user. The fix
(disconnecting a tunnel, reordering interface metrics, or scoping DNS) is the user's call — do
not change interface metrics, disconnect VPNs, or rewrite DNS settings automatically.

## WSL HCS connection-timeout escalation ladder

Symptoms like the shell hanging, errors mentioning the Host Compute Service (HCS), or
`The operation timed out because a response was not received` usually mean the WSL VM or its
backing service is wedged. Escalate one rung at a time and **stop at the first rung that restores
a working shell** — each rung is more disruptive than the last.

### Rung 1 — terminate just the affected distro

```powershell
wsl --terminate "<EXACT-DISTRO-NAME>"
```

Then try to open a shell in that distro again. Least disruptive: leaves other distros and the VM
running.

### Rung 2 — shut down the whole WSL VM

```powershell
wsl --shutdown
```

Stops every distro and the lightweight utility VM. The next `wsl` invocation cold-starts it.
More disruptive — affects all distros — but does not touch Windows services.

### Rung 3 — restart the WSL service (requires elevation)

If the VM will not come back, restart the LxssManager service from an **elevated** (Administrator)
PowerShell:

```powershell
# Run in an elevated PowerShell
Restart-Service LxssManager
```

This needs admin rights; surface that requirement to the user rather than attempting silent
elevation.

### Rung 4 — reboot Windows

Last resort. A reboot clears kernel-level virtualization and networking state that the rungs
above cannot. Only suggest this after rungs 1–3 fail.

Safe action: present the ladder and let the user confirm before each disruptive rung. Do not chain
`--shutdown`, a service restart, and a reboot in one go — that defeats the point of localizing
which rung was actually needed.

## localhost-forwarding masquerade

WSL forwards `localhost` between Windows and the distro. If a service was **migrated from WSL to
native Windows** (or vice versa) but the old instance is still running, requests to
`localhost:<PORT>` may be silently answered by the stale instance via this forwarding — so a
"fixed" service appears unchanged, or a new version's behavior never takes effect.

Diagnose by checking **both** sides for a listener on the same port:

```powershell
# Windows side — what is listening, and which PID owns it
Get-NetTCPConnection -State Listen -LocalPort <PORT> |
  Select-Object LocalAddress, LocalPort, OwningProcess
```

```bash
# WSL side — is something still bound to the same port inside the distro?
ss -ltnp | grep ":<PORT>"
```

If a listener exists on the WSL side for a service you believe now runs natively on Windows, the
WSL instance is the likely responder.

Safe action: **stop the WSL-side service first**, then re-test against `localhost:<PORT>`. Stopping
the stale instance is the targeted fix; killing the Windows-side process or rebinding ports blindly
risks taking down the instance you actually want. Identify the owning process before stopping
anything, and confirm with the user which instance is authoritative.

## WSL ↔ Windows file-transfer caveats

There are two paths between the two filesystems, and they are not equivalent for bulk transfers:

1. **From inside WSL to the mounted Windows drive** — e.g. copying to `/mnt/<drive>/...` from a
   shell running in the distro.
2. **From Windows to the WSL UNC mount** — e.g. copying via `\\wsl$\<distro>\...` or
   `\\wsl.localhost\<distro>\...` in Explorer or a Windows tool.

For **many small files**, prefer path 1 (copy from inside WSL to the mounted drive). The UNC mount
adds per-file network-protocol (9P) overhead that makes large counts of small files dramatically
slower and more failure-prone than copying within the WSL-native path.

Additional caveats:

- Some Windows copy tools mangle or normalize POSIX paths (case-folding, symlink handling,
  permission/ownership loss) when writing across the boundary. Prefer WSL-native tools
  (`cp`, `rsync`, `tar`) for trees that rely on case-sensitivity, symlinks, or executable bits.
- Verify a transfer by comparing file counts and a checksum sample rather than trusting a copy
  tool's "complete" message — boundary copies can drop or alter files quietly.

> Example (illustrative — not required): bulk-copying a dependency tree of tens of thousands of
> small files completed in minutes when run as `cp -a` from inside the distro to `/mnt/<drive>/...`,
> versus stalling for a long time over the `\\wsl$\` UNC mount.

Safe action: recommend the WSL-native copy path for small-file-heavy transfers and a post-copy
verification step. Do not delete the source until the destination is verified.

## Bash `/tmp` maps to a Windows temp dir — write artifacts to an explicit path

A common surprise when an agent runs commands through a Git-Bash-style shell on Windows (not
inside a WSL distro): the shell's `/tmp` is **not** a Linux tmpfs. It is silently mapped onto the
Windows per-user temp directory (the `LocalAppData` Temp area). A file the shell writes to
`/tmp/foo.txt` lands at a Windows path, and the Read tool — which resolves real OS paths — cannot
open it as `/tmp/foo.txt`. The artifact "vanishes" even though the write succeeded.

Observe → localize:

- A command reports it wrote `/tmp/<name>`, but a Read of `/tmp/<name>` (or of the literal
  Windows temp path) fails or returns nothing.
- Resolve where `/tmp` actually points before concluding the write failed:

```bash
# What the shell thinks /tmp is, and where it physically lands
echo "$TMPDIR"
cd /tmp && pwd -W   # pwd -W prints the Windows path form under Git Bash
```

Safe action: **have the command write its artifact to an explicit, agreed absolute path** (a
project-relative path, or a Windows path you then Read directly) rather than to `/tmp`. Do not
assume `/tmp` is Read-tool-resolvable on a Windows Git-Bash shell. This is a path-mapping quirk,
not a missing-file fault — no mutation is warranted.

## Confirm an "empty" content-search with a direct Read on an absolute path

A content search (ripgrep-style) that returns zero hits is **not proof the string is absent**.
On Windows the searched glob may exclude the file, the file may be outside the search root, an
encoding/BOM may defeat the matcher, or the path may sit behind a boundary the indexer skipped.
Treating an empty search as "the code doesn't contain X" sends the whole diagnosis down the wrong
branch.

Observe → localize → safe action:

- When a search you expected to match comes back empty, **corroborate with a direct Read of the
  specific absolute path** before believing the negative. The Read either confirms the string is
  genuinely absent or exposes why the search missed it (wrong root, excluded glob, encoding).
- Only after the direct Read agrees should you treat the symptom as "string truly absent." This
  is read-only confirmation; never edit or regenerate a file to "make the search work."
- The mirror-image trap: a **positive** hit can be corrupted too. In an interactive terminal a
  content search highlights matches by wrapping them in terminal escape sequences; captured back
  through a tty, the highlighted substring can come through mangled — a multi-term or alternation
  pattern can render `ready/occupied/vacant` as a two-character fragment. The match itself is real,
  but the text displayed *for* it is not the text in the file. So never quote interactive search
  output verbatim for a **load-bearing identifier** — a field name, an enum value, a path, a config
  key — that will go into a report, a patch, or a command. Re-run with color disabled
  (`rg --color=never`) or Read the file at the matched line before using the string. Non-interactive
  callers (subagents, scripts with no tty) get uncolored output and are unaffected, which is why
  this only bites in the hands-on shell.

## WSL mirrored networking + persisted IDE port-forward = squat / feedback loop

WSL2 *mirrored* networking mode shares the Windows network namespace with the distro, so a port a
dev server binds **inside** WSL is reachable on Windows `localhost:<PORT>` with no manual
forwarding. If an IDE (or a previous nat-mode setup) has *also* persisted an explicit port-forward
for that same port, the forward now squats on the port on the Windows side — so the IDE's stale
forwarder answers `localhost:<PORT>` instead of the live in-WSL server, or the two fight in a
bind/forward feedback loop and the port behaves erratically.

This is a cousin of the localhost-masquerade above, specific to the mirrored-mode + stale-forward
combination. Diagnose by checking the networking mode and who owns the port on the Windows side:

```powershell
# Is mirrored mode actually in effect? (read the effective config)
Get-Content "$env:USERPROFILE\.wslconfig" | Select-String -Pattern 'networkingMode'

# Who is listening on the port on the Windows side, and which PID owns it?
Get-NetTCPConnection -State Listen -LocalPort <PORT> |
  Select-Object LocalAddress, LocalPort, OwningProcess
```

If mirrored mode is on **and** a separate IDE/forwarder PID owns the port (distinct from the WSL
relay), the persisted forward is redundant and is the likely squatter.

Safe action: **clear the stale IDE port-forward** (remove that one forwarding rule in the IDE's
config) so the mirrored-mode pass-through reaches the live in-WSL server directly. Identify the
owning PID first; do not blanket-kill listeners or flip the networking mode mid-diagnosis — both
are more disruptive than removing the one redundant forward.

## `EADDRINUSE` inside the distro while `ss` / `fuser` show the port free

The mirrored-mode port collision has a general form worth recognizing on its own, because all the
evidence for it sits on the **other** side of the boundary. A process inside WSL2 fails to bind with
`bind: Address already in use`, yet `ss -ltnp` and `fuser` in that same distro report nothing on the
port. The Linux side really is clean: a **Windows** process is already listening on
`127.0.0.1:<PORT>`, and because WSL2 shares/forwards the loopback, that listener consumes the port
for the Linux bind too. The usual squatter is a desktop application's helper process — an IDE's
client or backend, a language-server host, a dev server from a session the user believes is closed —
which is why nobody suspects it: the app that owns the port is not the thing being started.

The trap is that every instinct points inward — a leftover Linux process, a duplicated systemd unit,
a config that declares the port twice. All three of those probes come back clean and the diagnosis
stalls, because the conflict is **invisible from inside the distro**.

Observe → localize:

```bash
# 1. Is the Linux side genuinely clean? (expect: no rows)
ss -ltnp | grep ":<PORT>"

# 2. Bare-socket control — does the bind fail even with no application involved?
python3 -c "import socket;s=socket.socket();s.bind(('127.0.0.1',<PORT>));print('bound')"

# 3. Port control — run the identical bind against a neighbouring free port.
#    If <PORT>+1 binds fine, the port is the variable, not the code or the config.
```

```powershell
# 4. Who owns it on the WINDOWS side? This is where the answer is.
Get-NetTCPConnection -State Listen -LocalPort <PORT> |
  Select-Object LocalAddress, LocalPort, OwningProcess
Get-Process -Id <PID-from-above> | Select-Object Id, ProcessName, Path
```

Clean Linux probes **plus** a failing bare-socket bind **plus** a neighbouring port that binds
**plus** a Windows PID holding the port is what confirms it; no single one of those does.

Safe action: name the owning Windows process and its PID, and let the user choose between closing it
and moving the in-WSL service to a free port. Do not kill a desktop application's process to free a
dev port, and do not rebind blindly. If the squatter turns out to be an IDE's persisted forward
rather than a real server, the mirrored-forward section above is the more precise fix; the in-WSL
`sshd` section below is another instance of this same collision.

## Mirrored-mode DNS can hang when a VPN mesh + its DNS overlap

A second mirrored-mode pitfall: because the distro shares the Windows DNS path, a VPN mesh client
running on Windows (one that installs its own overlay resolver / split-DNS for a private name
suffix) can make name resolution **inside WSL hang** when the mesh's DNS and the system DNS
overlap or contend. Public lookups stall or time out even though connectivity is otherwise fine —
the in-WSL resolver is waiting on the contended overlay resolver.

This overlaps the VPN/DNS-conflict section above; the mirrored-mode twist is that WSL inherits the
contention rather than having its own resolver. Diagnose with the same resolver-latency comparison
(system default vs. an explicit public resolver) from inside the distro, and confirm mirrored mode
is in effect (see the `networkingMode` check above).

Safe action: report the overlapping mesh-DNS interface and the mirrored-mode dependency to the
user. The remedy (scoping the mesh's DNS to its private suffix only, or temporarily disconnecting
the mesh to confirm) is the user's call — do not disconnect the VPN mesh or rewrite DNS scoping
automatically.

## nat-mode idle-stops the WSL VM

In the default *nat* networking mode the lightweight WSL utility VM can be **idle-stopped** when
no distro shell is active, releasing its virtual NIC and IP. A long-lived connection that targeted
the old VM IP then drops, and the first reconnect pays a cold-start penalty while the VM and its
NIC come back. This looks like an intermittent network fault but is the VM lifecycle, not a broken
route.

Observe → localize:

- `wsl --list --verbose` shows the distro `Stopped` between uses; the VM IP changes across
  cold-starts.
- Mirrored mode does not exhibit the IP-churn variant (it uses the Windows namespace), so the
  symptom appearing only in nat mode is itself a localizing signal.

Safe action: prefer to **address services by name / the current relayed `localhost`** rather than
pinning a captured VM IP, and expect a cold-start delay after idle. If stable in-WSL service
reachability across idle periods is required, switching to mirrored mode is an option to *propose*
(it changes networking semantics) — never flip `.wslconfig` automatically; surface the trade-off
and let the user decide.

## A WSL VM restart silently expires an earlier reachability verdict

Mirrored-mode pass-through and the Hyper-V firewall rules that govern it are re-established when
the WSL utility VM boots. So a "Windows cannot reach the in-WSL listener" finding is only true of
**the VM generation you tested**: an idle-stop, a `wsl --shutdown`, a distro restart, or a Windows
resume between turns can rebuild that path and make the port reachable with no action from anyone.
Nothing announces the change — the earlier failure just quietly stops being true.

Consequences for how the finding is reported:

- Treat a reachability result as a timestamped observation. Before **repeating** "Windows can't
  reach `<PORT>`" in a later turn, re-run the one-line probe (`Test-NetConnection 127.0.0.1 -Port
  <PORT> -InformationLevel Quiet`, or a plain HTTP fetch of the service's health path).
- This matters most before recommending an **elevated** remedy — an admin-only firewall rule, a
  `.wslconfig` change. Sending the user after admin rights for a wall that is no longer there costs
  them more than the two seconds the re-probe would have cost.
- Conversely, a success is just as perishable: if the VM idle-stops after your probe, the next call
  pays a cold start. Re-probe rather than reasoning from the earlier result in either direction.

## Windows git "dubious ownership" = the repo dir is owned by `BUILTIN\Administrators`

`fatal: detected dubious ownership in repository at '<dir>'` on Windows means git's safe-directory
guard (a CVE-2022-24765 mitigation) sees the repository directory owned by an identity **other than
the current user** — on Windows that owner is almost always `BUILTIN\Administrators`. It happens
when the folder was created/cloned by an elevated process, lives at a drive root, or was laid down
by an installer or a service, so its owner is the Administrators group rather than you.

Observe → localize (read-only — just inspect the owner):

```powershell
# The owner is the whole story. If it reads BUILTIN\Administrators, that's the cause.
(Get-Acl "<dir>").Owner
```

- Owner is `BUILTIN\Administrators` (or any SID that is not the current user) → confirmed dubious
  ownership. Not a git-config or credential problem.

Safe action — prefer the **scoped, non-mutating** override:

```bash
# Applies the exception for THIS one invocation only; writes nothing to global config
git -c safe.directory="<dir>" status
```

The commonly-pasted fix `git config --global --add safe.directory <dir>` **mutates global config**
(`~/.gitconfig`) permanently and accumulates an entry per repo — and `safe.directory '*'` disables
the guard everywhere. Per the diagnose-don't-mutate discipline, propose the per-command
`git -c safe.directory=<dir> …` form first; it needs no global write. If the user wants a durable
fix, taking real ownership of the directory (`takeown` / `icacls`, an FS-ACL change they confirm)
addresses the root cause, whereas the global `--add` only suppresses the symptom. Never silently
edit global git config as part of the diagnosis.

## Running WSL under a session-0 Windows service (LocalSystem) — empty 9P shares, ~30s VM death

Two failures appear only when WSL is invoked from a **Windows service / scheduled task running in
session 0 as `LocalSystem`**, not from the user's interactive shell:

- **`\\wsl.localhost\<distro>` (and `\\wsl$\<distro>`) appear EMPTY / inaccessible.** The 9P file
  shares that back those UNC paths are published by the **per-user** WSL session. A session-0
  `LocalSystem` context has no such mount, so a script reading `\\wsl.localhost\...` under the
  service sees nothing — even though the identical path lists fine in the user's terminal.
- **The WSL2 VM idle-stops ~30 seconds after the launching process exits.** When a service shells
  into WSL and returns, nothing keeps a handle on the lightweight utility VM, so it (and the
  distro) shut down about 30s later. The next call pays a cold start, or a distro the service
  "left running" is gone when it looks again.

Observe → localize:

```powershell
whoami                                            # NT AUTHORITY\SYSTEM => session-0 LocalSystem
Test-Path "\\wsl.localhost\<distro>\home"         # False/empty under the service, True as the user
wsl --list --verbose                              # distro flips to Stopped shortly after each call
```

Safe action: run WSL-touching work **in the user's own session** (a scheduled task set to the
user account with "run only when the user is logged on"), not as `LocalSystem`. If a service truly
must keep a distro alive, **pin the VM** by holding a long-lived process open (e.g. a background
`wsl -d <distro> -- sleep infinity` handle) so it does not idle-stop — do not rely on the distro
persisting on its own after a one-shot call. Surface the session-0 constraint to the user; do not
reconfigure services automatically.

## A pin/background process that "won't die": owner matters, and `pgrep -f` self-matches

Two independent measurement errors make an in-WSL background process (a VM pin, a keepalive, any
`sleep`-style holder) look like it survived a kill — or like it exists when it does not. Both are
counting mistakes, not stubborn processes.

- **`pkill` cannot signal a process owned by another user, and says nothing about it.** A pin
  started by a scheduled task with `wsl -d <distro> -u root --exec …` is **root-owned**; a pin the
  user started interactively runs as the default account. `pkill -f "<pattern>"` run as the normal
  user kills only that user's matches, silently leaves the root-owned one running, and still exits
  as if it had done its job. The tell is that a follow-up `pgrep` still lists the process. This is
  the ordinary Unix signal-permission rule, not a WSL quirk — but WSL is where it bites, because
  the two pins are spawned by different launchers and look identical on the command line.
- **`pgrep -f <pattern>` matches the measuring shell itself.** The pattern appears verbatim in the
  command line of the very process doing the search, so `pgrep -f 'sleep infinity' | wc -l`
  over-counts by one and a "how many pins are left" check never reaches zero. Use an exact
  process-name match (`pgrep -xa sleep`), or exclude the current pid, so the count is real.

Observe → localize (read-only — identify the owner before signalling anything):

```bash
# Who owns each candidate? The user column is the whole story.
ps -eo pid,user,args | grep -E "<pattern>" | grep -v grep

# Exact process-name match — no self-match artifact from the pattern.
pgrep -xa <process-name>
```

Safe action: report the surviving process **with its owner and pid**, and propose the matching
remedy — a root-owned pin needs `sudo`/a root shell (`wsl -d <distro> -u root`) or its owning
scheduled task disabled, not a louder `pkill`. Never widen a kill pattern, and never escalate a
pattern-based kill to root, to make a stubborn match disappear; a broad pattern run as root is
exactly how unrelated processes get killed. Re-check with `ps -eo pid,user,args` after any kill the user applies — an
exit code from `pkill` is not evidence the target is gone.

Related side effect worth anticipating: re-running the **installer** for a scheduled task that
ends by starting the task will *fire* the task as it installs, re-spawning the very pin you were
trying to remove. Read an installer to its last line before running it as part of a diagnosis.

## WSL2 sshd: socket-activation ignores `Port`, and a Windows listener blocks the bind

Three independent reasons an in-WSL `sshd` does not listen where you expect — or refuses to
validate at all:

- **systemd socket-activation ignores `Port` in `sshd_config`.** When sshd is started via
  `ssh.socket` (socket activation), the listening port is dictated by the **socket unit's**
  `ListenStream`, and the `Port` directive in `sshd_config` is **ignored**. Editing `Port 2222`
  changes nothing; sshd keeps listening on the socket unit's port (typically 22). Recent
  distributions (Ubuntu 24.04 and later) ship openssh-server socket-activated **by default**, so
  this is the expected starting state, not a mis-configuration someone introduced. `ListenAddress`
  is ignored for the same reason — the socket unit owns the listener, so neither the port nor the
  bind address in `sshd_config` (or a drop-in) is in charge. A drop-in that looks perfectly correct
  therefore has no observable effect, and a smoke test against the intended port fails.
- **A fresh openssh-server install fails `sshd -t` on a missing `/run/sshd`.** Immediately after
  installing the package, `sudo sshd -t` errors with
  `Missing privilege separation directory: /run/sshd` — because that directory is created by
  systemd's `RuntimeDirectory=sshd`, which only runs on the **first service start**. The config
  under test may be entirely valid; the failure is about the runtime directory, not the file. Do
  not "fix" a config that the test only appears to reject.
- **A Windows-side listener blocks the Linux bind (`EADDRINUSE`).** Under mirrored networking WSL
  shares the Windows network namespace, so if a Windows process already listens on the port (the
  built-in Windows OpenSSH sshd on 22, for instance), the in-WSL sshd cannot bind and dies with
  "address already in use".

Observe → localize:

```bash
# Is sshd socket-activated? Then sshd_config's Port / ListenAddress are not in charge.
systemctl is-active ssh.socket
systemctl cat ssh.socket | grep -i ListenStream     # the ACTUAL port
ss -ltnp | grep -E ':(22|<PORT>)\b'

# Does /run/sshd exist yet? Its absence — not the config — is what `sshd -t` is complaining about.
test -d /run/sshd && echo "present" || echo "absent (service has never started)"
```

```powershell
# Is the Windows side already squatting the port? (mirrored-mode collision)
Get-NetTCPConnection -State Listen -LocalPort <PORT> | Select LocalAddress, OwningProcess
```

Safe action: for the socket-activation case, change the **socket unit's** `ListenStream` (or
disable **and stop** `ssh.socket`, then enable and start `ssh.service`) rather than only editing
`sshd_config` — the socket must be stopped, not merely disabled, or it keeps the inherited listener
alive for the current boot. Verify the outcome with `ss -tlnp`: exactly the intended port should be
listening and the old one gone. Do not accept "the config says 2222" as evidence; only the listener
listing is. For the `/run/sshd` case, either start the service once and let its `ExecStartPre`
validate the config, or create the directory before validating manually
(`install -d -o root -g root -m 0755 /run/sshd`) — both are mutations, so propose them rather than
running them during diagnosis. For `EADDRINUSE`, identify which side legitimately owns the port
first (see the localhost-masquerade section), then relocate or stop the correct one — do not
blanket-kill listeners.

## `/mnt/c` root is read-only; the Windows Desktop may be OneDrive-redirected

Two path traps when a WSL script writes to the Windows filesystem:

- **The root of `/mnt/c` (i.e. `C:\`) is effectively read-only from WSL.** Creating a new top-level
  entry (`mkdir /mnt/c/<x>`, a file at `/mnt/c/<x>`) fails with permission denied, because writing
  to the drive root needs Windows admin. Work under a user-writable subtree
  (`/mnt/c/Users/<you>/...`), not the drive root.
- **The Desktop (and Documents/Pictures) may be OneDrive-redirected.** Known folders are often
  redirected to `%USERPROFILE%\OneDrive\Desktop`, so writing to `/mnt/c/Users/<you>/Desktop` lands
  in a stale, non-synced location while the *real* Desktop lives under `.../OneDrive/Desktop` — the
  file "vanishes" from the user's view. Do not assume `~/Desktop` / `Users\<you>\Desktop`.

Observe → localize:

```powershell
# Resolve the REAL Desktop known-folder rather than guessing the path
[Environment]::GetFolderPath('Desktop')
(Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders').Desktop
```

Safe action: write under a confirmed user-writable subtree, and resolve the Desktop/Documents path
from the Windows known-folder API (above) instead of hard-coding `Users\<you>\Desktop`. This is a
path-resolution fix, not a permissions change to apply — never `chmod`/`icacls` the drive root to
force a write through.

## Summary

| Symptom | Section | First safe move |
|---------|---------|-----------------|
| Wrong distro responds to `wsl` | Distro discovery | `wsl --list --verbose`, use exact name |
| External API unreachable | DNS-vs-TCP ladder | ping IP → TCP connect → name-vs-IP fetch |
| Public names time out, IPs work | VPN/DNS conflict | compare resolver latency, inspect metrics |
| Shell hangs / HCS timeout | HCS escalation ladder | terminate distro, stop at first that recovers |
| "Fixed" service unchanged | localhost masquerade | check both sides, stop WSL-side service first |
| Slow/failed bulk file copy | File-transfer caveats | copy from inside WSL to mounted drive |
| Wrote `/tmp/...`, Read can't find it | `/tmp` maps to Windows temp | write to an explicit absolute path |
| Empty content-search "proves" absence | Confirm with direct Read | Read the absolute path before believing the negative |
| Quoted identifier from a search looks corrupted | Interactive search highlighting | re-run `--color=never`, or Read the matched line |
| Port behaves erratically under mirrored mode | mirrored + stale forward | clear the redundant IDE port-forward |
| In-WSL bind `EADDRINUSE` but `ss`/`fuser` show the port free | `EADDRINUSE` invisible from inside | check the Windows side for the listener and its PID |
| In-WSL name lookups hang with a VPN mesh | mirrored-mode DNS overlap | compare resolver latency; report the overlap |
| Intermittent drop, IP churn (nat mode) | nat-mode idle-stop | address by name; expect cold-start delay |
| Restating "Windows can't reach `<PORT>`" | VM restart expires the verdict | re-probe before repeating it or asking for elevation |
| `fatal: dubious ownership` in a repo | Windows git ownership | scoped `git -c safe.directory=<dir>`; avoid the global `--add` |
| `\\wsl.localhost` empty from a service | Session-0 WSL service | run WSL in the user session, not LocalSystem |
| Distro dies ~30s after a service call | Session-0 WSL service | pin the VM with a held-open process |
| `pkill` "worked" but the pin still runs | Pin owner / `pgrep` self-match | `ps -eo pid,user,args` — a root-owned pin ignores a user `pkill` |
| A `pgrep -f` count never reaches zero | Pin owner / `pgrep` self-match | re-count with `pgrep -xa <name>`; the pattern matched your own shell |
| sshd ignores `Port`/`ListenAddress`, or bind `EADDRINUSE` | WSL2 sshd | edit the socket unit (disable **and stop** `ssh.socket`); free the Windows-side port |
| `sshd -t`: "Missing privilege separation directory: /run/sshd" | WSL2 sshd | the config may be fine — `/run/sshd` appears on first service start |
| `mkdir /mnt/c/<x>` denied; Desktop file missing | `/mnt/c` root + OneDrive | write under a user subtree; resolve the real Desktop path |
