from pathlib import Path
import subprocess
from review_core import load_clip,export_review
from clip_engine import FFMPEG
root=Path(__file__).resolve().parents[1]
source=root/"exports"/"videoplayback"/"videoplayback_v04_01_00243s_rev3.mp4"
d=load_clip(source)
d["duration"]=3.0
d["subtitles"]=[x for x in d["subtitles"] if float(x["end"])<=3.0]
d["clip"]=str((root/"samples"/"review-editor-qa"/"fullhd-reedit-test.mp4").resolve())
p=export_review(d)
probe=subprocess.run([FFMPEG,"-hide_banner","-i",str(p)],
                     capture_output=True,text=True,timeout=25)
print("REVIEW_1080_OUTPUT",p,flush=True)
print("REVIEW_1080_META",[t.strip() for t in probe.stderr.splitlines() if "Video:" in t][:1],flush=True)
