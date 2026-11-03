from pathlib import Path
import gemini_highlights as g
g.sample_windows=lambda total:[(0.0,9.0),(9.0,total-9.0)]
calls=[0]
def provider(audio,length,seconds,key,model,frames):
    calls[0]+=1
    if calls[0]>=2:
        raise RuntimeError("Gemini returned malformed or incomplete JSON")
    return [{"start":1.0,"end":7.0,"score":95,"title":"verified test","reason":"mock"}]
result=g.process_ai("samples/spoken-test.mp4","samples/qa-partial",
                    clips=1,seconds=5,model="gemini-3.6-flash",
                    provider=provider,visual=False)
print("PARTIAL_RESULT_COUNT",len(result["clips"]),"FAILED_SECTIONS",
      len(result["sections_failed"]),"API_CALLS",calls[0],flush=True)
calls2=[0]
def next_provider(audio,length,seconds,key,model,frames):
    calls2[0]+=1
    return [{"start":1.0,"end":7.0,"score":90,"title":"retry test","reason":"mock"}]
result2=g.process_ai("samples/spoken-test.mp4","samples/qa-partial",
                     clips=2,seconds=5,model="gemini-3.6-flash",
                     provider=next_provider,visual=False)
print("RESUME_RESULT_COUNT",len(result2["clips"]),"NEW_API_CALLS",calls2[0],flush=True)
