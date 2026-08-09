$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

Set-Location $projectRoot

if (-not (Test-Path -LiteralPath $venvPython)) {
    python -m venv .venv
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements.txt
& $venvPython -m pip install -e . --no-deps

Write-Host ""
Write-Host "环境安装完成。运行样例："
Write-Host ".\.venv\Scripts\python.exe -m stock_ai 600519 --skip-news --skip-reports --no-cache"
Write-Host ""
Write-Host "已有数据时生成DeepSeek分析："
Write-Host '$env:DEEPSEEK_API_KEY="你的API密钥"'
Write-Host ".\.venv\Scripts\python.exe -m stock_ai 600519 --input-json .\data\output\600519.json --analyze"
Write-Host ""
Write-Host "启动FastAPI后端："
Write-Host ".\scripts\start_api.ps1"
