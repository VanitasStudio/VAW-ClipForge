"""Production smoke: offline engine+subtitle, no visible console windows."""
from pathlib import Path
from clipforge.clip_engine import probe_duration,process
from clipforge.silent_process import verify_hidden_flags
from clipforge.secure_config import has_key,load_key
from clipforge.smart_reframe import export_v04
from clipforge.url_source import _ensure_ffmpeg
import yt_dlp.utils
import os,subprocess,sys

root=Path(__file__).resolve().parents[1]
source=root/"samples"/"spoken-test.mp4"
target=root/"samples"/"silent-qa"
print("STARTUP",verify_hidden_flags(),flush=True)
ff=Path(_ensure_ffmpeg())
print("MERGER_READY",ff.is_file(),flush=True)
if os.name=="nt":
    si=yt_dlp.utils.Popen._startupinfo
    print("YTDLP_HIDE",(si.dwFlags & subprocess.STARTF_USESHOWWINDOW)!=0,
          si.wShowWindow==subprocess.SW_HIDE,flush=True)
data=process(source,target,clips=1,seconds=5,style="fit",
             dry_run=True,log=lambda x:print("OFFLINE",x,flush=True))
result=export_v04(source,target,data["clips"],auto=False,
                   captions=False,burn=False,resolution="720p",
                   log=lambda x:print("RENDER",x,flush=True))
passed=[x["output"] for x in result["clips"] if x.get("ok")]
print("RENDER_SUCCESS",len(passed),[Path(x).stat().st_size for x in passed],flush=True)
assert len(passed)==1
print("HIDDEN_SMOKE_PASS",flush=True)
