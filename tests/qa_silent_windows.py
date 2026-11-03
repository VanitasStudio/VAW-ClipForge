"""QA silent process spawning on Windows, no credentials printed."""
import ctypes
import os
import subprocess
import time
from ctypes import wintypes
from pathlib import Path

from silent_process import run,popen,verify_hidden_flags
from clip_engine import FFMPEG,probe_duration
from secure_config import has_key,load_key

print("HIDDEN_FLAGS",verify_hidden_flags(),flush=True)
powershell=run(
    ["powershell.exe","-NoProfile","-NonInteractive","-Command",
     "Write-Output 'PS_HIDDEN_OK'"],
    capture_output=True,text=True,timeout=25)
print("POWERSHELL_RC",powershell.returncode,"STDOUT",powershell.stdout.strip(),flush=True)
assert powershell.returncode==0 and "PS_HIDDEN_OK" in powershell.stdout

video=Path(__file__).resolve().parents[1]/"samples"/"spoken-test.mp4"
print("PROBE_SECONDS",round(probe_duration(video),2),flush=True)

# Enumerate ONLY windows owned by our background child. No unrelated windows.
user32=ctypes.windll.user32
child=popen(["powershell.exe","-NoProfile","-NonInteractive","-Command",
             "Start-Sleep -Seconds 2; Write-Output 'DONE'"],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            text=True,stdin=subprocess.DEVNULL)
@ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
def visit(hwnd,arg):
    process_id=wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd,ctypes.byref(process_id))
    if process_id.value==child.pid and user32.IsWindowVisible(hwnd):
        found.append(hwnd)
    return True
found=[]
for _ in range(8):
    user32.EnumWindows(visit,0)
    time.sleep(.13)
stdout,stderr=child.communicate(timeout=20)
print("CHILD_PID",child.pid,"VISIBLE_WINDOWS",len(set(found)),
      "OUTPUT",stdout.strip(),flush=True)
assert child.returncode==0 and stdout.strip()=="DONE" and not found

print("DPAPI_CONFIGURED",has_key(),flush=True)
if has_key():
    key=load_key()
    # No secret output; verifies PowerShell DPAPI worked in hidden mode.
    print("DPAPI_HIDDEN_READ_OK",bool(key) and len(key)>=20,flush=True)
    assert len(key)>=20
print("ALL_SILENT_PROCESS_TESTS_PASS",flush=True)
