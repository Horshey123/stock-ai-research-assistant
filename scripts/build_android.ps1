$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$mobileRoot = Join-Path $projectRoot "mobile"
$androidRoot = Join-Path $mobileRoot "android"
$nodeModules = Join-Path $mobileRoot "node_modules"

Set-Location -LiteralPath $mobileRoot
$Host.UI.RawUI.WindowTitle = "Build Stock AI Android App"

function Find-FirstExistingPath {
    param([string[]]$Candidates)
    foreach ($candidate in $Candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            return $candidate
        }
    }
    return $null
}

$nodeCommand = Get-Command "node.exe" -ErrorAction SilentlyContinue
$nodePath = Find-FirstExistingPath @(
    $(if ($nodeCommand) { $nodeCommand.Source }),
    (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe")
)

if (-not $nodePath) {
    Write-Host "Node.js is not installed." -ForegroundColor Red
    Write-Host "Install the Node.js LTS version from https://nodejs.org and launch again."
    exit 2
}

if (-not (Test-Path -LiteralPath $nodeModules)) {
    Write-Host "Mobile dependencies are missing." -ForegroundColor Red
    Write-Host "Open PowerShell in the mobile folder and run: npm install"
    exit 3
}

Write-Host "1/3 Building the mobile interface..." -ForegroundColor Cyan
& $nodePath (Join-Path $nodeModules "vite\bin\vite.js") build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "2/3 Syncing the Android project..." -ForegroundColor Cyan
& $nodePath (Join-Path $nodeModules "@capacitor\cli\bin\capacitor") sync android
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$javaCommand = Get-Command "java.exe" -ErrorAction SilentlyContinue
$javaPath = Find-FirstExistingPath @(
    $(if ($javaCommand) { $javaCommand.Source }),
    "C:\Program Files\Android\Android Studio\jbr\bin\java.exe"
)

if (-not $javaPath) {
    Write-Host "" 
    Write-Host "The interface and Android project are ready, but Android Studio is not installed." -ForegroundColor Yellow
    Write-Host "Install Android Studio from https://developer.android.com/studio, complete its first-run SDK setup, then launch this file again."
    exit 4
}

$javaBin = Split-Path -Parent $javaPath
$env:JAVA_HOME = Split-Path -Parent $javaBin

$sdkPath = Find-FirstExistingPath @(
    $env:ANDROID_HOME,
    $env:ANDROID_SDK_ROOT,
    (Join-Path $env:LOCALAPPDATA "Android\Sdk")
)
if (-not $sdkPath) {
    Write-Host "Android SDK was not found." -ForegroundColor Red
    Write-Host "Open Android Studio once and finish its Android SDK setup, then launch again."
    exit 5
}

$env:ANDROID_HOME = $sdkPath
$env:ANDROID_SDK_ROOT = $sdkPath

Write-Host "3/3 Generating the APK..." -ForegroundColor Cyan
Set-Location -LiteralPath $androidRoot
& (Join-Path $androidRoot "gradlew.bat") assembleDebug
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$sourceApk = Join-Path $androidRoot "app\build\outputs\apk\debug\app-debug.apk"
$outputDirectory = Join-Path $mobileRoot "dist-apk"
$targetApk = Join-Path $outputDirectory "StockAI-1.0-debug.apk"

New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
Copy-Item -LiteralPath $sourceApk -Destination $targetApk -Force

Write-Host ""
Write-Host "APK generated successfully:" -ForegroundColor Green
Write-Host $targetApk

