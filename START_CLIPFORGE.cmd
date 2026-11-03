@echo off
cd /d "%~dp0"
if exist "C:\Python314\pythonw.exe" (
  start "" "C:\Python314\pythonw.exe" "%~dp0clipforge_gui.py"
) else (
  "C:\Python314\python.exe" "%~dp0clipforge_gui.py"
)
