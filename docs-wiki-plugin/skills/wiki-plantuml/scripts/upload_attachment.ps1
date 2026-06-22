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

# Body for the CLI/REST path. NOTE: the official spec documents a raw octet-stream body,
# but on this org's instance base64 transport is the verified-working path (raw bytes via
# Invoke-RestMethod can mis-encode). If your instance renders a broken image, switch to
# raw bytes: set $body = $bytes below and keep Content-Type application/octet-stream.
$bytes = [System.IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $File))
$body = [Convert]::ToBase64String($bytes)

$encodedName = [System.Uri]::EscapeDataString($Name)
$base = "$($Org.TrimEnd('/'))/$Project/_apis/wiki/wikis/$WikiId"
$putUri = "$base/attachments?name=$encodedName&api-version=$ApiVersion"
# The Wiki Attachments API (7.1) is Create-only -- there is NO GET-by-name endpoint, so
# the 500-but-succeeded quirk is verified by RE-PUTting (idempotent), never by a GET.
function Invoke-AttachmentPut {
  Invoke-RestMethod -Method Put -Uri $putUri -Headers $headers `
    -ContentType 'application/octet-stream' -Body $body -ErrorAction Stop | Out-Null
}

Write-Host "Uploading $Name to wiki $WikiId (.attachments) ..."
try {
  Invoke-AttachmentPut
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
    # KNOWN QUIRK: the PUT commonly returns HTTP 500 yet the attachment WAS written.
    # Re-uploading the same name is idempotent (new ETag version, not an error), so a
    # clean re-PUT confirms the attachment is in place. This replaces the old GET-by-name
    # check, which always failed because that endpoint does not exist in this API.
    Write-Warning "PUT returned HTTP 500 - re-PUTting (idempotent) to confirm the attachment landed..."
    try {
      Invoke-AttachmentPut
      Write-Host "OK: re-PUT succeeded - the attachment is present (the first 500 was spurious)."
    }
    catch {
      $status2 = $null
      if ($_.Exception.Response) { $status2 = [int]$_.Exception.Response.StatusCode }
      Fail "HTTP 500 on the first PUT and the idempotent re-PUT also failed (HTTP $status2) - real failure."
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
