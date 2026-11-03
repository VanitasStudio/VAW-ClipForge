@echo off
cd /d "%~dp0"
if exist "C:\Python314\pythonw.exe" (
  start "" "C:\Python314\pythonw.exe" "%~dp0review_editor.py" --clip "%~dp0exports\videoplayback\videoplayback_v04_01_00243s_rev3.mp4"
) else (
  "C:\Python314\python.exe" "%~dp0review_editor.py"
)
