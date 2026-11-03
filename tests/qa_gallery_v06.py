"""Temporary UI screenshot QA of subtitle-style gallery, exits automatically."""
import ctypes
from ctypes import wintypes
from pathlib import Path
from PIL import ImageGrab
from review_editor import ReviewEditor
ed=ReviewEditor()
def capture():
    handles=[]
    win=ctypes.windll.user32
    @ctypes.WINFUNCTYPE(ctypes.c_bool,wintypes.HWND,wintypes.LPARAM)
    def callback(hwnd,param):
        n=win.GetWindowTextLengthW(hwnd)
        if n and win.IsWindowVisible(hwnd):
            buf=ctypes.create_unicode_buffer(n+1)
            win.GetWindowTextW(hwnd,buf,n+1)
            if "Subtitle Modes" in buf.value:
                handles.append(hwnd)
        return True
    win.EnumWindows(callback,0)
    if handles:
        image=ImageGrab.grab(window=handles[0])
        path=Path(__file__).resolve().parents[1]/"samples"/"review-v06-qa"/"subtitle-gallery.png"
        image.save(path)
        print("GALLERY_QA",path,image.size,flush=True)
    else:
        print("GALLERY_WINDOW_NOT_FOUND",flush=True)
    ed.app.after(350,ed.on_close)
ed.app.after(800,ed.open_style_gallery)
ed.app.after(1800,capture)
ed.app.mainloop()
