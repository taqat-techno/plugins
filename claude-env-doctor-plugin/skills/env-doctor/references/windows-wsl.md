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

## Summary

| Symptom | Section | First safe move |
|---------|---------|-----------------|
| Wrong distro responds to `wsl` | Distro discovery | `wsl --list --verbose`, use exact name |
| External API unreachable | DNS-vs-TCP ladder | ping IP → TCP connect → name-vs-IP fetch |
| Public names time out, IPs work | VPN/DNS conflict | compare resolver latency, inspect metrics |
| Shell hangs / HCS timeout | HCS escalation ladder | terminate distro, stop at first that recovers |
| "Fixed" service unchanged | localhost masquerade | check both sides, stop WSL-side service first |
| Slow/failed bulk file copy | File-transfer caveats | copy from inside WSL to mounted drive |
