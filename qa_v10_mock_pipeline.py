import json
from pathlib import Path
from gemini_highlights import process_ai

root=Path(__file__).parent
source=root/"samples"/"spoken-test.mp4"
dest=root/"samples"/"v10-mock-pipeline"
def mock_provider(audio,window_length,desired,key,model,frames):
    return [{
      "start":2.6,"end":14.0,"score":86,"complete":True,
      "title":"Why this workflow is useful",
      "reason":"A complete explanation with a practical payoff.",
      "hook":"A simple problem with a useful solution.",
      "context":"The example demonstrates local file automation.",
      "payoff":"Always inspect the output before posting.",
      "hook_strength":91,"payoff_strength":94,"context_independence":90,
      "clarity":92,"visual_interest":83,"pacing":88,"novelty":85,
      "retention_potential":90,"visual_type":"animation",
      "visual_notes":"The sampled frame shows a clear workflow diagram.",
      "retention_risk":"none",
      "retention_reason":"A concrete question is answered with a useful takeaway.",
      "edit_suggestion":"Keep the diagram on screen until the final takeaway."
    }]
events=[]
result=process_ai(source,dest,clips=1,seconds=30,provider=mock_provider,
                  visual=False,render=False,dry_run=False,context_aware=True,
                  log=lambda x:(events.append(x),print("LOG",x,flush=True)))
manifest_path=dest/"ai-highlights.json"
report_path=dest/"ai-editorial-report.html"
assert result["version"]=="v1.0"
assert result["ranked_candidates"][0]["visual_type"]=="animation"
assert result["clips"][0]["editorial_score"]>85
assert manifest_path.is_file() and report_path.is_file()
stored=json.loads(manifest_path.read_text(encoding="utf-8"))
assert stored["editorial_report"]==str(report_path)
assert "Why this workflow is useful" in report_path.read_text(encoding="utf-8")
print("MANIFEST_VERSION",stored["version"])
print("EDITORIAL_SCORE",stored["clips"][0]["editorial_score"])
print("REPORT_PATH",report_path)
print("V10_MOCK_PIPELINE_PASS")
