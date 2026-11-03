"""Exercise Review Studio's drag box and track callback on authorized local video."""
from types import SimpleNamespace
from pathlib import Path
from clipforge.review_editor import ReviewEditor
clip=Path(__file__).resolve().parents[1]/"exports"/"videoplayback"/"videoplayback_v04_01_00243s_rev3.mp4"
editor=ReviewEditor(clip)
def act():
    editor.position.set(0.1)
    editor.scrub()
    editor.arm_subject()
    editor.selection_start(SimpleNamespace(x=150,y=50))
    editor.selection_drag(SimpleNamespace(x=280,y=228))
    editor.selection_end(SimpleNamespace(x=280,y=228))
    print("UI_SELECTION_SUBMITTED",editor.busy,flush=True)
def done():
    result=editor.data.get("subject_tracks",[]) if editor.data else []
    print("UI_TRACKS",len(result),flush=True)
    if result:
        print("UI_TRACK_SAMPLE",result[-1]["method"],len(result[-1]["points"]),
              result[-1].get("bbox"),flush=True)
    print("UI_STATUS",editor.status.get(),flush=True)
    editor.on_close()
editor.app.after(950,act)
editor.app.after(7000,done)
editor.app.mainloop()
