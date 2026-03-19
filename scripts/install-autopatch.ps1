#!/usr/bin/env pwsh
# Claude Parrot — Auto-Patch Installer
#
# Adds a line to your PowerShell profile that silently re-patches
# Claude Code's spinner on every terminal open. If already patched,
# it does nothing (zero overhead).
#
# Usage: pwsh scripts/install-autopatch.ps1
#        pwsh scripts/install-autopatch.ps1 -Uninstall

param([switch]$Uninstall)

$scriptDir = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$patchScript = Join-Path (Join-Path $scriptDir "scripts") "patch-claude.js"
$marker = "# claude-parrot-autopatch"
$line = "node `"$patchScript`" --quiet 2>`$null $marker"

$profilePath = $PROFILE

if ($Uninstall) {
    if (Test-Path $profilePath) {
        $content = Get-Content $profilePath | Where-Object { $_ -notmatch "claude-parrot-autopatch" }
        Set-Content $profilePath $content
        Write-Host "  Removed auto-patch from $profilePath"
    } else {
        Write-Host "  No profile found at $profilePath"
    }
    return
}

# Create profile if it doesn't exist
if (!(Test-Path $profilePath)) {
    New-Item -Path $profilePath -ItemType File -Force | Out-Null
    Write-Host "  Created PowerShell profile at $profilePath"
}

# Check if already installed
$existing = Get-Content $profilePath | Where-Object { $_ -match "claude-parrot-autopatch" }
if ($existing) {
    Write-Host "  Auto-patch already installed in $profilePath"
    return
}

# Append the auto-patch line
Add-Content $profilePath "`n$line"
Write-Host ""
Write-Host "  Claude Parrot auto-patch installed!"
Write-Host ""
Write-Host "  Added to: $profilePath"
Write-Host "  Every new terminal will silently ensure the parrot spinner is active."
Write-Host ""
Write-Host "  To remove: pwsh scripts/install-autopatch.ps1 -Uninstall"
Write-Host ""
