from pathlib import Path
from types import SimpleNamespace
import time
from review_editor import ReviewEditor
clip=Path(__file__).resolve().parents[1]/"exports"/"videoplayback"/"videoplayback_v04_01_00243s_rev3.mp4"
ed=ReviewEditor(clip)
for _ in range(9):
    ed.app.update()
    time.sleep(.09)
assert ed.data is not None,"Editor failed to load test video"
ed.position.set(.12)
ed.scrub()
ed.arm_subject()
ed.selection_start(SimpleNamespace(x=150,y=50))
ed.selection_drag(SimpleNamespace(x=280,y=228))
ed.selection_end(SimpleNamespace(x=280,y=228))
start=time.monotonic()
while ed.busy and time.monotonic()-start<6:
    ed.app.update()
    time.sleep(.15)
ed.app.update()
print("GUI_DRAG_TRACKS",len(ed.data.get("subject_tracks",[])),"BUSY",ed.busy,flush=True)
print("STATUS",ed.status.get(),flush=True)
assert len(ed.data.get("subject_tracks",[]))>0,"No object track saved by UI"
ed.on_close()
