#Requires -Version 5.1
<#
    notification plugin - Windows toast backend.

    Reads its payload from the environment, never from the command line, so
    quotes, newlines, dollar signs and backticks in a question or an API error
    can never be parsed as PowerShell. All text is XML-escaped before it is
    placed in the toast document.

    Environment contract (set by hooks/backends.py):
        CCN_TITLE    notification title
        CCN_BODY     notification body
        CCN_ATTRIB   attribution line, "project - a1b2c3"
        CCN_STICKY   "1" to stay on screen until dismissed
        CCN_SILENT   "1" to suppress the notification sound
        CCN_TAG      replace-in-place key, so a burst updates one toast

    Must run under Windows PowerShell 5.1 (powershell.exe), NOT PowerShell 7:
    pwsh cannot load WinRT types without the Windows SDK projections.

    Always exits 0.
#>

[CmdletBinding()]
param()

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

try {
    $title  = if ($env:CCN_TITLE)  { $env:CCN_TITLE }  else { 'Claude Code' }
    $body   = if ($env:CCN_BODY)   { $env:CCN_BODY }   else { '' }
    $attrib = if ($env:CCN_ATTRIB) { $env:CCN_ATTRIB } else { '' }
    $sticky = ($env:CCN_STICKY -eq '1')
    $silent = ($env:CCN_SILENT -eq '1')
    $tag    = if ($env:CCN_TAG) { $env:CCN_TAG } else { 'claude-code' }

    [void][Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
    [void][Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime]

    # scenario="reminder" keeps the toast on screen until it is dismissed, but
    # Windows SILENTLY IGNORES it unless the toast carries at least one action
    # with background activation - hence the Dismiss button.
    $scenario = ''
    $actions  = ''
    if ($sticky) {
        $scenario = ' scenario="reminder"'
        $actions  = '<actions><action content="Dismiss" arguments="dismiss" activationType="background"/></actions>'
    }

    $audio = if ($silent) { '<audio silent="true"/>' } else { '' }

    $attribNode = ''
    if ($attrib) {
        $attribNode = '<text placement="attribution">' + (ConvertTo-XmlText $attrib) + '</text>'
    }

    $xml = @"
<toast$scenario>
  <visual>
    <binding template="ToastGeneric">
      <text>$(ConvertTo-XmlText $title)</text>
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
    # Tag and group give Windows a stable identity for this notification, so a
    # burst of task completions updates one toast instead of stacking five.
    $toast.Tag   = $tag
    $toast.Group = 'claude-code'

    # Windows PowerShell's own AppUserModelID. It already has a Start Menu
    # shortcut, which is what Windows requires to accept a toast, so the plugin
    # registers nothing.
    $appId = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show($toast)
}
catch {
    # A notifier must never disturb the session it observes.
}

exit 0
