"""VAW ClipForge v0.5 review data + non-destructive timeline render.

Edits local subtitles and camera framing from ORIGINAL horizontal footage, avoiding
recropping a previously cropped Shorts export. No Gemini request, no uploads.
"""
from __future__ import annotations
import json
import math
import re
import subprocess
from datetime import datetime
from pathlib import Path

import cv2
from clip_engine import FFMPEG, probe_duration
from subtitle_presets import caption_ass, choose
from subject_tracking import tracked_center

def srt_seconds(value):
    m=re.fullmatch(r"(\d+):(\d\d):(\d\d)[,.](\d{3})",value.strip())
    if not m:raise ValueError("Invalid caption timestamp "+repr(value))
    return 3600*int(m[1])+60*int(m[2])+int(m[3])+int(m[4])/1000

def timestamp_srt(t):
    ms=max(0,round(float(t)*1000))
    h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def parse_srt(path):
    text=Path(path).read_text(encoding="utf-8-sig")
    rows=[]
    for block in re.split(r"\n\s*\n",text.strip().replace("\r\n","\n")):
        lines=block.split("\n")
        time_line=next((l for l in lines if "-->" in l),None)
        if not time_line:continue
        parts=time_line.split("-->")
        try:
            start=srt_seconds(parts[0].strip())
            end=srt_seconds(parts[1].strip().split(" ")[0])
        except (ValueError,IndexError):continue
        idx=lines.index(time_line)
        body=" ".join(l.strip() for l in lines[idx+1:] if l.strip()).strip()
        if body and end>start:
            rows.append({"start":start,"end":end,"text":body})
    return rows

def make_srt(rows):
    return "\n".join(
        f"{i}\n{timestamp_srt(item['start'])} --> {timestamp_srt(item['end'])}\n{item['text']}\n"
        for i,item in enumerate(rows,1)
    )+"\n"

def make_ass(rows,mode="karaoke"):
    return caption_ass(rows,mode)


def load_clip(mp4):
    clip=Path(mp4).resolve()
    if not clip.is_file() or clip.suffix.lower()!=".mp4":
        raise ValueError("Select an existing ClipForge MP4")
    manifest=clip.parent/"v04-manifest.json"
    if not manifest.is_file():
        raise ValueError("v04-manifest.json is missing. Open a ClipForge v0.4 output.")
    data=json.loads(manifest.read_text(encoding="utf-8"))
    clip_data=next((r for r in data.get("clips",[])
                    if Path(r.get("output","")).resolve()==clip),None)
    if not clip_data:
        raise ValueError("This clip is not listed in the v04 manifest. Open the latest v0.4 export.")
    src=Path(data["source"]).resolve()
    if not src.is_file():
        raise FileNotFoundError("Original video is missing: "+str(src))
    raw_sub=clip.with_suffix(".srt")
    if not raw_sub.is_file():
        raise FileNotFoundError("SRT sidecar missing: "+str(raw_sub))
    duration=float(clip_data["duration"])
    source_start=float(clip_data["start"])
    focus=clip_data.get("visual",{}).get("focus_samples",[])
    cuts=clip_data.get("visual",{}).get("scene_cuts",[])
    draft=clip.with_suffix(".review.json")
    subtitles=parse_srt(raw_sub)
    keyframes=[]
    mode="karaoke"
    subject_tracks=[]
    transitions={}
    if draft.exists():
        saved=json.loads(draft.read_text(encoding="utf-8"))
        if saved.get("clip")==str(clip) and saved.get("source")==str(src):
            subtitles=saved.get("subtitles",subtitles)
            keyframes=saved.get("keyframes",[])
            mode=saved.get("caption_style",mode)
            subject_tracks=saved.get("subject_tracks",[])
            transitions=saved.get("transitions",{})
    cap=cv2.VideoCapture(str(src))
    if not cap.isOpened():raise RuntimeError("Could not read original footage.")
    w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    if w<10 or h<10:raise ValueError("Could not read source dimensions.")
    return {"clip":str(clip),"source":str(src),"source_start":source_start,
            "duration":duration,"width":w,"height":h,"focus_samples":focus,
            "cuts":cuts,"subtitles":subtitles,"keyframes":keyframes,
            "caption_style":mode,"subject_tracks":subject_tracks,
            "transitions":transitions}

