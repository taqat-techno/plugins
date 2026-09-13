#Requires -Version 5.1
<#
    notification plugin - Windows toast backend.

    Reads its payload from the environment, never from the command line, so
    quotes, newlines, dollar signs and backticks in a question or an API error
    can never be parsed as PowerShell. All text is XML-escaped before it is
    placed in the toast document.

    Environment contract (set by hooks/backends.py):
        CCN_MODE        "show" (default) or "remove"
        CCN_TITLE       notification title
        CCN_BODY        notification body
        CCN_ATTRIB      attribution line, "session a1b2c3"
        CCN_ATTENTION   "1" for attention class: long duration when not persistent
        CCN_PERSISTENT  "1" to stay on screen until the user closes it (D-015)
        CCN_SILENT      "1" to suppress the notification sound
        CCN_TAG         unique toast id, never reused, so toasts never replace each other
        CCN_GROUP       session + category, so stale toasts can be withdrawn together
        CCN_REMOVE      ";"-separated groups of earlier toasts to withdraw
        CCN_ICON        absolute path of the header icon PNG (registered as IconUri)

    App identity (D-014): toasts are shown under a per-user AppUserModelID whose
    display name is "Claude Code", registered under HKCU on first use - no admin
    rights, no Start Menu shortcut. If registration fails for any reason, the
    toast falls back to Windows PowerShell's own identity and still appears.

    Must run under Windows PowerShell 5.1 (powershell.exe), NOT PowerShell 7:
    pwsh cannot load WinRT types without the Windows SDK projections.

    Always exits 0.
#>

[CmdletBinding()]
param()

$AppId         = 'TaqaTechno.ClaudeCode.Notifications'
$AppName       = 'Claude Code'
$FallbackAppId = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
$DefaultGroup  = 'claude-code'

function ConvertTo-XmlText {
    param([string] $Value)
    if ([string]::IsNullOrEmpty($Value)) { return '' }
    $escaped = $Value -replace '&', '&amp;'
    $escaped = $escaped -replace '<', '&lt;'
    $escaped = $escaped -replace '>', '&gt;'
    $escaped = $escaped -replace '"', '&quot;'
    $escaped = $escaped -replace "'", '&apos;'
    return $escaped
}

function Register-AppIdentity {
    # Idempotent: reads first and writes only what differs, so a normal call
    # touches nothing. IconUri is written BEFORE the first toast is shown,
    # because Windows caches an app's header icon the first time it sees it. It
    # is re-pointed after a plugin upgrade moves the install directory.
    param([string] $IconPath)
    try {
        $key = "HKCU:\Software\Classes\AppUserModelId\$AppId"
        if (-not (Test-Path -Path $key)) { [void](New-Item -Path $key -Force) }
        $current = Get-ItemProperty -Path $key
        if ($IconPath -and (Test-Path -LiteralPath $IconPath) -and ($current.IconUri -ne $IconPath)) {
            Set-ItemProperty -Path $key -Name IconUri -Value $IconPath
        }
        if ($current.DisplayName -ne $AppName) {
            Set-ItemProperty -Path $key -Name DisplayName -Value $AppName
        }
        if ($current.ShowInSettings -ne 1) {
            Set-ItemProperty -Path $key -Name ShowInSettings -Value 1 -Type DWord
        }
        return $true
    }
    catch {
        return $false
    }
}

try {
    [void][Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
    [void][Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime]

    $appId = if (Register-AppIdentity $env:CCN_ICON) { $AppId } else { $FallbackAppId }

    # Withdraw stale toasts - only ever because the user acted: an answered
    # question, or a session's waiting toasts once the user types again. A new
    # notification never removes an older one.
    if ($env:CCN_REMOVE) {
        $history = [Windows.UI.Notifications.ToastNotificationManager]::History
        foreach ($oldGroup in ($env:CCN_REMOVE -split ';')) {
            if ($oldGroup) {
                try { $history.RemoveGroup($oldGroup, $appId) } catch { }
            }
        }
    }

    if ($env:CCN_MODE -eq 'remove') { exit 0 }

    $title      = if ($env:CCN_TITLE)  { $env:CCN_TITLE }  else { 'Claude Code' }
    $body       = if ($env:CCN_BODY)   { $env:CCN_BODY }   else { '' }
    $attrib     = if ($env:CCN_ATTRIB) { $env:CCN_ATTRIB } else { '' }
    $attention  = ($env:CCN_ATTENTION -eq '1')
    $persistent = ($env:CCN_PERSISTENT -eq '1')
    $silent     = ($env:CCN_SILENT -eq '1')
    $tag        = if ($env:CCN_TAG) { $env:CCN_TAG } else { [guid]::NewGuid().ToString('N').Substring(0, 16) }
    $group      = if ($env:CCN_GROUP) { $env:CCN_GROUP } else { $DefaultGroup }

    # Persistent toasts use scenario="reminder", which stays on screen until the
    # user closes it - but Windows SILENTLY IGNORES that scenario unless the toast
    # shows a button with a background action. Verified live on 2026-09-13: the
    # same action placed only in the ... menu (placement="contextMenu") does NOT
    # keep the toast on screen, hence the visible Close button. Everything else
    # auto-dismisses: attention after about 25 s, informational sooner.
    $toastAttributes = ''
    $actions = ''
    if ($persistent) {
        $toastAttributes = ' scenario="reminder"'
        $actions = '<actions><action content="Close" arguments="dismiss" activationType="background"/></actions>'
    } elseif ($attention) {
        $toastAttributes = ' duration="long"'
    }

    $audio = if ($silent) { '<audio silent="true"/>' } else { '' }

    $attribNode = ''
    if ($attrib) {
        $attribNode = '<text placement="attribution">' + (ConvertTo-XmlText $attrib) + '</text>'
    }

    $xml = @"
<toast$toastAttributes>
  <visual>
    <binding template="ToastGeneric">
      <text hint-maxLines="2">$(ConvertTo-XmlText $title)</text>
      <text>$(ConvertTo-XmlText $body)</text>
      $attribNode
    </binding>
  </visual>
  $actions
  $audio
</toast>
"@

    $document = New-Object Windows.Data.Xml.Dom.XmlDocument
    $document.LoadXml($xml)

    $toast = New-Object Windows.UI.Notifications.ToastNotification $document
    # A unique tag means a new toast never replaces an older one; the group
    # (session + category) is what lets a later event withdraw stale toasts.
    $toast.Tag   = $tag
    $toast.Group = $group

    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show($toast)
}
catch {
    # A notifier must never disturb the session it observes.
}

exit 0
