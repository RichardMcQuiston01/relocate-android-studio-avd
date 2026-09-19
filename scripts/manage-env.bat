@echo off
REM Runs Manage-Env.ps1 from the Windows Command Line (cmd.exe).
REM Usage: manage-env.bat init|set|get|list|edit [args...]

setlocal

set "SCRIPT_DIR=%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%Manage-Env.ps1" %*

exit /b %ERRORLEVEL%
