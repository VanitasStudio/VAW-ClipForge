from pathlib import Path
from gemini_highlights import process_ai

root=Path(__file__).parent
source=root/"samples"/"spoken-test.mp4"
dest=root/"samples"/"v09-mock-pipeline"

def mock_provider(audio,window_length,desired,key,model,frames):
    return [{
        "start":2.6,"end":14.0,"score":92,
        "title":"Why this workflow is useful",
        "reason":"A complete explanation with a clear ending.",
        "complete":True,"hook":"A useful local workflow",
        "context":"A simple Python automation example",
        "payoff":"Always check the output before posting."
    }]

events=[]
result=process_ai(source,dest,clips=1,seconds=30,provider=mock_provider,
                  visual=False,render=False,dry_run=True,context_aware=True,
                  log=lambda x:(events.append(x),print("LOG",x,flush=True)))
pick=result["clips"][0]
print("PICK",pick,flush=True)
assert result["version"]=="v1.0"
assert result["candidate_count"]==1
assert result["ranked_candidates"][0]["selection_status"]=="selected"
assert pick["editorial_score"]==92.0
assert pick["duration"] != 30
assert pick["boundary_alignment"]["start"]=="sentence"
assert pick["boundary_alignment"]["end"]=="sentence"
assert pick["start"] <= 2.6 and pick["end"] >= 14.0
print("END_TO_END_MOCK_PIPELINE_PASS",flush=True)
