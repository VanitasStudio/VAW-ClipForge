"""ClipForge v0.4 captions: 2-4 word social subtitles with strict 720x1280 ASS sizing.
Local Whisper transcription; creates SRT and ASS. Never uploads text/audio.
"""
from __future__ import annotations
import os
import re
import subprocess
from silent_process import run as silent_run, popen as silent_popen
from pathlib import Path
from auto_captions import get_model, stamp
from clip_engine import FFMPEG
from subtitle_presets import caption_ass, choose

STOPWORDS={"a","an","and","are","as","at","be","by","for","from","has","he",
           "her","his","i","in","is","it","its","of","on","or","our","she",
           "that","the","their","them","there","these","they","this","to",
           "was","were","we","what","when","who","will","with","you","your"}
ASS_HEADER="""[Script Info]
Title: VAW ClipForge / Modern Captions
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
ScaledBorderAndShadow: yes
WrapStyle: 2
Collisions: Normal

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Modern,Segoe UI Semibold,46,&H00FFFFFF,&H00FFFFFF,&H00060609,&H90000000,-1,0,0,0,100,100,0,0,1,4,2,2,38,38,192,1
Style: Clean,Segoe UI Semibold,40,&H00FFFFFF,&H00FFFFFF,&H00111216,&H90000000,-1,0,0,0,100,100,0,0,1,3,1,2,42,42,190,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
RED=r"\1c&H005546FF&"
WHITE=r"\1c&H00FFFFFF&"

def safe_text(s):
    return (s.replace("\\","")
             .replace("{","(").replace("}",")")
             .replace("\n"," ").replace("\r"," "))

def format_caption_text(text,mode="modern"):
    """Apply preset text casing consistently to ASS and SRT output."""
    value=str(text)
    return value.upper() if choose(mode).uppercase else value

def get_words(segments):
    words=[]
    for seg in segments:
        segment_words=getattr(seg,"words",None)
        if segment_words:
            for w in segment_words:
                t=str(w.word).strip()
                if t and w.end is not None and w.start is not None and w.end>w.start:
                    words.append((float(w.start),float(w.end),t))
        else:
            txt=str(getattr(seg,"text","")).strip()
            if txt and seg.end>seg.start:
                tokens=txt.split()
                step=(seg.end-seg.start)/max(1,len(tokens))
                for i,t in enumerate(tokens):
                    words.append((seg.start+i*step,seg.start+(i+1)*step,t))
    return words

def phrases(words):
    out=[];current=[]
    for item in words:
        start,end,word=item
        if current:
            txt=" ".join(x[2] for x in current)
            gap=start-current[-1][1]
            total=len(txt)+len(word)+1
            # roughly 1.4 s and 2-4 words per line, no long paragraphs
            if (len(current)>=4 or
                (len(current)>=2 and (end-current[0][0]>1.85 or total>32)) or
                gap>0.45):
                out.append(current);current=[]
        current.append(item)
        if word.endswith((".","!","?")) and len(current)>=2:
            out.append(current);current=[]
    if current:out.append(current)
    # keep very short phrases by fusing with a neighbor if neither exceeds 1.8s
    fused=[]
    for p in out:
        if fused and len(p)==1 and len(fused[-1])<=3 and p[-1][1]-fused[-1][0][0]<2.4:
            fused[-1].extend(p)
        else:
            fused.append(p)
    return fused

def timestamp_ass(t):
    cs=max(0,round(t*100))
    h,cs=divmod(cs,360000)
    m,cs=divmod(cs,6000)
    sec,cs=divmod(cs,100)
    return f"{h}:{m:02}:{sec:02}.{cs:02}"

def emphasized_text(tokens,active_index=None):
    # Single emphasized content word, stable for entire short phrase.
    candidates=[(i,len(re.sub(r"[^A-Za-z]","",x).strip()))
                for i,x in enumerate(tokens)
                if re.sub(r"[^A-Za-z]","",x).lower() not in STOPWORDS]
    chosen=active_index if active_index is not None else (max(candidates,key=lambda x:x[1])[0] if candidates else -1)
    parts=[]
    for index,token in enumerate(tokens):
        text=safe_text(token)
        if index==chosen:
            parts.append("{"+RED+"}"+text+"{"+WHITE+"}")
        else:parts.append(text)
    return " ".join(parts)

def generate_caption_files(clip,mode="modern",model="base",log=print):
    clip=Path(clip).resolve()
    import av
    if not getattr(av.open,"_vaw_patched",False):
        base=av.open
        def compatible(*args,**kwargs):
            kwargs.pop("metadata_errors",None)
            return base(*args,**kwargs)
        compatible._vaw_patched=True
        av.open=compatible
    whisper=get_model(model,log)
    segments,info=whisper.transcribe(str(clip),beam_size=1,best_of=1,
        word_timestamps=True,vad_filter=True,condition_on_previous_text=False)
    groups=phrases(get_words(list(segments)))
    if not groups:
        log("No clear speech; skipped auto-caption.")
        return None,None,0
    srt=[];ass=[ASS_HEADER]
    rows=[]
    previous_end=0.0
    for n,group in enumerate(groups,1):
        start=max(previous_end,group[0][0]-0.01)
        end=group[-1][1]+0.04
        if n<len(groups):
            next_start=groups[n][0][0]
            end=min(end,max(start+0.09,next_start-0.025))
        end=max(end,start+0.09)
        previous_end=end
        words=[x[2] for x in group]
        msg=format_caption_text(" ".join(words).replace("\n"," "),mode)
        srt.append(f"{n}\n{stamp(start)} --> {stamp(end)}\n{msg}\n")
        rows.append({"start":start,"end":end,"text":msg,
                     "word_spans":[(float(w[0]),float(w[1])) for w in group]})
        # Absolute baseline 1088/1280; no libass font scaling surprises.
        if mode=="modern":
            # Stable phrase, animated color follows the spoken word.
            boundaries=[start]
            for item in group[1:]:
                boundaries.append(max(boundaries[-1],min(end,float(item[0]))))
            boundaries.append(end)
            for word_index in range(len(group)):
                a,b=boundaries[word_index:word_index+2]
                if b<=a+0.02:
                    continue
                active=emphasized_text(words,word_index)
                fade=(r"\fad(55,0)" if word_index==0 else
                      r"\fad(0,55)" if word_index==len(group)-1 else "")
                effect=r"{\an2\pos(360,1088)"+fade+"}"
                ass.append(f"Dialogue: 0,{timestamp_ass(a)},{timestamp_ass(b)},"
                           f"Modern,,0,0,0,,{effect}{active}\n")
        else:
            effect=r"{\an2\pos(360,1088)\fad(70,65)}"
            ass.append(f"Dialogue: 0,{timestamp_ass(start)},{timestamp_ass(end)},"
                       f"Clean,,0,0,0,,{effect}{safe_text(msg)}\n")
    srtfile=clip.with_suffix(".srt")
    assfile=clip.with_suffix(".ass")
    srtfile.write_text("\n".join(srt),encoding="utf-8")
    assfile.write_text(caption_ass(rows,mode),encoding="utf-8-sig")
    log(f"Polished captions: {len(groups)} short phrases, saved SRT + ASS.")
    return assfile,srtfile,len(groups)

def burn_ass(clip,ass,log=print):
    clip,ass=Path(clip).resolve(),Path(ass).resolve()
    output=clip.with_name(clip.stem+".captioned-tmp.mp4")
    if output.exists():output.unlink()
    command=[FFMPEG,"-hide_banner","-loglevel","error","-y",
             "-i",str(clip),"-vf",f"ass={ass.name}",
             "-c:v","libx264","-preset","veryfast","-crf","22",
             "-c:a","copy","-movflags","+faststart",str(output)]
    result=silent_run(command,cwd=str(ass.parent),capture_output=True,
                          text=True,timeout=420)
    if result.returncode:
        output.unlink(missing_ok=True)
        raise RuntimeError("ASS subtitle rendering failed: "+result.stderr[-500:])
    # caption track is never burned twice on the same source file
    os.replace(output,clip)
    log("Burned modern subtitle styling into "+clip.name)

def polish_clip(clip,mode="modern",burn=True,log=print):
    ass,srt,count=generate_caption_files(clip,mode=mode,log=log)
    if ass and burn:burn_ass(clip,ass,log)
    return {"captions":count,"srt":str(srt) if srt else None,
            "ass":str(ass) if ass else None,"burned":bool(ass and burn)}
