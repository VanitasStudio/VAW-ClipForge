"""Capture the editor WINDOW only for visual QA on the authorized PC."""
import ctypes
import time
from pathlib import Path
from PIL import ImageGrab
from ctypes import wintypes
user=ctypes.windll.user32
titles=[]
@ctypes.WINFUNCTYPE(ctypes.c_bool,wintypes.HWND,wintypes.LPARAM)
def callback(hwnd,param):
    if not user.IsWindowVisible(hwnd):
        return True
    n=user.GetWindowTextLengthW(hwnd)
    if n:
        b=ctypes.create_unicode_buffer(n+1)
        user.GetWindowTextW(hwnd,b,n+1)
        if "Universal Object Review" in b.value:
            titles.append((hwnd,b.value))
    return True
user.EnumWindows(callback,0)
if not titles:
    print("EDITOR_WINDOW_NOT_FOUND")
else:
    hwnd,title=titles[0]
    # Do not interrupt the user's foreground app
    # capture only the target window
    time.sleep(1.2)
    class RECT(ctypes.Structure):
        _fields_=[("left",ctypes.c_long),("top",ctypes.c_long),
                  ("right",ctypes.c_long),("bottom",ctypes.c_long)]
    rect=RECT()
    user.GetWindowRect(hwnd,ctypes.byref(rect))
    print("WINDOW",title,rect.left,rect.top,rect.right,rect.bottom,flush=True)
    bbox=(max(0,rect.left),max(0,rect.top),rect.right,rect.bottom)
    img=ImageGrab.grab(window=hwnd)
    output=Path(__file__).resolve().parents[1]/"samples"/"review-editor-qa"/"editor-window-direct.png"
    img.save(output)
    print("CAPTURE_FILE",output,img.size,flush=True)
