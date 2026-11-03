from pathlib import Path
from clipforge.review_core import load_clip,make_ass,validate,export_review
from clipforge.subject_tracking import track_subject
from clipforge.subtitle_presets import PRESETS,preview_image
p=Path("exports/videoplayback/videoplayback_v04_01_00243s_rev3.mp4")
d=load_clip(p)
print("CUTS",d["cuts"],flush=True)
for s in PRESETS:
    ass=make_ass(d["subtitles"],s.id)
    print("SUBTITLE",s.id,"events",ass.count("Dialogue:"),"chars",len(ass),flush=True)
    image=preview_image(s.id)
    path=Path("samples")/f"preview-caption-{s.id}.png"
    image.save(path)
    assert "Style: Selected" in ass
d["caption_style"]="gaming"
d["duration"]=6.0
d["subtitles"]=[x for x in d["subtitles"] if x["end"]<=6.0]
d["transitions"]={"2.00":"dip"}
d["cuts"]=[2.0]
validate(d)
print("TRANSITION_CONFIG_VALID",flush=True)
print("TRACK_START",flush=True)
try:
    track=track_subject(d["source"],d["source_start"],0,d["duration"],0.5,0.45,d["cuts"],seconds=1.4)
    print("SUBJECT_TRACK_OK",len(track["points"]),flush=True)
    d["subject_tracks"]=[track]
except Exception as exc:
    print("SUBJECT_TRACK_EXCEPTION",type(exc).__name__,str(exc),flush=True)
from pathlib import Path
dest=Path("samples/review-v06-qa")
dest.mkdir(parents=True,exist_ok=True)
d["clip"]=str((dest/"v06-sample.mp4").resolve())
output=export_review(d)
print("FULL_RENDERED",output,output.stat().st_size,flush=True)
