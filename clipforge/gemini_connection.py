"""Test Gemini API connectivity using stored key, without uploading media."""
from __future__ import annotations
import json
import urllib.error
import urllib.request
from clipforge.secure_config import load_key
from clipforge.gemini_highlights import ENDPOINT, MODEL

def test_gemini_connection(model=MODEL) -> str:
    key=load_key()
    request=urllib.request.Request(
        ENDPOINT.format(model=model),method="POST",
        headers={"Content-Type":"application/json","x-goog-api-key":key},
        data=json.dumps({
            "contents":[{"parts":[{"text":"Reply with exactly OK."}]}],
            "generationConfig":{"maxOutputTokens":20,"temperature":0}
        }).encode("utf-8"))
    try:
        with urllib.request.urlopen(request,timeout=30) as response:
            result=json.loads(response.read(50000))
    except urllib.error.HTTPError as exc:
        if exc.code in (401,403):
            raise RuntimeError("Gemini authentication failed (401/403). Try a newly generated Google AI Studio API key.") from None
        if exc.code==429:
            raise RuntimeError("Gemini quota exceeded (429). Check free-tier limits or billing.") from None
        raise RuntimeError(f"Gemini returned HTTP {exc.code}. Check model access and API project.") from None
    except urllib.error.URLError:
        raise RuntimeError("Gemini connection failed. Check internet and proxy.") from None
    if not result.get("candidates"):
        raise RuntimeError("Connected, but no model response was returned.")
    return "Gemini API connected successfully. Model: "+model

if __name__=="__main__":
    print(test_gemini_connection())
