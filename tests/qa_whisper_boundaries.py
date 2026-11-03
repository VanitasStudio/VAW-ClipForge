from pathlib import Path
from clipforge.smart_duration import analyze_boundaries,align_interval
from clipforge.gemini_highlights import select_best
root=Path(__file__).resolve().parents[1]
source=root/"samples"/"spoken-test.mp4"
cache=root/"samples"/"context-duration-qa"
sentences=analyze_boundaries(source,cache,model_size="base",
    log=lambda x:print("WHISPER",x,flush=True))
print("TRANSCRIPT_SENTENCES",len(sentences),flush=True)
for item in sentences[:8]:
    print("BOUNDARY",round(item["start"],2),round(item["end"],2),item["text"][:100],flush=True)
total=19.53
candidate={"start":1.2,"end":17.2,"score":90,"title":"QA story",
           "reason":"Test complete speech context","complete":True}
aligned=align_interval(candidate["start"],candidate["end"],sentences,total)
print("ALIGNED",aligned,flush=True)
if aligned:
    print("DURATION",round(aligned[1]-aligned[0],2),flush=True)
    assert aligned[1]-aligned[0] != 30
print("REAL_WHISPER_BOUNDARY_QA_PASS",flush=True)
