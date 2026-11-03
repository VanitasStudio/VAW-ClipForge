"""Patch Gemini ClipForge to v0.3: structured JSON, sparse visuals, partial-result recovery."""
from pathlib import Path
p=Path(__file__).with_name("gemini_highlights.py")
s=p.read_text(encoding="utf-8")
s=s.replace("import base64\n", "import base64\nimport time\n")
s=s.replace('model: str = MODEL) -> list[dict]:', 'model: str = MODEL, frames=None) -> list[dict]:')
s=s.replace(
    "You do NOT have video. Do not invent visual events, quotes or dialogue.",
    "You have audio and optionally a few video stills. Still images are sparse, not continuous video. Do not invent unseen events or dialogue. Rank hook, context independence, payoff and clarity (25 points each)."
)
s=s.replace(
    '    payload={"contents":[{"role":"user","parts":[',
    '    payload={"contents":[{"role":"user","parts":['
)
needle='''    ]}],"generationConfig":{"responseMimeType":"application/json",
                           "temperature":0.2,"maxOutputTokens":2200}}'''
replacement='''    ]}],"generationConfig":{"responseMimeType":"application/json",
                           "responseSchema":{"type":"OBJECT","properties":{"clips":{
                              "type":"ARRAY","items":{"type":"OBJECT","properties":{
                                "start":{"type":"NUMBER"},"end":{"type":"NUMBER"},
                                "score":{"type":"NUMBER"},"title":{"type":"STRING"},
                                "reason":{"type":"STRING"}},
                                "required":["start","end","score","title","reason"]}}},
                                "required":["clips"]},
                           "temperature":0.2,"maxOutputTokens":8192}}
    for timestamp,frame in frames or []:
        payload["contents"][0]["parts"].append({
            "text":f"Sparse video frame at relative timestamp {timestamp:.1f}s (context only)"})
        payload["contents"][0]["parts"].append({"inline_data":{
            "mime_type":"image/jpeg","data":base64.b64encode(frame).decode("ascii")}})'''
if needle not in s:raise Exception("SCHEMA_NEEDLE_MISSING")
s=s.replace(needle,replacement)
s=s.replace(
  '    parsed=json.loads(text)\n',
  '''    try:
        parsed=json.loads(text)
    except (ValueError,TypeError) as exc:
        raise RuntimeError("Gemini returned malformed or incomplete JSON; try an alternate model.") from exc
'''
)
s=s.replace(
  '    response=json.loads(raw)\n',
  '''    try:
        response=json.loads(raw)
    except (ValueError,TypeError) as exc:
        raise RuntimeError("Gemini returned an invalid response envelope.") from exc
'''
)
s=s.replace(
  '''    if not parts:
        raise RuntimeError("Gemini returned no content or blocked the request.")''',
  '''    if not parts:
        reasons=[str(x.get("finishReason","UNKNOWN")) for x in response.get("candidates",[])]
        raise RuntimeError("Gemini returned empty output (finish: "+",".join(reasons[:3])+").")'''
)
anchor="def process_ai(src,dest,clips=3,seconds=30,style=\"blur\",model=MODEL,log=print,"
visual_fn='''def sampled_frames(src,offset,length,folder):
    """Four small sampled frames; not a full-video understanding."""
    frames=[]
    for i,ratio in enumerate((0.15,0.38,0.62,0.85),1):
        position=length*ratio
        output=folder/f"vframe-{i}.jpg"
        result=subprocess.run([FFMPEG,"-hide_banner","-loglevel","error","-y",
            "-ss",str(offset+position),"-i",str(src),"-frames:v","1",
            "-vf","scale=320:-2","-q:v","8",str(output)],
            capture_output=True,text=True,timeout=50)
        if result.returncode==0 and output.exists():
            frames.append((position,output.read_bytes()))
    return frames

'''
if anchor not in s:raise Exception("PROC_ANCHOR_MISSING")
s=s.replace(anchor,visual_fn+anchor)
s=s.replace('dry_run=False,provider=None):','dry_run=False,provider=None,visual=True):')
s=s.replace(
  '    rows=[]\n    active_model=model',
  '    rows=[]\n    errors=[]\n    active_model=model'
)
s=s.replace(
  '            log(f"Gemini request {i}/{len(windows)} ({round(offset)}s, {len(chunk)//1024} KiB)")',
  '            frames=sampled_frames(src,offset,length,Path(work)) if visual else []\n'
  '            log(f"Gemini request {i}/{len(windows)} ({round(offset)}s, {len(chunk)//1024} KiB, {len(frames)} frames)")'
)
s=s.replace(
  '''            try:
                candidates=fn(chunk,length,seconds,key,active_model)
            except RuntimeError as exc:''',
  '''            try:
                candidates=fn(chunk,length,seconds,key,active_model,frames)
            except RuntimeError as exc:'''
)
s=s.replace(
  '''                if provider is not None or active_model=="gemini-3.5-flash-lite" or not any(
                    marker in str(exc) for marker in ("HTTP 503", "HTTP 502", "HTTP 504")):
                    raise
                log(f"Primary model unavailable ({type(exc).__name__}); trying Gemini 3.5 Flash-Lite.")
                active_model="gemini-3.5-flash-lite"
                candidates=fn(chunk,length,seconds,key,active_model)''',
  '''                if provider is not None or active_model=="gemini-3.5-flash-lite":
                    log(f"Section {i} skipped: {type(exc).__name__}: {str(exc)[:130]}")
                    errors.append({"section":i,"reason":str(exc)[:130]})
                    continue
                if "quota" in str(exc).lower() or "authentication" in str(exc).lower():
                    log(f"Gemini quota/auth error in section {i}: {str(exc)[:100]}")
                    errors.append({"section":i,"reason":str(exc)[:130]})
                    break
                log(f"Section {i} response error; retrying with Gemini 3.5 Flash-Lite.")
                active_model="gemini-3.5-flash-lite"
                try:
                    candidates=fn(chunk,length,seconds,key,active_model,frames)
                except Exception as fallback_exc:
                    log(f"Section {i} skipped after retry: {str(fallback_exc)[:130]}")
                    errors.append({"section":i,"reason":str(fallback_exc)[:130]})
                    continue'''
)
s=s.replace('"sections_analyzed":len(windows),"clips":[]}',
            '"sections_analyzed":len(windows),"sections_failed":errors,"clips":[]}')
s=s.replace('    if not picks:\n        raise RuntimeError("No useful spoken highlights found. Try Audio Activity mode.")',
            '    if not picks:\n        raise RuntimeError("No valid highlights from analyzed sections. Try Audio Activity mode; "+str(len(errors))+" sections failed.")')
s=s.replace(
  '    log("TEST MODE: no Google request." if provider else "Audio excerpts sent to Google for analysis; no video uploaded.")',
  '    log("TEST MODE: no Google request." if provider else "Audio and sparse sampled video frames may be sent to Gemini.")')
p.write_text(s,encoding="utf-8")
print("Gemini v0.3 patch applied.")
