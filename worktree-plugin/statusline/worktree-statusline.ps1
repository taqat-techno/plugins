# worktree-statusline.ps1 - Claude Code status line showing the active worktree.
#
# Fallback for Windows machines where Git Bash is not installed. Claude Code
# routes status-line commands through Git Bash when it is present and through
# PowerShell when it is not. Prefer the .sh version: PowerShell startup costs
# roughly 600ms versus about 80ms for Git Bash, and Claude Code re-runs the
# status line on a 300ms debounce.
#
# Environment overrides: WT_GLYPH_TREE, WT_GLYPH_MAIN, WT_SEP, WT_SHOW_DIRTY.
# Always exits 0 and always prints something.

$ErrorActionPreference = 'SilentlyContinue'

$GT  = if ($env:WT_GLYPH_TREE) { $env:WT_GLYPH_TREE } else { [char]::ConvertFromUtf32(0x1F333) }
$GM  = if ($env:WT_GLYPH_MAIN) { $env:WT_GLYPH_MAIN } else { [char]0x25C9 }
$SEP = if ($env:WT_SEP)        { $env:WT_SEP }        else { ' | ' }

$raw = $input | Out-String
$j = $null
try { if ($raw.Trim()) { $j = $raw | ConvertFrom-Json } } catch { $j = $null }

$dir = $null; $name = $null; $branch = $null; $session = $null; $agent = $null
if ($j) {
    $dir     = $j.workspace.current_dir; if (-not $dir) { $dir = $j.cwd }
    $name    = $j.worktree.name                     # tier 1: --worktree session
    $branch  = $j.worktree.branch
    if (-not $name) { $name = $j.workspace.git_worktree }   # tier 2: any worktree
    $session = $j.session_name
    $agent   = $j.agent.name
}

$inWorktree = [bool]$name

# Branch from .git/HEAD on disk - no git subprocess.
if (-not $branch -and $dir) {
    $d = $dir; $gitdir = $null; $i = 0
    while ($d -and $i -lt 40) {
        $probe = Join-Path $d '.git'
        if (Test-Path -LiteralPath $probe -PathType Container) { $gitdir = $probe; break }
        if (Test-Path -LiteralPath $probe -PathType Leaf) {
            $line = (Get-Content -LiteralPath $probe -TotalCount 1)
            if ($line -match '^\s*gitdir:\s*(.+?)\s*$') {
                $g = $Matches[1]
                if ($g -match '^([A-Za-z]:[\\/]|[\\/])') { $gitdir = $g } else { $gitdir = Join-Path $d $g }
            }
            break
        }
        $parent = Split-Path -LiteralPath $d -Parent
        if (-not $parent -or $parent -eq $d) { break }
        $d = $parent; $i++
    }
    if ($gitdir) {
        $headFile = Join-Path $gitdir 'HEAD'
        if (Test-Path -LiteralPath $headFile) {
            $head = (Get-Content -LiteralPath $headFile -TotalCount 1)
            if ($head -match '^\s*ref:\s*(.+?)\s*$') { $branch = $Matches[1] -replace '^refs/heads/', '' }
            elseif ($head) { $branch = '@' + $head.Substring(0, [Math]::Min(7, $head.Length)) }
        }
    }
}

$extra = ''
if ($env:WT_SHOW_DIRTY -eq '1' -and $dir) {
    $st = & git -C "$dir" status --porcelain 2>$null
    if ($st) { $extra = ' *' + (@($st).Count) }
}

$parts = @()
if ($inWorktree) { $parts += "$GT $name" } else { $parts += "$GM MAIN" }
if ($branch)  { $parts += $branch }
if ($session) { $parts += $session }
if ($agent)   { $parts += "@$agent" }

$out = ($parts -join $SEP) + $extra
Write-Host $out
exit 0
