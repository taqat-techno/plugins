<#
.SYNOPSIS
  Render a PlantUML activity-beta swimlane (.puml) to SVG (default) or PNG using a
  PINNED local plantuml.jar - the privacy-safe default render path (no network).

.DESCRIPTION
  Owned by the docs-wiki `wiki-plantuml` skill. Lints the .puml for the two
  most common authoring faults before rendering, then invokes java -jar.

  Guarantees:
    - Pins the jar version. Refuses the 2012 Maven-"latest" build 8059 trap.
    - Sets PLANTUML_LIMIT_SIZE to clear the silent 4096px-per-axis clip on big diagrams.
    - Lints: rejects the DEPRECATED prefix colour form (#color:text;) and unbalanced
      if/endif gateways - both mis-render silently in activity-beta.
    - No network. Source never egresses.

.PARAMETER Puml
  Path to the .puml swimlane source.

.PARAMETER Format
  svg (default) | png. PNG is the safe embed default on GitHub/Azure wikis.

.PARAMETER Out
  Output directory (default: same directory as the .puml).

.PARAMETER JavaExe
  java executable (default: $env:DOCS_WIKI_JAVA or 'java' on PATH).

.PARAMETER PlantumlJar
  plantuml.jar path (default: $env:DOCS_WIKI_PLANTUML_JAR). MUST be a 1.20xx version.

.PARAMETER LimitSize
  PLANTUML_LIMIT_SIZE value (default 8192).

.EXAMPLE
  ./render_puml.ps1 -Puml swimlane-orders-fulfilment.puml -Format png
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$Puml,
  [ValidateSet('svg', 'png')][string]$Format = 'svg',
  [string]$Out,
  [string]$JavaExe = $(if ($env:DOCS_WIKI_JAVA) { $env:DOCS_WIKI_JAVA } else { 'java' }),
  [string]$PlantumlJar = $env:DOCS_WIKI_PLANTUML_JAR,
  [int]$LimitSize = 8192
)

$ErrorActionPreference = 'Stop'

function Fail($msg) { Write-Error $msg; exit 1 }

# --- Preconditions --------------------------------------------------------
if (-not (Test-Path -LiteralPath $Puml)) { Fail "Puml not found: $Puml" }
if (-not $PlantumlJar) { Fail "plantuml.jar not set. Pass -PlantumlJar or set DOCS_WIKI_PLANTUML_JAR (a 1.20xx version)." }
if (-not (Test-Path -LiteralPath $PlantumlJar)) { Fail "plantuml.jar not found: $PlantumlJar" }
if (-not (Get-Command $JavaExe -ErrorAction SilentlyContinue)) { Fail "java not found: $JavaExe (need JRE 11+)." }

# Reject the Maven-"latest" 8059 ancient-jar trap (2012 build sorts above date-scheme).
if ($PlantumlJar -match '8059') {
  Fail "Refusing plantuml jar '8059' - that is the 2012 Maven-'latest' trap. Pin a 1.2026.x jar."
}

# --- Lint the .puml before rendering -------------------------------------
$src = Get-Content -LiteralPath $Puml -Raw
$lines = $src -split "`r?`n"

# (1) Deprecated PREFIX colour form on an ACTIVITY: a line like "#PaleGreen:Step;".
#     Require a trailing ';' so <style>/skinparam hex lines do NOT false-positive.
$prefixColour = @()
for ($i = 0; $i -lt $lines.Count; $i++) {
  if ($lines[$i] -match '^\s*#[0-9A-Za-z]+\s*:.+;\s*$') { $prefixColour += ($i + 1) }
}
if ($prefixColour.Count -gt 0) {
  Fail ("Deprecated PREFIX colour form on line(s) $($prefixColour -join ', '). " +
        "activity-beta requires the END-OF-LINE suffix stereotype ':text; <<#RRGGBB>>'.")
}

# (2) Unbalanced gateways: count if vs endif (a swimlane with mismatched counts mis-renders).
$ifCount    = ([regex]::Matches($src, '(?m)^\s*if\s*\(')).Count
$endifCount = ([regex]::Matches($src, '(?m)^\s*endif\b')).Count
if ($ifCount -ne $endifCount) {
  Fail "Unbalanced gateways: $ifCount 'if(' vs $endifCount 'endif'. Balance them before rendering."
}

# --- Render ---------------------------------------------------------------
if (-not $Out) { $Out = Split-Path -Parent (Resolve-Path -LiteralPath $Puml) }
if (-not (Test-Path -LiteralPath $Out)) { New-Item -ItemType Directory -Path $Out -Force | Out-Null }

$env:PLANTUML_LIMIT_SIZE = "$LimitSize"
$flag = "-t$Format"

Write-Host "Rendering $Puml -> $Format (limit=$LimitSize) with $(Split-Path -Leaf $PlantumlJar)"
& $JavaExe '-jar' $PlantumlJar $flag '-o' $Out (Resolve-Path -LiteralPath $Puml).Path
if ($LASTEXITCODE -ne 0) { Fail "PlantUML render failed (exit $LASTEXITCODE)." }

$base = [System.IO.Path]::GetFileNameWithoutExtension($Puml)
$artifact = Join-Path $Out "$base.$Format"
if (-not (Test-Path -LiteralPath $artifact)) { Fail "Render reported success but $artifact is missing." }

Write-Host "OK: $artifact"
$artifact
