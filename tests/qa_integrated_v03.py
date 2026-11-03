from pathlib import Path
from clipforge.gemini_highlights import process_ai
from clipforge.auto_captions import caption_output
source=Path("samples/spoken-test.mp4")
dest=Path("samples/v03-integrated-test")
result=process_ai(source,dest,clips=1,seconds=8,style="blur",
                  model="gemini-3.5-flash-lite",visual=True)
clips=[Path(x["path"]) for x in result["clips"] if Path(x["path"]).exists()]
print("INTEGRATION_MP4_COUNT",len(clips),flush=True)
print("INTEGRATION_CAPTION_RESULTS",caption_output(clips,size="base",burn=True),flush=True)
