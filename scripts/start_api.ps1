$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

Set-Location $projectRoot

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "找不到项目Python环境，请先运行：.\scripts\setup.ps1"
}

if (-not $env:DEEPSEEK_API_KEY) {
    Write-Warning "尚未设置DEEPSEEK_API_KEY。后端可以启动，但新的AI分析任务会失败。"
}

Write-Host "正在启动股票AI后端..."
Write-Host "接口文档：http://127.0.0.1:8000/docs"
Write-Host "按 Ctrl+C 停止后端。"
Write-Host ""

& $venvPython -m uvicorn stock_ai.api.main:app --reload --host 127.0.0.1 --port 8000
