"""Gemini multimodal story analysis and editorial ranking for ClipForge v1.0.
Compressed audio and optional sparse frames are sent to Google; original source video is not uploaded.
Max 6 section requests per run; no extra request per candidate.
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
from smart_duration import analyze_boundaries, align_interval
from editorial_intelligence import enrich_candidate, write_editorial_report

MODEL = "gemini-3.6-flash"
CHUNK_SECONDS = 240
CHUNK_OVERLAP = 12
MAX_REQUESTS = 6
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

def request_gemini(audio: bytes, window_length: float, desired: int, key: str,
                   model: str = MODEL, frames=None) -> list[dict]:
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,100}", model):
        raise ValueError("Invalid model identifier.")
    if len(audio) > 13_000_000:
        raise ValueError("Audio chunk exceeds inline request size.")
    prompt = f"""You are the lead editorial producer for high-retention educational, science, technology and animated-documentary Shorts.
Analyze the ACTUAL attached audio, length {window_length:.1f} seconds, plus the optional timestamped sparse frames.
Find complete, independently understandable story moments—not merely loud, emotional, fast, or visually busy sections.
A strong clip has a specific HOOK -> enough CONTEXT -> a meaningful PAYOFF. Start before the hook becomes clear,
include only the setup a new viewer needs, and end after the payoff and the final complete sentence.
Never cut a sentence, list, explanation, comparison, joke, demonstration, or thought in the middle.
Reject generic intros, sponsor reads, repetition, filler, silence, music-only parts, unfinished arguments,
context-dependent fragments, misleading claims, and moments whose payoff is missing.
VISUAL INTELLIGENCE: classify what is actually visible, not who a person is. Content may be animation,
illustration, infographic, diagrams, maps, UI/screen recordings, objects, products, live action, or mixed media.
Do not identify people or infer identity. Describe visible subjects/actions generically.
Sparse frames are snapshots, NOT continuous video. Use a frame only when its timestamp falls inside the candidate.
Never invent movement, scene changes, actions, dialogue, facts, or visual details not supported by the inputs.
When no useful frame falls inside a candidate, set visual_interest=50, visual_type="unknown",
and visual_notes="Insufficient sampled frames to assess this candidate."
EDITORIAL SCORING: score each candidate independently from 0-100 for:
hook_strength (immediate curiosity), payoff_strength (satisfying resolution/reveal),
context_independence (understandable to a new viewer), clarity (easy to follow),
visual_interest (visual support and variety, not just motion), pacing (no dead stretches),
novelty (specificity/surprise), retention_potential (editorial estimate of likely sustained interest).
Do not inflate scores. A high score needs both a compelling story and a complete payoff.
Assess retention_risk using one of: none, slow_opening, context_heavy, repetitive,
low_visual_change, weak_payoff, abrupt_transition, uncertain.
Provide a short reason for the retention estimate and a practical edit suggestion.
Do NOT claim to predict actual views, watch time, or platform performance.
The requested duration of about {desired} seconds is a SOFT preference only, NOT a fixed cut length.
A complete story may be shorter or longer than the target. Choose the natural start/end of the idea.
For Shorts, prefer 15-90 seconds; allow up to 180 seconds only when the complete story genuinely needs it.
Never return a candidate longer than 180 seconds. If a longer story has independent mini-arcs,
return those as separate complete candidates; otherwise omit it rather than truncate it.
Never pad a weak moment to hit the target. Never truncate a strong moment to hit the target.
Return ONLY valid JSON:
{{"clips":[{{"start":12.0,"end":57.0,"score":92,"complete":true,
"title":"Specific viewer-facing hook","reason":"Why this is a complete and compelling moment",
"hook":"The opening idea","context":"Necessary setup","payoff":"The conclusion or reveal",
"hook_strength":92,"payoff_strength":90,"context_independence":88,"clarity":94,
"visual_interest":82,"pacing":86,"novelty":80,"retention_potential":87,
"visual_type":"animation","visual_notes":"Illustrated reactor diagram supports the explanation",
"retention_risk":"none","retention_reason":"The opening poses a clear question and resolves it",
"edit_suggestion":"Keep the diagram visible through the reveal"}}]}}
Return 1-5 candidates with start/end RELATIVE TO THIS AUDIO in seconds.
All times must be within 0 to {window_length:.1f}. Every numeric score is 0-100.
visual_type must be one of animation, illustration, infographic, diagram, screen_recording,
live_action, mixed, unknown. Set complete=false if the segment has no complete thought.
If no meaningful story exists, return {{"clips":[]}}."""
    payload={"contents":[{"role":"user","parts":[
        {"text":prompt},
        {"inline_data":{"mime_type":"audio/mpeg",
                        "data":base64.b64encode(audio).decode("ascii")}}
    ]}],"generationConfig":{"responseMimeType":"application/json",
                           "responseSchema":{"type":"OBJECT","properties":{"clips":{
                              "type":"ARRAY","items":{"type":"OBJECT","properties":{
                                "start":{"type":"NUMBER"},"end":{"type":"NUMBER"},
                                "score":{"type":"NUMBER"},"title":{"type":"STRING"},
                                "reason":{"type":"STRING"},"complete":{"type":"BOOLEAN"},
                                "hook":{"type":"STRING"},"context":{"type":"STRING"},
                                "payoff":{"type":"STRING"},
                                "hook_strength":{"type":"NUMBER"},"payoff_strength":{"type":"NUMBER"},
                                "context_independence":{"type":"NUMBER"},"clarity":{"type":"NUMBER"},
                                "visual_interest":{"type":"NUMBER"},"pacing":{"type":"NUMBER"},
                                "novelty":{"type":"NUMBER"},"retention_potential":{"type":"NUMBER"},
                                "visual_type":{"type":"STRING","enum":["animation","illustration","infographic","diagram","screen_recording","live_action","mixed","unknown"]},
                                "visual_notes":{"type":"STRING"},
                                "retention_risk":{"type":"STRING","enum":["none","slow_opening","context_heavy","repetitive","low_visual_change","weak_payoff","abrupt_transition","uncertain"]},
                                "retention_reason":{"type":"STRING"},"edit_suggestion":{"type":"STRING"}},
                                "required":["start","end","score","title","reason","hook_strength","payoff_strength","context_independence","clarity","visual_interest","pacing","novelty","retention_potential","visual_type","visual_notes","retention_risk","retention_reason","edit_suggestion"]}}},
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
            metrics={}
            for field in ("hook_strength","payoff_strength","context_independence",
                          "clarity","visual_interest","pacing","novelty","retention_potential"):
                try:
                    value=float(row[field])
                    if math.isfinite(value):
                        metrics[field]=round(max(0,min(100,value)),1)
                except (KeyError,TypeError,ValueError):
                    pass
            result.append({"start":start,"end":min(end,window_length),
                           "score":round(max(0,min(100,score)),1),
                           "title":str(row.get("title",""))[:120],
                           "reason":str(row.get("reason",""))[:350],
                           "complete":row.get("complete") is not False,
                           "hook":str(row.get("hook",""))[:220],
                           "context":str(row.get("context",""))[:300],
                           "payoff":str(row.get("payoff",""))[:300],
                           **metrics,
                           "visual_type":str(row.get("visual_type","unknown"))[:32],
                           "visual_notes":str(row.get("visual_notes",""))[:420],
                           "retention_risk":str(row.get("retention_risk","uncertain"))[:40],
                           "retention_reason":str(row.get("retention_reason",""))[:420],
                           "edit_suggestion":str(row.get("edit_suggestion",""))[:420]})
        except (TypeError,ValueError,KeyError,AttributeError):
            continue
    return result

def sample_windows(total:float):
    """Analyze windows with 12s overlap so ideas crossing section seams retain context."""
    if total<=CHUNK_SECONDS:
        return [(0.0,total)]
    stride=CHUNK_SECONDS-CHUNK_OVERLAP
    required=math.ceil(max(0.0,total-CHUNK_SECONDS)/stride)+1
    if required<=MAX_REQUESTS:
        starts=[float(stride*i) for i in range(required)]
    else:
        # Long sources exceed the request budget: sample evenly from start to finish.
        starts=[(total-CHUNK_SECONDS)*i/(MAX_REQUESTS-1)
                for i in range(MAX_REQUESTS)]
    return [(s,min(CHUNK_SECONDS,total-s)) for s in starts]

def extract_audio(src:Path,start:float,duration:float,out:Path):
    cmd=[FFMPEG,"-hide_banner","-loglevel","error","-y",
         "-ss",str(start),"-i",str(src),"-t",str(duration),
         "-vn","-ac","1","-ar","16000",
         "-c:a","libmp3lame","-b:a","40k",str(out)]
    p=silent_run(cmd,capture_output=True,text=True,timeout=150)
    if p.returncode:
        raise RuntimeError("Could not extract audio: "+p.stderr[-250:])

def rank_candidates(rows:list[dict],total:float,seconds:int,sentences=None):
    """Align valid stories, compute weighted editorial scores, and rank every candidate."""
    pool=[]
    for row in rows:
        if row.get("complete") is False:
            continue
        try:
            ai_start=float(row["start"])
            ai_end=float(row["end"])
            ai_score=float(row["score"])
        except (TypeError,ValueError,KeyError):
            continue
        if not all(map(math.isfinite,(ai_start,ai_end,ai_score))):
            continue
        if sentences:
            aligned=align_interval(ai_start,ai_end,sentences,total,
                                   min_duration=12.0,max_duration=180.0)
            if not aligned:
                continue
            start,end,boundary=aligned
        else:
            start,end=ai_start,ai_end
            boundary={"start":"model","end":"model"}
        duration=end-start
        if duration<12.0 or duration>180.0 or start<0 or end>total+0.5:
            continue
        enriched=enrich_candidate(row)
        # Duration is only a soft ranking preference; the cut itself is never changed.
        deviation=abs(duration-float(seconds))/max(20.0,float(seconds))
        length_penalty=min(5.0,deviation*2.0)
        alignment_bonus=1.5 if boundary.get("start")=="sentence" and boundary.get("end")=="sentence" else 0.0
        selection_score=round(max(0.0,min(100.0,enriched["editorial_score"]+alignment_bonus-length_penalty)),1)
        legacy_score=round(max(0.0,min(100.0,ai_score+alignment_bonus-length_penalty)),1)
        pool.append({**enriched,"start":round(start,2),"end":round(end,2),
                     "duration":round(duration,2),"score":legacy_score,
                     "ai_score":round(ai_score,1),"ranking_score":selection_score,
                     "audio_start":ai_start,"audio_end":ai_end,
                     "boundary_alignment":boundary})
    pool.sort(key=lambda x:x["ranking_score"],reverse=True)
    for index,row in enumerate(pool,1):
        row["editorial_rank"]=index
        row["selection_status"]="ranked"
        row["selection_reason"]="Awaiting diversity and requested clip-count selection."
    return pool


def select_best(rows:list[dict],count:int,total:float,seconds:int,sentences=None,
                return_ranked=False):
    """Select the strongest non-overlapping stories while retaining the full ranking."""
    ranked=rank_candidates(rows,total,seconds,sentences=sentences)
    taken=[]
    for row in ranked:
        conflict=None
        for chosen in taken:
            overlap=max(0.0,min(row["end"],chosen["end"])-max(row["start"],chosen["start"]))
            ratio=overlap/max(1.0,min(row["duration"],chosen["duration"]))
            if ratio>0.35:
                conflict=chosen
                break
        if conflict is not None:
            row["selection_status"]="skipped_overlap"
            row["selection_reason"]=f"Overlaps stronger candidate #{conflict['editorial_rank']}."
            continue
        if len(taken)>=count:
            row["selection_status"]="below_clip_count"
            row["selection_reason"]="Ranked below the requested number of non-overlapping clips."
            continue
        row["selection_status"]="selected"
        row["selection_reason"]="Selected as a high-scoring, complete, non-overlapping story."
        taken.append(row)
    selected=sorted(taken,key=lambda x:x["start"])
    return (selected,ranked) if return_ranked else selected

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
               dry_run=False,provider=None,visual=True,render=True,
               context_aware=True,duration_model="base"):
    src,dest=Path(src).resolve(),Path(dest).resolve()
    if not src.is_file() or src.suffix.lower() not in EXTS:
        raise ValueError("Select an existing supported local video file.")
    if not 1<=clips<=20 or not 5<=seconds<=180:
        raise ValueError("Clips 1-20, duration 5-180 seconds required.")
    if style not in {"blur","crop","fit"}:
        raise ValueError("Unknown layout")
    total=probe_duration(src)
    if total<12:
        raise ValueError("Source must be at least 12 seconds long for context-aware Shorts.")
    key="" if provider else load_key()
    windows=sample_windows(total)
    log(f"Analyzing {len(windows)} audio segment(s) with Gemini {model}")
    log(f"Target duration: {seconds}s (soft preference; complete story boundaries win, Shorts ceiling 180s).")
    log("TEST MODE: no Google request." if provider else "Compressed audio and sparse sampled video frames may be sent to Gemini.")
    if context_aware:
        log(f"Context-aware duration ON: local Whisper '{duration_model}' will align sentence boundaries; transcript stays on this PC.")
    rows=[]
    errors=[]
    active_model=model
    # Save each successful section to avoid reusing quota after a partial failure.
    if not dry_run:
        dest.mkdir(parents=True,exist_ok=True)
    cachefile=dest/"analysis-progress.json"
    fingerprint=str((str(src),src.stat().st_size,src.stat().st_mtime_ns,
                     model,seconds,visual,"editorial-intelligence-v10"))
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
    sentences=[]
    if context_aware:
        try:
            sentences=analyze_boundaries(src,dest,model_size=duration_model,log=log)
        except Exception as exc:
            log(f"Local Whisper boundary alignment unavailable; using Gemini's natural time ranges. {type(exc).__name__}: {str(exc)[:180]}")
            sentences=[]
    picks,ranked=select_best(rows,clips,total,seconds,sentences=sentences,
                             return_ranked=True)
    if not picks:
        raise RuntimeError("No complete story candidates passed duration/boundary checks. Try another model or disable context-aware duration; "+str(len(errors))+" sections failed.")
    manifest={"tool":"VAW ClipForge","version":"v1.0",
              "method":"Gemini multimodal editorial analysis + deterministic weighted ranking + local Whisper boundary alignment",
              "source":str(src),"model":active_model,"created":datetime.now().isoformat(),
              "duration_policy":"context-aware soft target; 12-180s; natural sentence boundaries",
              "editorial_method":"weighted hook/payoff/context/clarity/visual/pacing/novelty/retention scores",
              "retention_note":"AI editorial estimate only; not a prediction of actual views, watch time, or platform performance.",
              "visual_analysis":"sparse timestamped sample frames; generic visual-content classification; no identity recognition",
              "target_seconds":seconds,"context_aware":bool(context_aware),
              "local_boundary_count":len(sentences),"sections_analyzed":len(windows),
              "sections_failed":errors,"candidate_count":len(ranked),
              "ranked_candidates":ranked,"clips":[]}
    if not dry_run:
        dest.mkdir(parents=True,exist_ok=True)
    for i,item in enumerate(picks,1):
        outfile=dest/f"{src.stem}_ai_{i:02d}_{int(item['start']):05d}s.mp4"
        manifest["clips"].append({**item,"path":str(outfile)})
        log(f"Selected #{item['editorial_rank']} {i}: {item['start']:.1f}-{item['end']:.1f}s ({item['duration']:.1f}s), editorial {item['editorial_score']}/100, retention estimate {item['retention_potential']}/100 — {item['title']}")
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
        report=write_editorial_report(manifest,dest/"ai-editorial-report.html")
        manifest["editorial_report"]=str(report)
        (dest/"ai-highlights.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
        log(f"Editorial report saved: {report.name} ({len(ranked)} candidates ranked).")
    return manifest
