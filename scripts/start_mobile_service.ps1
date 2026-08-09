$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$backendLauncher = Join-Path $PSScriptRoot "start_local.ps1"
$tailscaleCandidates = @(
    (Join-Path $env:ProgramFiles "Tailscale\tailscale.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Tailscale\tailscale.exe")
)

$tailscaleCommand = Get-Command "tailscale.exe" -ErrorAction SilentlyContinue
$tailscalePath = if ($tailscaleCommand) {
    $tailscaleCommand.Source
} else {
    $tailscaleCandidates |
        Where-Object { $_ -and (Test-Path -LiteralPath $_) } |
        Select-Object -First 1
}

Set-Location -LiteralPath $projectRoot
$Host.UI.RawUI.WindowTitle = "Stock AI Mobile Service"

if (-not $tailscalePath) {
    Write-Host "Tailscale is not installed." -ForegroundColor Red
    Write-Host "Install Tailscale for Windows, sign in, then launch again."
    Write-Host "https://tailscale.com/download/windows"
    exit 3
}

Write-Host "Checking Tailscale..." -ForegroundColor Cyan
& $tailscalePath status | Out-Host
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Tailscale is not connected. Open Tailscale and sign in first." -ForegroundColor Red
    exit 4
}

Write-Host ""
Write-Host "Configuring private HTTPS access to port 8000..." -ForegroundColor Cyan
& $tailscalePath serve --bg 8000 | Out-Host
if ($LASTEXITCODE -ne 0) {
    Write-Host "Tailscale Serve setup failed. Follow the URL shown above and allow HTTPS." -ForegroundColor Red
    exit 5
}

Write-Host ""
Write-Host "Use the HTTPS address below in the Android app settings:" -ForegroundColor Green
& $tailscalePath serve status | Out-Host
Write-Host ""

$env:STOCK_AI_NO_BROWSER = "1"
& $backendLauncher
exit $LASTEXITCODE
