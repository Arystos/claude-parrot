#Requires -RunAsAdministrator
# Install PartyParrot font and set up font linking for Windows Terminal
# Run this script as Administrator (right-click > Run as Administrator)

$ErrorActionPreference = "Stop"

$fontSrc = Join-Path $PSScriptRoot "PartyParrot.ttf"
$fontDest = "$env:LOCALAPPDATA\Microsoft\Windows\Fonts\PartyParrot.ttf"
$fontLinkPath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\FontLink\SystemLink"
$fontRegPath = "HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"

# 1. Copy font to user fonts directory
Write-Host "  Copying font..." -ForegroundColor Cyan
Copy-Item -Path $fontSrc -Destination $fontDest -Force
Write-Host "  -> $fontDest"

# 2. Register font in user registry
Write-Host "  Registering font..." -ForegroundColor Cyan
Set-ItemProperty -Path $fontRegPath -Name "PartyParrot (TrueType)" -Value $fontDest -Type String
Write-Host "  -> HKCU font registry entry added"

# 3. Add font linking for Cascadia Mono (default Windows Terminal font)
Write-Host "  Setting up font linking..." -ForegroundColor Cyan
$linkValue = @("PartyParrot.ttf,PartyParrot")

# Also link for Cascadia Code in case user switches
foreach ($fontName in @("Cascadia Mono", "Cascadia Code", "Consolas", "Cascadia Mono NF", "Cascadia Code NF")) {
    $existing = (Get-ItemProperty -Path $fontLinkPath -Name $fontName -ErrorAction SilentlyContinue).$fontName
    if ($existing) {
        # Append our font to existing links (if not already there)
        if ($existing -notcontains "PartyParrot.ttf,PartyParrot") {
            $newLinks = @($existing) + $linkValue
            Set-ItemProperty -Path $fontLinkPath -Name $fontName -Value $newLinks -Type MultiString
            Write-Host "  -> Appended to existing links for $fontName"
        } else {
            Write-Host "  -> Already linked for $fontName"
        }
    } else {
        New-ItemProperty -Path $fontLinkPath -Name $fontName -Value $linkValue -PropertyType MultiString -Force | Out-Null
        Write-Host "  -> Created font link for $fontName"
    }
}

Write-Host ""
Write-Host "  Done! Restart Windows Terminal to see the changes." -ForegroundColor Green
Write-Host "  Then test with: node preview.js --font" -ForegroundColor Yellow
Write-Host ""
