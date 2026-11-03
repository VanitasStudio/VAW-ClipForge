@echo off
setlocal
set "APP=%~dp0dist\VAW-ClipForge.exe"
if exist "%APP%" (
  start "" "%APP%"
  exit /b 0
)
echo VAW ClipForge.exe is not built yet.
echo Build it with: powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
pause
