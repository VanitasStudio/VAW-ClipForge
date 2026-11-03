import json
from unittest.mock import patch
from gemini_highlights import request_gemini

sample={"clips":[{"start":4.0,"end":41.0,"score":94,"complete":True,
 "title":"Why the result matters","reason":"A complete mini-story with payoff.",
 "hook":"An unexpected result","context":"The experiment setup","payoff":"The surprising outcome",
 "hook_strength":96,"payoff_strength":94,"context_independence":92,"clarity":90,
 "visual_interest":86,"pacing":88,"novelty":84,"retention_potential":91,
 "visual_type":"animation","visual_notes":"An animated diagram illustrates the result.",
 "retention_risk":"none","retention_reason":"The opening question is resolved.",
 "edit_suggestion":"Hold on the reveal for a beat."}]}
class FakeResponse:
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self,n=-1):
        body={"candidates":[{"content":{"parts":[{"text":json.dumps(sample)}]}}]}
        return json.dumps(body).encode()

captured=[]
def fake_urlopen(req,timeout=0):
    captured.append(json.loads(req.data.decode("utf-8")))
    return FakeResponse()

with patch("urllib.request.urlopen",fake_urlopen):
    rows=request_gemini(b"synthetic-audio",60,30,"not-a-real-key",
                        model="gemini-3.5-flash-lite")
schema=captured[0]["generationConfig"]["responseSchema"]["properties"]["clips"]["items"]["properties"]
assert {"complete","hook","context","payoff"}.issubset(schema)
assert rows[0]["complete"] is True and rows[0]["payoff"]=="The surprising outcome"
assert rows[0]["end"]-rows[0]["start"]==37
assert rows[0]["hook_strength"]==96 and rows[0]["visual_type"]=="animation"
assert rows[0]["retention_potential"]==91 and rows[0]["retention_risk"]=="none"
print("PROMPT_SCHEMA_FIELDS",sorted(schema))
print("PARSED_STORY_FIELDS",rows[0]["hook"],rows[0]["context"],rows[0]["payoff"])
print("GEMINI_REQUEST_MOCK_QA_PASS")
