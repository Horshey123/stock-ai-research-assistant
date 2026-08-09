@echo off
chcp 65001 >nul
set "PROJECT_DIR=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PROJECT_DIR%scripts\build_android.ps1"
if errorlevel 1 (
  echo.
  echo Build stopped. Review the message above.
  pause
  exit /b 1
)
echo.
pause

