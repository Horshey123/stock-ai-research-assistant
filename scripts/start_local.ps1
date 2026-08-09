$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$configPath = Join-Path $projectRoot ".env.local"
$configTemplatePath = Join-Path $projectRoot ".env.local.example"

Set-Location -LiteralPath $projectRoot
$Host.UI.RawUI.WindowTitle = "Stock AI Local Server"

function Import-DotEnvFile {
    param([Parameter(Mandatory = $true)][string]$Path)

    foreach ($rawLine in Get-Content -LiteralPath $Path -Encoding UTF8) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            continue
        }

        $separatorIndex = $line.IndexOf("=")
        if ($separatorIndex -le 0) {
            continue
        }

        $name = $line.Substring(0, $separatorIndex).Trim()
        $value = $line.Substring($separatorIndex + 1).Trim()

        if (
            $value.Length -ge 2 -and
            (($value.StartsWith('"') -and $value.EndsWith('"')) -or
             ($value.StartsWith("'") -and $value.EndsWith("'")))
        ) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        $existingValue = [Environment]::GetEnvironmentVariable($name, "Process")
        if ([string]::IsNullOrWhiteSpace($existingValue)) {
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

if (-not (Test-Path -LiteralPath $pythonPath)) {
    Write-Host "Python environment was not found:" -ForegroundColor Red
    Write-Host "  $pythonPath"
    Write-Host ""
    Write-Host "Run scripts\setup.ps1 once, then double-click the launcher again."
    exit 1
}

if (
    -not (Test-Path -LiteralPath $configPath) -and
    [string]::IsNullOrWhiteSpace($env:DEEPSEEK_API_KEY)
) {
    Copy-Item -LiteralPath $configTemplatePath -Destination $configPath
    Write-Host "A local configuration file has been created:" -ForegroundColor Yellow
    Write-Host "  $configPath"
    Write-Host ""
    Write-Host "Enter your NEW DeepSeek API key, save the file, then launch again."
    Start-Process -FilePath "notepad.exe" -ArgumentList $configPath
    exit 2
}

if (Test-Path -LiteralPath $configPath) {
    Import-DotEnvFile -Path $configPath
}

if ([string]::IsNullOrWhiteSpace($env:DEEPSEEK_API_KEY)) {
    Write-Host "DEEPSEEK_API_KEY is empty in .env.local." -ForegroundColor Red
    Write-Host "Enter the key, save the file, then launch again."
    Start-Process -FilePath "notepad.exe" -ArgumentList $configPath
    exit 2
}

$listenHost = if ($env:STOCK_AI_HOST) { $env:STOCK_AI_HOST } else { "127.0.0.1" }
$listenPort = if ($env:STOCK_AI_PORT) { $env:STOCK_AI_PORT } else { "8000" }
$docsHost = if ($listenHost -eq "0.0.0.0") { "127.0.0.1" } else { $listenHost }
$docsUrl = "http://${docsHost}:${listenPort}/docs"

Write-Host ""
Write-Host "Stock AI backend is starting..." -ForegroundColor Green
Write-Host "API docs: $docsUrl"
Write-Host "Close this window or press Ctrl+C to stop the backend."
Write-Host ""

if ($env:STOCK_AI_NO_BROWSER -ne "1") {
    $browserCommand = "Start-Sleep -Seconds 2; Start-Process '$docsUrl'"
    Start-Process -FilePath "powershell.exe" -WindowStyle Hidden -ArgumentList @(
        "-NoLogo",
        "-NoProfile",
        "-Command",
        $browserCommand
    )
}

& $pythonPath -m uvicorn stock_ai.api.main:app `
    --host $listenHost `
    --port $listenPort `
    --workers 1

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "The backend stopped with exit code $LASTEXITCODE." -ForegroundColor Red
    exit $LASTEXITCODE
}