def crop_width(data):
    return min(int(data["width"]),max(2,int(data["height"]*9/16)//2*2))

def linear(points,t):
    if not points:return None
    points=sorted((float(a),float(b)) for a,b in points)
    if t<=points[0][0]:return points[0][1]
    if t>=points[-1][0]:return points[-1][1]
    for (a,x),(b,y) in zip(points,points[1:]):
        if a<=t<=b:
            f=(t-a)/max(0.001,b-a)
            return x+(y-x)*f
    return points[-1][1]

def focus_center(data,t):
    width=int(data["width"]);crop=crop_width(data)
    points=data.get("focus_samples",[])
    base=linear(points,t)
    center=(float(base)+crop/2) if base is not None else width/2
    subject=tracked_center(data,t)
    if subject is not None:
        center=subject
    manual=[(float(k["time"]),float(k["center"])) for k in data.get("keyframes",[])]
    if manual:
        manual.sort()
        # Manual keyframes influence a 3-second neighborhood; automatic tracking
        # remains active elsewhere and scene changes retain their original behavior.
        for i,(at,desired) in enumerate(manual):
            distance=abs(t-at)
            if distance>2.0:continue
            strength=max(0,1-distance/2)
            chosen=desired*width
            if i+1<len(manual) and at<=t<=manual[i+1][0] and manual[i+1][0]-at<4:
                t1,nxt=manual[i+1]
                fraction=(t-at)/max(0.001,t1-at)
                chosen=(desired+(nxt-desired)*fraction)*width
                strength=1
            center=center*(1-strength)+chosen*strength
    return max(crop/2,min(width-crop/2,center))

def focus_x(data,t):
    w=data["width"];cw=crop_width(data)
    x=max(0,min(w-cw,round(focus_center(data,t)-cw/2)))
    return int(x//2*2)

def validate(data):
    dur=float(data["duration"])
    if dur<1 or dur>180:
        raise ValueError("Timeline supports 1 to 180 second Shorts")
    rows=data["subtitles"]
    if len(rows)>500:raise ValueError("Too many caption segments")
    prior=0
    for r in sorted(rows,key=lambda x:float(x["start"])):
        a=float(r["start"]);b=float(r["end"])
        if not math.isfinite(a) or not math.isfinite(b) or a<0 or b>dur+0.25 or b<=a:
            raise ValueError("Caption timestamps must be inside clip duration")
        if a<prior-0.025:raise ValueError("Overlapping caption timestamps")
        if len(r["text"])>200:raise ValueError("Caption phrase too long")
        prior=b
    for k in data.get("keyframes",[]):
        if not 0<=float(k["time"])<=dur or not 0<=float(k["center"])<=1:
            raise ValueError("Keyframe is out of bounds")
    if choose(data.get("caption_style","karaoke")).id not in ("karaoke","bold_pop",
            "minimal","gaming","neon","creator"):
        raise ValueError("Unknown subtitle preset")
    for track in data.get("subject_tracks",[]):
        if not 0<=float(track["start"])<=float(track["end"])<=dur+.1:
            raise ValueError("Subject tracking time invalid")
        if len(track.get("points",[]))>1000:
            raise ValueError("Too many track points")
    cuts={f"{float(cut):.2f}" for cut in data.get("cuts",[])}
    for cut,mode in data.get("transitions",{}).items():
        if cut not in cuts or mode not in ("hard","dip"):
            raise ValueError("Unknown cut transition setting")

def save_draft(data):
    validate(data)
    path=Path(data["clip"]).with_suffix(".review.json")
    to_save={k:data[k] for k in ("clip","source","subtitles","keyframes",
                                  "caption_style","subject_tracks","transitions")}
    to_save["saved_at"]=datetime.now().isoformat(timespec="seconds")
    path.write_text(json.dumps(to_save,ensure_ascii=False,indent=2),encoding="utf-8")
    return path

def export_review(data,log=print):
    validate(data)
    clip=Path(data["clip"]);source=Path(data["source"])
    folder=clip.parent
    base=clip.stem+"_edited"
    target=folder/(base+".mp4")
    version=2
    while target.exists():
        target=folder/(f"{base}_rev{version}.mp4")
        version+=1
    srt=target.with_suffix(".srt")
    ass=target.with_suffix(".ass")
    commands=target.with_suffix(".tracking.txt")
    srt.write_text(make_srt(data["subtitles"]),encoding="utf-8")
    ass.write_text(make_ass(data["subtitles"],data.get("caption_style","modern")),encoding="utf-8-sig")
    cw=crop_width(data)
    w=data["width"];h=data["height"]
    if w/h>9/16+0.03:
        # FFmpeg sendcmd at 0.2-second intervals: smooth tracking/manual overrides.
        timeline=[round(n*0.2,3) for n in range(math.ceil(data["duration"]/0.2))]
        cmds="".join(f"{t:.3f} crop@focus x {focus_x(data,t)};\n" for t in timeline)
        commands.write_text(cmds,encoding="ascii")
        first=focus_x(data,0)
        video_filter=(f"sendcmd=f={commands.name},crop@focus=w={cw}:h={h}:x={first}:y=0,"
                      "scale=1080:1920,setsar=1,format=yuv420p,")
    else:
        video_filter=("scale=1080:1920:force_original_aspect_ratio=decrease,"
                      "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,format=yuv420p,")
    dip_times=[float(c) for c,kind in data.get("transitions",{}).items()
               if kind=="dip" and .16<float(c)<float(data["duration"])-.16]
    if dip_times:
        terms=["exp(-(((t-"+f"{c:.3f}"+")/0.12)*((t-"+f"{c:.3f}"+")/0.12)))"
               for c in dip_times]
        video_filter+="eq=brightness='-0.65*("+"+".join(terms)+")':eval=frame,"
        log(f"Applying soft dip transitions to {len(dip_times)} scene cut(s).")
    video_filter+=f"ass={ass.name}"
    log("Rendering reframe and captions from original source...")
    cmd=[FFMPEG,"-hide_banner","-loglevel","error","-y",
         "-ss",f"{float(data['source_start']):.3f}","-i",str(source),
         "-t",f"{float(data['duration']):.3f}","-vf",video_filter,
         "-c:v","libx264","-preset","veryfast","-crf","22",
         "-r","30","-c:a","aac","-b:a","128k","-movflags","+faststart",str(target)]
    p=subprocess.run(cmd,cwd=str(folder),capture_output=True,text=True,timeout=750)
    if p.returncode:
        target.unlink(missing_ok=True)
        raise RuntimeError("Export failed: "+p.stderr[-650:])
    commands.unlink(missing_ok=True)
    edit_meta=target.with_suffix(".json")
    edit_meta.write_text(json.dumps(
        {"original_clip":str(clip),"source":str(source),
         "source_start":data["source_start"],"seconds":data["duration"],
         "keyframes":data["keyframes"],"subjects":len(data.get("subject_tracks",[])),
         "transitions":data.get("transitions",{}),
         "subtitle_mode":data.get("caption_style","karaoke"),
         "output_resolution":"1080x1920",
         "captions":len(data["subtitles"]),
         "created":datetime.now().isoformat(timespec="seconds")},indent=2),encoding="utf-8")
    save_draft(data)
    log(f"Export complete: {target.name}")
    return target
