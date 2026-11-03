"""Local speech-to-text + optional hard subtitles for ClipForge.
Uses faster-whisper on CPU. Downloads the requested model once, no voice upload.
"""
from __future__ import annotations
import os
import subprocess
import tempfile
from pathlib import Path
from clip_engine import FFMPEG

BASE=Path(__file__).resolve().parent
MODEL_HOME=BASE/"models"
WHISPER_MODELS={"tiny","base","small"}

def stamp(t:float)->str:
    ms=max(0,round(t*1000))
    h,ms=divmod(ms,3600000)
    m,ms=divmod(ms,60000)
    sec,ms=divmod(ms,1000)
    return f"{h:02}:{m:02}:{sec:02},{ms:03}"

def caption_groups(segments):
    """Prefer word timestamps with short 1-2 line groups."""
    words=[]
    for segment in segments:
        for word in getattr(segment,"words",[]) or []:
            s=float(word.start)
            e=float(word.end)
            value=str(word.word).strip()
            if value and e>s:
                words.append((s,e,value))
        if not getattr(segment,"words",None):
            value=str(getattr(segment,"text","")).strip()
            if value and segment.end>segment.start:
                words.append((float(segment.start),float(segment.end),value))
    groups=[];buffer=[]
    for w in words:
        if buffer and (w[1]-buffer[0][0]>2.9 or len(buffer)>=7
                       or w[0]-buffer[-1][1]>0.75):
            groups.append((buffer[0][0],buffer[-1][1],
                           " ".join(t[2] for t in buffer)))
            buffer=[]
        buffer.append(w)
    if buffer:
        groups.append((buffer[0][0],buffer[-1][1],
                       " ".join(t[2] for t in buffer)))
    return groups

def srt_from_groups(groups):
    lines=[]
    for i,(a,b,msg) in enumerate(groups,1):
        # Keep subtitles reasonably legible on mobile.
        words=msg.split()
        text=[];line=""
        for word in words:
            if line and len(line)+1+len(word)>28:
                text.append(line);line=word
            else:
                line=(line+" "+word).strip()
        if line:text.append(line)
        # No fabricated text. Keep every transcribed word even if long.
        lines.append(f"{i}\n{stamp(a)} --> {stamp(b)}\n"+"\n".join(text)+"\n")
    return "\n".join(lines)+("\n" if lines else "")

_model_cache={}
def get_model(size="base",log=print):
    if size not in WHISPER_MODELS:
        raise ValueError("Whisper size must be tiny, base, or small")
    if size not in _model_cache:
        from faster_whisper import WhisperModel
        MODEL_HOME.mkdir(parents=True,exist_ok=True)
        log(f"Loading Whisper '{size}' locally (first run may download model)...")
        _model_cache[size]=WhisperModel(size,device="cpu",compute_type="int8",
                                        download_root=str(MODEL_HOME))
    return _model_cache[size]

def transcribe_clip(clip:Path,size="base",log=print):
    # PyAV 19 removed metadata_errors argument while faster-whisper 1.2.1 still
    # passes it. Adapt the decoder call without modifying any installed packages.
    import av
    if not getattr(av.open,"_vaw_compat",False):
        original_open=av.open
        def compat_open(*args,**kwargs):
            kwargs.pop("metadata_errors",None)
            return original_open(*args,**kwargs)
        compat_open._vaw_compat=True
        av.open=compat_open
    model=get_model(size,log)
    segments,info=model.transcribe(str(clip),beam_size=1,best_of=1,
                                   word_timestamps=True,vad_filter=True,
                                   condition_on_previous_text=False)
    captions=caption_groups(list(segments))
    if not captions:
        log(f"No reliable speech detected in {clip.name}; captions skipped.")
        return None
    srt=clip.with_suffix(".srt")
    srt.write_text(srt_from_groups(captions),encoding="utf-8")
    log(f"Saved {len(captions)} subtitle lines: {srt.name}")
    return srt

def burn_srt(clip:Path,srt:Path,log=print)->bool:
    """Burn SRT with libass if available; otherwise keep .srt as sidecar."""
    clip=clip.resolve()
    srt=srt.resolve() if srt else None
    if not srt or not srt.is_file():
        return False
    tmp=clip.with_name(clip.stem+"-burned-temp.mp4")
    # relative basename avoids Windows colon escaping in FFmpeg subtitles filter
    # Source media still absolute; process cwd points to the SRT directory.
    escaped=srt.name.replace("\\","\\\\").replace(":","\\:").replace("'","\\'")
    style="FontName=Arial,FontSize=19,Bold=1,Outline=3,Shadow=1,MarginV=150,Alignment=2"
    filters=f"subtitles={escaped}:force_style='{style}'"
    cmd=[FFMPEG,"-hide_banner","-loglevel","error","-y","-i",str(clip),
         "-vf",filters,"-c:v","libx264","-preset","veryfast","-crf","23",
         "-c:a","copy","-movflags","+faststart",str(tmp)]
    try:
        result=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              text=True,cwd=str(srt.parent),timeout=420)
        if result.returncode!=0:
            log("Caption burn not available; kept .srt. "+result.stderr[-160:].replace("\n"," "))
            tmp.unlink(missing_ok=True)
            return False
        os.replace(tmp,clip)
        log(f"Burned captions: {clip.name}")
        return True
    except (OSError,subprocess.TimeoutExpired) as exc:
        tmp.unlink(missing_ok=True)
        log("Caption burn failed; .srt retained.")
        return False

def caption_output(clips:list[Path],size="base",burn=True,log=print):
    outcomes={}
    for i,clip in enumerate(clips,1):
        try:
            log(f"Auto-caption {i}/{len(clips)}: {clip.name}")
            srt=transcribe_clip(clip,size=size,log=log)
            burned=burn_srt(clip,srt,log) if srt and burn else False
            outcomes[str(clip)]={"srt":str(srt) if srt else None,"burned":burned}
        except Exception as exc:
            log(f"Caption skipped for {clip.name}: {type(exc).__name__}: {str(exc)[:140]}")
            outcomes[str(clip)]={"srt":None,"burned":False,"error":type(exc).__name__}
    return outcomes
