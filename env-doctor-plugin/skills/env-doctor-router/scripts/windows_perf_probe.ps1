<#
.SYNOPSIS
  env-doctor WSL performance branch -- READ-ONLY Windows-side probes.

.DESCRIPTION
  Prints one line per probe:  PROBE <name>: <measurement> -> <verdict>
  Reads WMI/CIM, Defender status, the registry, .wslconfig and file contents. Changes
  nothing, needs no elevation, does not start WSL. Defender exclusions are often unreadable
  without admin or under organisation policy; that is reported, never worked around.

.PARAMETER Path
  Windows folder to sample for the per-file open cost (default: the first of
  C:\TQ-WorkSpace, $env:USERPROFILE\source, $env:USERPROFILE that exists).

.PARAMETER Count
  Number of small files to read (default 200).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File windows_perf_probe.ps1 -Path C:\work\project
#>
[CmdletBinding()]
param([string]$Path = '', [int]$Count = 200)
$ErrorActionPreference = 'SilentlyContinue'
function Say([string]$name, [string]$value, [string]$verdict) { Write-Output ("PROBE {0}: {1} -> {2}" -f $name, $value, $verdict) }

# --- system drive, pagefile, commit ----------------------------------------------------------
$sys = $env:SystemDrive.TrimEnd(':')
$d = Get-PSDrive -Name $sys
if ($d) {
    $pct = 100 * $d.Free / ($d.Free + $d.Used)
    $v = if ($pct -lt 10) { 'LOW: Windows shrinks the pagefile; WSL may fail to boot with Wsl/0x8007000e' } else { 'ok' }
    Say 'system drive' ('{0:N1} GB free of {1:N0} GB ({2:N0}%)' -f ($d.Free / 1GB), (($d.Free + $d.Used) / 1GB), $pct) $v
}
$pf = Get-CimInstance Win32_PageFileUsage
if ($pf) {
    $alloc = ($pf | Measure-Object AllocatedBaseSize -Sum).Sum
    $v = if ($alloc -lt 4096) { 'SMALL: commit limit is close to RAM; a large WSL memory= can fail to reserve' } else { 'ok' }
    Say 'pagefile' ('{0} MB allocated, {1} MB in use' -f $alloc, (($pf | Measure-Object CurrentUsage -Sum).Sum)) $v
}
$os = Get-CimInstance Win32_OperatingSystem
if ($os) {
    $limit = $os.TotalVirtualMemorySize / 1MB; $free = $os.FreeVirtualMemory / 1MB
    $v = if ($free / $limit -lt 0.15) { 'HIGH commit: new VMs/processes can fail with out-of-memory (0x8007000e)' } else { 'ok' }
    Say 'commit' ('{0:N1} of {1:N1} GB committed; RAM {2:N1} GB, {3:N1} GB free' -f ($limit - $free), $limit, ($os.TotalVisibleMemorySize / 1MB), ($os.FreePhysicalMemory / 1MB)) $v
}

# --- Defender / Defender for Endpoint --------------------------------------------------------
$mp = Get-MpComputerStatus
if ($mp) {
    $v = if ($mp.RealTimeProtectionEnabled) { 'on-access scanning adds a per-file cost on C:\ and through /mnt/c' } else { 'off' }
    Say 'Defender real-time protection' ("enabled={0}, tamper-protected={1}, mode={2}" -f $mp.RealTimeProtectionEnabled, $mp.IsTamperProtected, $mp.AMRunningMode) $v
} else { Say 'Defender' 'Get-MpComputerStatus unavailable' 'another antivirus may be active; check its exclusions the same way' }
$sense = Get-Service -Name Sense
if ($sense) { Say 'Defender for Endpoint (Sense)' $sense.Status 'org-managed: exclusions are set by IT, not locally' }
$ex = (Get-MpPreference).ExclusionPath
if ($null -eq $ex) { Say 'Defender exclusions' 'not readable (needs admin, or hidden by policy)' 'ask IT; do not try to change them' }
elseif (@($ex | Where-Object { $_ -like 'N/A*' }).Count) { Say 'Defender exclusions' 'hidden by policy' 'ask IT; do not try to change them' }
else { Say 'Defender exclusions' ('{0} path(s): {1}' -f @($ex).Count, ((@($ex) | Select-Object -First 5) -join '; ')) 'check the workspace and the WSL VHDX folder are listed' }

# --- Windows-native per-file open cost -------------------------------------------------------
if (-not $Path) { $Path = @('C:\TQ-WorkSpace', (Join-Path $env:USERPROFILE 'source'), $env:USERPROFILE) | Where-Object { Test-Path $_ } | Select-Object -First 1 }
if ($Path -and (Test-Path $Path)) {
    $files = @(Get-ChildItem -LiteralPath $Path -Recurse -File -Depth 4 -Include *.py, *.xml, *.js, *.txt, *.json |
        Where-Object { $_.Length -lt 65536 } | Select-Object -First $Count)
    if ($files.Count) {
        $sw = [Diagnostics.Stopwatch]::StartNew()
        foreach ($f in $files) { [void][IO.File]::ReadAllBytes($f.FullName) }
        $sw.Stop()
        $per = $sw.Elapsed.TotalMilliseconds / $files.Count
        $v = if ($per -gt 5) { 'SLOW: on-access scanning (Defender/MDE) is the likely cost; healthy NVMe is ~0.05 ms' } elseif ($per -gt 1) { 'elevated' } else { 'ok' }
        Say "read cost Windows ($Path)" ('{0} files: {1:N2} ms/file' -f $files.Count, $per) $v
    }
}

# --- WSL version + .wslconfig ----------------------------------------------------------------
$ver = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Lxss\MSI').Version
if ($ver) {
    $v = if ($ver -like '2.6.3*') { 'known 0xc00000fd wsl.exe crashes: wsl --update (3.0.3+) when WSL is idle' } else { 'ok' }
    Say 'WSL version' $ver $v
}
$cfg = Join-Path $env:USERPROFILE '.wslconfig'
if (Test-Path $cfg) {
    $section = ''; $vals = @{}; $misplaced = @()
    foreach ($line in Get-Content -LiteralPath $cfg) {
        $t = $line.Trim()
        if ($t -match '^\[(.+)\]$') { $section = $Matches[1].ToLower(); continue }
        if ($t -match '^([A-Za-z]+)\s*=\s*(.+)$') {
            $vals["$section.$($Matches[1].ToLower())"] = $Matches[2].Trim()
            if ($section -eq 'wsl2' -and $Matches[1] -in @('autoMemoryReclaim', 'sparseVhd')) { $misplaced += $Matches[1] }
        }
    }
    $mem = $vals['wsl2.memory']; $swap = $vals['wsl2.swap']; $cpu = $vals['wsl2.processors']
    Say '.wslconfig' ("memory={0} swap={1} processors={2} vmIdleTimeout={3} autoMemoryReclaim={4}" -f $mem, $swap, $cpu, $vals['wsl2.vmidletimeout'], $vals['experimental.automemoryreclaim']) $(if ($misplaced.Count) { "MISPLACED under [wsl2] (belongs in [experimental] on 2.x): $($misplaced -join ', ')" } else { 'compare memory= with what your concurrent jobs need' })
} else { Say '.wslconfig' 'absent' 'WSL defaults: half of RAM; fine unless OOM kills appear inside the distro' }
