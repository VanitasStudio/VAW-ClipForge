"""End-to-end UI integration QA, public CC BY Blender Foundation test clip.
Runs locally without showing UI; no Gemini request or YouTube publication.
"""
from pathlib import Path
import json
import time
from tkinter import messagebox
from clipforge_gui import ClipForge
from clip_engine import FFMPEG
import subprocess

messagebox.askyesno=lambda *args,**kwargs:True
messagebox.showinfo=lambda *args,**kwargs:print("UI_INFO",args[0],flush=True)
messagebox.showerror=lambda *args,**kwargs:print("UI_ERROR",args,flush=True)
messagebox.showwarning=lambda *args,**kwargs:print("UI_WARNING",args,flush=True)

app=ClipForge()
app.root.withdraw()
app.source_type.set("Video URL")
app.src.set("https://www.youtube.com/watch?v=qzfWVYJNmAM")
app.mode.set("Audio Activity (offline)")
app.caption.set(False)
app.burn.set(False)
app.count.set(1)
app.seconds.set(8)
app.resolution.set("1080p")
app.scenedetect.set(False)
app.autoframe.set(True)
app.start()
start=time.monotonic()
while app.busy and time.monotonic()-start<180:
    app.root.update()
    time.sleep(.1)
app.root.update()
print("UI_FINISHED",not app.busy,"SECONDS",round(time.monotonic()-start,1),flush=True)
if app.last_export:
    print("EXPORT_LOCATION",app.last_export,flush=True)
    candidates=list(Path(app.last_export).glob("*_v04_*.mp4"))
    print("MP4_COUNT",len(candidates),flush=True)
    if candidates:
        file=max(candidates,key=lambda p:p.stat().st_mtime)
        meta=subprocess.run([FFMPEG,"-hide_banner","-i",str(file)],capture_output=True,text=True,timeout=30)
        print("VIDEO_META",[line.strip() for line in meta.stderr.splitlines() if "Video:" in line][:1],flush=True)
        print("OUTPUT_FILE",str(file),file.stat().st_size,flush=True)
    else:
        raise RuntimeError("UI did not export any clip")
else:
    raise RuntimeError("UI never selected an export folder")
log=app.logview.get("1.0","end")
print("LOG_TAIL",log[-1500:],flush=True)
app.root.destroy()
if app.busy:
    raise TimeoutError("UI integration exceeded 180 sec")
