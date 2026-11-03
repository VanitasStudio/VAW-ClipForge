from pathlib import Path
from smart_reframe import frame_centers, smart_render
root=Path(__file__).resolve().parent
src=root/"samples"/"animated-object-qa.mp4"
for mode in ("universal","people","motion","center"):
    width,height,positions,counts,kind=frame_centers(src,[],subject_mode=mode)
    print("MODE",mode,"SAMPLES",len(positions),"DECISIONS",counts,"START",positions[0] if positions else None,"END",positions[-1] if positions else None,flush=True)
out=root/"samples"/"universal-auto-preview.mp4"
metadata=smart_render(src,out,subject_mode="universal",auto=True,scenes=True)
print("UNIVERSAL_MP4",out,out.stat().st_size,"META",metadata["mode"],flush=True)
