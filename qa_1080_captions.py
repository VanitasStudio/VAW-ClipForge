from pathlib import Path
import subprocess
from clip_engine import FFMPEG
from smart_reframe import export_v04
root=Path(__file__).parent
dest=root/"samples"/"fullhd-caption-qa"
result=export_v04(root/"samples"/"spoken-test.mp4",dest,
                  [{"start":0.5,"duration":6,"score":100,"title":"QA speech"}],
                  auto=True,scenes=False,captions=True,burn=True,
                  style="karaoke",subject_mode="universal",resolution="1080p")
for row in result["clips"]:
    print("QA1080CAPTION",row.get("ok"),row.get("caption"),
          row.get("caption_error"),row.get("error"),flush=True)
    if row.get("ok"):
        file=Path(row["output"])
        p=subprocess.run([FFMPEG,"-hide_banner","-i",str(file)],
                         capture_output=True,text=True,timeout=30)
        print("VIDEO_STREAM",[x.strip() for x in p.stderr.splitlines() if "Video:" in x][:1],flush=True)
