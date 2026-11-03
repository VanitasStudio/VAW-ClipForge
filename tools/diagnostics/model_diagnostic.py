"""List Gemini model IDs available to this key and make tiny text-only calls.
Does not print the API key, response content, or full errors."""
import json
import urllib.request
import urllib.error
from clipforge.secure_config import load_key
ROOT="https://generativelanguage.googleapis.com/v1beta"
KEY=load_key()
req=urllib.request.Request(ROOT+"/models?pageSize=100",headers={"x-goog-api-key":KEY})
try:
    with urllib.request.urlopen(req,timeout=25) as res:
        data=json.load(res)
        print("MODEL_LIST_HTTP",res.status,flush=True)
except urllib.error.HTTPError as e:
    print("MODEL_LIST_HTTP",e.code,flush=True)
    raise SystemExit(1)
except Exception as e:
    print("MODEL_LIST_NETWORK_ERROR",type(e).__name__,flush=True)
    raise SystemExit(1)
models=[m["name"].split("/")[-1] for m in data.get("models",[]) if "generateContent" in m.get("supportedGenerationMethods",[])]
for name in models:
    if "gemini" in name and any(z in name for z in ("flash","pro","lite")):
        print("AVAILABLE",name,flush=True)
preferred=["gemini-3.8-flash","gemini-3.5-flash-lite","gemini-3.1-flash-lite","gemini-3.6-flash","gemini-2.5-flash","gemini-flash-latest"]
selected=[m for m in preferred if m in models][:4]
if not selected:
    selected=models[:2]
for model in selected:
    body=json.dumps({"contents":[{"parts":[{"text":"Return exactly OK."}]}],
                     "generationConfig":{"maxOutputTokens":20,"temperature":0}}).encode()
    req=urllib.request.Request(ROOT+"/models/"+model+":generateContent",
           data=body,method="POST",headers={"x-goog-api-key":KEY,"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=30) as res:
            answer=json.load(res)
            print("TEST",model,res.status,"CANDIDATES",len(answer.get("candidates",[])),flush=True)
    except urllib.error.HTTPError as e:
        print("TEST",model,"HTTP",e.code,flush=True)
    except Exception as e:
        print("TEST",model,type(e).__name__,flush=True)
