from pathlib import Path
from review_core import load_clip,export_review
from subject_tracking import track_subject
base=Path(__file__).resolve().parents[1]
src=base/"exports"/"videoplayback"/"videoplayback_v04_01_00243s_rev3.mp4"
data=load_clip(src)
data["duration"]=3.0
data["subtitles"]=[row for row in data["subtitles"] if row["end"]<=3.0]
bbox=(150/450,50/255,280/450,228/255)
track=track_subject(data["source"],data["source_start"],0.12,data["duration"],
                    (150+280)/(2*450),(50+228)/(2*255),
                    data["cuts"],seconds=3,bbox=bbox)
data["subject_tracks"]=[track]
dest=base/"samples"/"review-v07-qa"
dest.mkdir(exist_ok=True)
data["clip"]=str((dest/"documentary-object.mp4").resolve())
out=export_review(data)
print("RENDER_V07_TRACK_POINTS",len(track["points"]))
print("RENDER_V07_OK",out,out.stat().st_size)
