<#
.SYNOPSIS
  env-doctor: shrink a WSL2 distro's ext4.vhdx after a cleanup (diskpart compact).

.DESCRIPTION
  A WSL2 disk image grows but never shrinks on its own; deleting files inside the distro
  frees space for the distro only. This script returns it to Windows.

  -Mode dry (default): reports the image size, the free space on its drive, what the
  run would do, and the idle gate's verdict if the distro is already running. It changes
  nothing, needs no elevation and does not start WSL.

  -Mode run (elevated PowerShell only, the user runs it):
    1. idle gate twice, 60 s apart (scripts/idle_gate.sh inside the distro): no long jobs,
       no server log written in 10 min, no active Postgres query. Busy -> stop.
    2. refuse if another wsl.exe client is attached (another terminal or Claude session).
    3. wsl --shutdown, then wait until vmmem / vmmemWSL is gone (abort after 120 s).
    4. diskpart: select vdisk / attach vdisk readonly / compact vdisk / detach vdisk.
    5. report size before -> after and the space reclaimed.
  Never uses `wsl --manage --set-sparse` (gated behind --allow-unsafe on WSL 2.6.x over
  corruption reports). Running servers stop with the VM: snapshot them first (the odoo
  plugin's local_snapshot / local_relaunch when present) and restart them afterwards.

.PARAMETER Distro
  Distro name exactly as `wsl -l -v` prints it. Default: the default distro.

.PARAMETER VhdxPath
  Override the image path (default: read from HKCU\...\Lxss\<id>\BasePath).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File compact-wsl.ps1 -Distro Ubuntu
  (dry run)
.EXAMPLE
  # elevated PowerShell, after telling other sessions to pause WSL work:
  powershell -NoProfile -ExecutionPolicy Bypass -File compact-wsl.ps1 -Distro Ubuntu -Mode run
#>
[CmdletBinding()]
param(
    [string]$Distro = '',
    [ValidateSet('dry', 'run')][string]$Mode = 'dry',
    [string]$VhdxPath = '',
    [int]$QuietMinutes = 10
)
$ErrorActionPreference = 'Stop'
$env:WSL_UTF8 = '1'

function Get-DistroImage([string]$name) {
    $root = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss'
    $default = (Get-ItemProperty $root -ErrorAction SilentlyContinue).DefaultDistribution
    foreach ($k in Get-ChildItem $root -ErrorAction SilentlyContinue) {
        $p = Get-ItemProperty $k.PSPath
        if (($name -and $p.DistributionName -eq $name) -or (-not $name -and $k.PSChildName -eq $default)) {
            $base = [string]$p.BasePath
            if ($base.StartsWith('\\?\')) { $base = $base.Substring(4) }
            return [pscustomobject]@{ Name = $p.DistributionName; Vhdx = (Join-Path $base 'ext4.vhdx') }
        }
    }
    return $null
}

function Get-RunningDistros {
    $out = & wsl.exe --list --running --quiet 2>$null
    if ($LASTEXITCODE -ne 0) { return @() }
    return @($out | ForEach-Object { ($_ -replace "`0", '').Trim() } | Where-Object { $_ })
}

function Invoke-IdleGate([string]$name) {
    $gate = Join-Path $PSScriptRoot 'idle_gate.sh'
    $linux = (& wsl.exe -d $name -- wslpath -a ($gate -replace '\\', '/')) -replace "`0", ''
    $lines = & wsl.exe -d $name -- bash $linux.Trim() $QuietMinutes 2>&1
    return [pscustomobject]@{ Idle = ($LASTEXITCODE -eq 0); Text = (($lines | ForEach-Object { "$_" }) -join "`n") }
}

$img = Get-DistroImage $Distro
if (-not $img) { throw "Distro '$Distro' not found in the Lxss registry. Use the exact name from 'wsl -l -v'." }
if ($VhdxPath) { $img.Vhdx = $VhdxPath }
if (-not (Test-Path -LiteralPath $img.Vhdx)) { throw "Image not found: $($img.Vhdx)" }

$before = (Get-Item -LiteralPath $img.Vhdx).Length
$drive = Get-PSDrive -Name ($img.Vhdx.Substring(0, 1))
Write-Output ("Distro {0}: image {1} = {2:N1} GB; drive {3}: {4:N1} GB free" -f $img.Name, $img.Vhdx, ($before / 1GB), $drive.Name, ($drive.Free / 1GB))

$running = Get-RunningDistros
if ($Mode -eq 'dry') {
    if ($running -contains $img.Name) {
        $g = Invoke-IdleGate $img.Name
        Write-Output ("Idle gate now: " + $g.Text)
    } else {
        Write-Output 'WSL distro is not running; the idle gate is not evaluated (dry run does not start WSL).'
    }
    Write-Output 'DRY RUN: a run (elevated) would: gate twice 60 s apart -> refuse if other wsl.exe clients are attached -> wsl --shutdown -> wait for vmmem to exit -> diskpart attach readonly / compact / detach -> report.'
    Write-Output 'Nothing was changed.'
    exit 0
}

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { throw 'Run mode needs an elevated PowerShell (diskpart). Nothing was changed.' }

if ($running -contains $img.Name) {
    foreach ($pass in 1, 2) {
        $g = Invoke-IdleGate $img.Name
        if (-not $g.Idle) { throw ("Idle gate pass ${pass}: BUSY. Nothing was changed.`n" + $g.Text) }
        Write-Output "Idle gate pass ${pass}: IDLE"
        if ($pass -eq 1) { Start-Sleep -Seconds 60 }
    }
}
$others = @(Get-CimInstance Win32_Process -Filter "Name = 'wsl.exe'" | Where-Object { $_.ProcessId -ne $PID })
if ($others.Count -gt 0) {
    throw ("{0} other wsl.exe client(s) attached (another terminal or session). Close them first. Nothing was changed.`n{1}" -f $others.Count, (($others | ForEach-Object { "  pid $($_.ProcessId): $($_.CommandLine)" }) -join "`n"))
}

Write-Output 'wsl --shutdown'
& wsl.exe --shutdown
$deadline = (Get-Date).AddSeconds(120)
while (Get-Process -Name 'vmmem', 'vmmemWSL' -ErrorAction SilentlyContinue) {
    if ((Get-Date) -gt $deadline) { throw 'The WSL VM (vmmem) is still running after 120 s; not compacting.' }
    Start-Sleep -Seconds 2
}

$script = Join-Path $env:TEMP ("envdoc-compact-{0}.txt" -f [guid]::NewGuid())
@(
    "select vdisk file=`"$($img.Vhdx)`"",
    'attach vdisk readonly',
    'compact vdisk',
    'detach vdisk'
) | Set-Content -LiteralPath $script -Encoding ASCII
try {
    & diskpart.exe /s $script
    if ($LASTEXITCODE -ne 0) { throw "diskpart exited $LASTEXITCODE" }
} finally {
    Remove-Item -LiteralPath $script -ErrorAction SilentlyContinue
}

$after = (Get-Item -LiteralPath $img.Vhdx).Length
Write-Output ("Compacted: {0:N2} GB -> {1:N2} GB, reclaimed {2:N2} GB. Start WSL again with: wsl -d {3}" -f ($before / 1GB), ($after / 1GB), (($before - $after) / 1GB), $img.Name)
