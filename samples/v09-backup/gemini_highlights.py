"""Gemini semantic audio highlight selection for ClipForge v0.2.
Audio excerpts sent to Google, never original video. Max 6 requests per run.
"""
from __future__ import annotations
import base64
import time
import json
import math
import re
import subprocess
from silent_process import run as silent_run, popen as silent_popen
import tempfile
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from clip_engine import FFMPEG, EXTS, filter_graph, probe_duration
from secure_config import load_key

MODEL = "gemini-3.6-flash"
CHUNK_SECONDS = 240
MAX_REQUESTS = 6
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

def request_gemini(audio: bytes, window_length: float, desired: int, key: str,
                   model: str = MODEL, frames=None) -> list[dict]:
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,100}", model):
        raise ValueError("Invalid model identifier.")
    if len(audio) > 13_000_000:
        raise ValueError("Audio chunk exceeds inline request size.")
    prompt = f"""You are a meticulous short-form editor. Analyze the ACTUAL attached audio,
length {window_length:.1f} seconds. Find self-contained clips with compelling hooks,
interesting information, jokes, surprising reactions, or clear story payoffs.
Skip silence, music-only segments, ads, filler, unfinished stories, generic intros.
You have audio and optionally a few video stills. Still images are sparse, not continuous video. Do not invent unseen events or dialogue. Rank hook, context independence, payoff and clarity (25 points each).
Return ONLY valid JSON shaped:
{{"clips":[{{"start":12.0,"end":42.0,"score":88,
"title":"Specific catchy hook","reason":"What happens in the audio"}}]}}
Return 1-5 candidates with start/end RELATIVE TO THIS AUDIO in seconds.
Target ~{desired} sec per candidate; all times must be within 0 to {window_length:.1f}.
Score between 0 and 100. If no meaningful speech, return {{"clips":[]}}."""
    payload={"contents":[{"role":"user","parts":[
        {"text":prompt},
        {"inline_data":{"mime_type":"audio/mpeg",
                        "data":base64.b64encode(audio).decode("ascii")}}
    ]}],"generationConfig":{"responseMimeType":"application/json",
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
            "mime_type":"image/jpeg","data":base64.b64encode(frame).decode("ascii")}})
    request=urllib.request.Request(
        ENDPOINT.format(model=model), data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type":"application/json","x-goog-api-key":key}, method="POST")
    try:
        with urllib.request.urlopen(request,timeout=120) as response:
            raw=response.read(500001)
    except urllib.error.HTTPError as exc:
        code=exc.code
        if code in (401,403):
            raise RuntimeError("Gemini rejected authentication (401/403). Check API key and project permissions.") from None
        if code==429:
            raise RuntimeError("Gemini quota/rate limit reached (429). Try again later.") from None
        message=""
        try:
            message=str(json.loads(exc.read(4000)).get("error",{}).get("message",""))[:200]
        except Exception:
            pass
        raise RuntimeError(f"Gemini HTTP {code}: {message}") from None
    except urllib.error.URLError:
        raise RuntimeError("Cannot connect to Gemini. Check internet.") from None
    if len(raw)>500000:
        raise RuntimeError("Gemini response too large.")
    try:
        response=json.loads(raw)
    except (ValueError,TypeError) as exc:
        raise RuntimeError("Gemini returned an invalid response envelope.") from exc
    parts=[]
    for candidate in response.get("candidates",[]):
        parts.extend(str(p.get("text","")) for p in candidate.get("content",{}).get("parts",[]) if "text" in p)
    if not parts:
        reasons=[str(x.get("finishReason","UNKNOWN")) for x in response.get("candidates",[])]
        raise RuntimeError("Gemini returned empty output (finish: "+",".join(reasons[:3])+").")
    text="\n".join(parts).strip()
    if text.startswith(chr(96)*3):
        text=text.strip(chr(96)).removeprefix("json").strip()
    try:
        parsed=json.loads(text)
    except (ValueError,TypeError) as exc:
        raise RuntimeError("Gemini returned malformed or incomplete JSON; try an alternate model.") from exc
    rows=parsed.get("clips",[]) if isinstance(parsed,dict) else []
    result=[]
    for row in rows[:8]:
        try:
            start,end,score=float(row["start"]),float(row["end"]),float(row["score"])
            if not all(map(math.isfinite,(start,end,score))):
                continue
            if start<0 or end<=start or end>window_length+3:
                continue
            result.append({"start":start,"end":min(end,window_length),
                           "score":round(max(0,min(100,score)),1),
                           "title":str(row.get("title",""))[:120],
                           "reason":str(row.get("reason",""))[:350]})
        except (TypeError,ValueError,KeyError,AttributeError):
            continue
    return result

def sample_windows(total:float):
    if total<=CHUNK_SECONDS:
        return [(0.0,total)]
    count=min(MAX_REQUESTS,math.ceil(total/CHUNK_SECONDS))
    if total<=count*CHUNK_SECONDS:
        starts=[float(CHUNK_SECONDS*i) for i in range(count)]
    else:
        starts=[(total-CHUNK_SECONDS)*i/(count-1) for i in range(count)]
    return [(s,min(CHUNK_SECONDS,total-s)) for s in starts]

def extract_audio(src:Path,start:float,duration:float,out:Path):
    cmd=[FFMPEG,"-hide_banner","-loglevel","error","-y",
         "-ss",str(start),"-i",str(src),"-t",str(duration),
         "-vn","-ac","1","-ar","16000",
         "-c:a","libmp3lame","-b:a","40k",str(out)]
    p=silent_run(cmd,capture_output=True,text=True,timeout=150)
    if p.returncode:
        raise RuntimeError("Could not extract audio: "+p.stderr[-250:])

def select_best(rows:list[dict],count:int,total:float,seconds:int):
    taken=[]
    for row in sorted(rows,key=lambda x:x["score"],reverse=True):
        start=max(0,min(total-seconds,(row["start"]+row["end"])/2-seconds/2))
        if all(start>=x["start"]+seconds+2 or x["start"]>=start+seconds+2 for x in taken):
            taken.append({**row,"start":round(start,2),"duration":seconds,
                          "audio_start":row["start"],"audio_end":row["end"]})
        if len(taken)>=count:
            break
    return sorted(taken,key=lambda x:x["start"])

def sampled_frames(src,offset,length,folder):
    """Four small sampled frames; not a full-video understanding."""
    frames=[]
    for i,ratio in enumerate((0.15,0.38,0.62,0.85),1):
        position=length*ratio
        output=folder/f"vframe-{i}.jpg"
        result=silent_run([FFMPEG,"-hide_banner","-loglevel","error","-y",
            "-ss",str(offset+position),"-i",str(src),"-frames:v","1",
            "-vf","scale=320:-2","-q:v","8",str(output)],
            capture_output=True,text=True,timeout=50)
        if result.returncode==0 and output.exists():
            frames.append((position,output.read_bytes()))
    return frames

def process_ai(src,dest,clips=3,seconds=30,style="blur",model=MODEL,log=print,
               dry_run=False,provider=None,visual=True,render=True):
    src,dest=Path(src).resolve(),Path(dest).resolve()
    if not src.is_file() or src.suffix.lower() not in EXTS:
        raise ValueError("Select an existing supported local video file.")
    if not 1<=clips<=20 or not 5<=seconds<=180:
        raise ValueError("Clips 1-20, duration 5-180 seconds required.")
    if style not in {"blur","crop","fit"}:
        raise ValueError("Unknown layout")
    total=probe_duration(src)
    if total<seconds:
        raise ValueError("Source must be longer than desired clip length.")
    key="" if provider else load_key()
    windows=sample_windows(total)
    log(f"Analyzing {len(windows)} audio segment(s) with Gemini {model}")
    log("TEST MODE: no Google request." if provider else "Audio and sparse sampled video frames may be sent to Gemini.")
    rows=[]
    errors=[]
    active_model=model
    # Save each successful section to avoid reusing quota after a partial failure.
    if not dry_run:
        dest.mkdir(parents=True,exist_ok=True)
    cachefile=dest/"analysis-progress.json"
    fingerprint=str((str(src),src.stat().st_size,src.stat().st_mtime_ns,
                     model,seconds,visual))
    completed={}
    if cachefile.exists():
        try:
            old=json.loads(cachefile.read_text(encoding="utf-8"))
            if old.get("fingerprint")==fingerprint:
                completed=old.get("successful_sections",{})
                log(f"Recovered {len(completed)} previously analyzed section(s).")
        except (ValueError,OSError):
            pass
    with tempfile.TemporaryDirectory(prefix="vawclip-ai-") as work:
        for i,(offset,length) in enumerate(windows,1):
            if str(i) in completed:
                cached=completed[str(i)]
                for x in cached:
                    rows.append({**x,"start":x["start"]+offset,"end":x["end"]+offset})
                log(f"Section {i}: reused {len(cached)} cached highlights.")
                continue
            audio=Path(work)/f"audio{i}.mp3"
            extract_audio(src,offset,length,audio)
            chunk=audio.read_bytes() if audio.exists() else b""
            if not chunk:
                log(f"Audio segment {i} was empty, skipping.")
                continue
            frames=sampled_frames(src,offset,length,Path(work)) if visual else []
            log(f"Gemini request {i}/{len(windows)} ({round(offset)}s, {len(chunk)//1024} KiB, {len(frames)} frames)")
            fn=provider or request_gemini
            try:
                candidates=fn(chunk,length,seconds,key,active_model,frames)
            except RuntimeError as exc:
                # Fail over only when provider is temporarily unavailable.
                # Do not hide quota (429), auth (401/403) or invalid request errors.
                if provider is not None or active_model=="gemini-3.5-flash-lite":
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
                    continue
            completed[str(i)]=candidates
            if not dry_run:
                cachefile.write_text(json.dumps({
                    "fingerprint":fingerprint,
                    "successful_sections":completed
                },indent=2),encoding="utf-8")
            for x in candidates:
                rows.append({**x,"start":x["start"]+offset,"end":x["end"]+offset})
            log(f"Candidates: {len(candidates)}")
    picks=select_best(rows,clips,total,seconds)
    if not picks:
        raise RuntimeError("No valid highlights from analyzed sections. Try Audio Activity mode; "+str(len(errors))+" sections failed.")
    manifest={"tool":"VAW ClipForge","version":"v0.2","method":"Gemini audio ranking",
              "source":str(src),"model":active_model,"created":datetime.now().isoformat(),
              "sections_analyzed":len(windows),"sections_failed":errors,"clips":[]}
    if not dry_run:
        dest.mkdir(parents=True,exist_ok=True)
    for i,item in enumerate(picks,1):
        outfile=dest/f"{src.stem}_ai_{i:02d}_{int(item['start']):05d}s.mp4"
        manifest["clips"].append({**item,"path":str(outfile)})
        log(f"Selected {i}: {item['start']:.1f}s, score {item['score']}, {item['title']}")
        if dry_run or not render:
            continue
        cmd=[FFMPEG,"-hide_banner","-loglevel","error","-y",
             "-ss",str(item["start"]),"-i",str(src),"-t",str(item["duration"]),
             "-vf",filter_graph(style),"-r","30",
             "-c:v","libx264","-preset","veryfast","-crf","24",
             "-c:a","aac","-b:a","128k","-movflags","+faststart",str(outfile)]
        p=silent_run(cmd,capture_output=True,text=True,timeout=420)
        if p.returncode:
            raise RuntimeError("Failed rendering AI clip: "+p.stderr[-350:])
        log("Exported "+outfile.name)
    if not dry_run:
        (dest/"ai-highlights.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return manifest
