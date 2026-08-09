@echo off
setlocal
cd /d "%~dp0"

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_local.ps1"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    if "%EXIT_CODE%"=="2" (
        echo Save .env.local, close Notepad, and double-click this file again.
    ) else (
        echo Startup failed. Review the message above.
    )
    pause
)

endlocal
