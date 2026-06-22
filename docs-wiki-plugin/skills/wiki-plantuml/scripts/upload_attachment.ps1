<#
.SYNOPSIS
  Azure DevOps ONLY - upload a rendered swimlane image (PNG by default) to the wiki's
  hidden /.attachments folder via the Wiki Attachments REST API, then return the
  root-relative reference for embedding.

.DESCRIPTION
  Owned by the docs-wiki `wiki-plantuml` skill. Encapsulates the Azure attachment gotchas:
    - PAT read from $env:AZDO_PAT - NEVER echoed or logged.
    - Body MUST be base64-encoded for the CLI/REST path (raw octet-stream => "broken image link").
    - PNG is the correct attachment format (official list: PNG/GIF/JPEG/ICO; SVG not listed).
    - VERIFY-ON-FAIL: the PUT commonly returns HTTP 500 even though the attachment WAS written.
      Treat 500 as "verify, don't abort" - re-fetch the attachment; succeed if present.
    - Re-uploading the same name creates a new ETag version (not an error) - idempotent.
    - "Wiki not found" => the wiki is not provisioned yet (a human creates it once), NOT a 403.

.PARAMETER Org           Azure DevOps org URL, e.g. https://dev.azure.com/contoso
.PARAMETER Project       Project name or GUID.
.PARAMETER WikiId        Wiki id or name.
.PARAMETER File          Path to the rendered image (PNG recommended).
.PARAMETER Name          Attachment name (e.g. swimlane-orders-fulfilment.png). URL-encoded for you.
.PARAMETER ApiVersion    Default 7.1.

.EXAMPLE
  $env:AZDO_PAT = '<pat-with-vso.wiki_write>'   # set in the session, not on the command line
  ./upload_attachment.ps1 -Org https://dev.azure.com/contoso -Project Web -WikiId Web.wiki `
      -File swimlane-orders-fulfilment.png -Name swimlane-orders-fulfilment.png
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$Org,
  [Parameter(Mandatory = $true)][string]$Project,
  [Parameter(Mandatory = $true)][string]$WikiId,
  [Parameter(Mandatory = $true)][string]$File,
  [Parameter(Mandatory = $true)][string]$Name,
  [string]$ApiVersion = '7.1'
)

$ErrorActionPreference = 'Stop'
function Fail($msg) { Write-Error $msg; exit 1 }

if (-not (Test-Path -LiteralPath $File)) { Fail "File not found: $File" }
$pat = $env:AZDO_PAT
if (-not $pat) { Fail "AZDO_PAT not set in the environment (scope vso.wiki_write). It is read from env and never echoed." }

# Basic auth header - PAT is never printed.
$auth = 'Basic ' + [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(":$pat"))
$headers = @{ Authorization = $auth }

# Body MUST be base64 for the CLI/REST path.
$bytes = [System.IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $File))
$body = [Convert]::ToBase64String($bytes)

$encodedName = [System.Uri]::EscapeDataString($Name)
$base = "$($Org.TrimEnd('/'))/$Project/_apis/wiki/wikis/$WikiId"
$putUri = "$base/attachments?name=$encodedName&api-version=$ApiVersion"
$getUri = "$base/attachments/$encodedName" + "?api-version=$ApiVersion"

function Test-AttachmentExists {
  try {
    Invoke-RestMethod -Method Get -Uri $getUri -Headers $headers -ErrorAction Stop | Out-Null
    return $true
  } catch { return $false }
}

Write-Host "Uploading $Name to wiki $WikiId (.attachments) ..."
try {
  Invoke-RestMethod -Method Put -Uri $putUri -Headers $headers `
    -ContentType 'application/octet-stream' -Body $body -ErrorAction Stop | Out-Null
  Write-Host "OK: uploaded."
}
catch {
  $status = $null
  if ($_.Exception.Response) { $status = [int]$_.Exception.Response.StatusCode }
  $msg = "$($_.Exception.Message)"

  if ($msg -match 'Wiki not found' -or $msg -match 'TF401174') {
    Fail "Wiki '$WikiId' not found - the project wiki is not provisioned yet (a human creates it once via Project Settings -> Wiki). This is NOT a permission error."
  }

  if ($status -eq 500) {
    # KNOWN QUIRK: PUT often returns 500 yet the attachment was written. Verify, don't abort.
    Write-Warning "PUT returned HTTP 500 - verifying whether the attachment was actually written..."
    if (Test-AttachmentExists) {
      Write-Host "OK: attachment present despite HTTP 500 (verify-on-fail succeeded)."
    } else {
      Fail "HTTP 500 and the attachment is genuinely missing on re-fetch - real failure."
    }
  }
  else {
    Fail "Attachment upload failed (HTTP $status): $msg"
  }
}

# Root-relative reference for the page embed (NOT relative to the .md).
$ref = "/.attachments/$Name"
Write-Host "Embed reference: ![alt]($ref)"
$ref
