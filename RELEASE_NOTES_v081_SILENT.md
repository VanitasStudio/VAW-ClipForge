# VAW ClipForge v0.8.1 - Silent Background Processing

Installed on VAWRIEL-PC (2026-11-03).

## Fix
- FFmpeg, PowerShell DPAPI, thumbnail extraction, audio preprocessing and video rendering now use silent Windows subprocess startup with CREATE_NO_WINDOW, STARTF_USESHOWWINDOW and SW_HIDE.
- ClipForge opening Review Studio is also started through the hidden process wrapper. This does NOT hide the Review Studio graphical interface.
- yt-dlp FFmpeg merger uses its own Popen subclass; the Windows startup info is explicitly SW_HIDE.
- The Desktop shortcut already points at pythonw.exe, so the GUI itself does not create a terminal.
- Errors remain visible in ClipForge Activity Log; background process stderr is still captured.

## Verified
- PowerShell read test returned successfully with no visible child window.
- Original encrypted Gemini key successfully decrypted with hidden PowerShell; key content was not logged.
- FFmpeg local video probe works.
- A 2-second PowerShell child was monitored: 0 visible windows for its PID.
- yt-dlp Popen startup configuration SW_HIDE confirmed.
- Offline clipping smoke from synthetic source succeeded with a valid MP4, and invisible child process launching.
- Original media and previous exports were not modified.

## Notes
- This applies to processes started internally by ClipForge, not standalone PowerShell windows launched manually.
- Standard app dialogs (file picker, confirmation and export/error messages) remain, because they are not terminal windows.
- To apply the update, restart ClipForge. Shortcuts should launch pythonw.exe.