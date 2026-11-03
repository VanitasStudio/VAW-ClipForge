"""Local Windows audio preview for ClipForge: approximate sync from playback clock.

Uses built-in winsound and FFmpeg. Generates temporary WAV on seek; no cloud.
"""
from __future__ import annotations
import tempfile
import time
import subprocess
from pathlib import Path
import winsound
from clip_engine import FFMPEG

class AudioPreview:
    def __init__(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="vaw-review-audio-")
        self.source=None
        self.start=0.0
        self.total=0.0
        self.playing=False
        self.base=0.0
        self.clock=0.0
        self.current=None

    def load(self,source,start,total):
        self.stop()
        self.source=Path(source).resolve()
        self.start=float(start)
        self.total=float(total)
        self.base=0

    def play(self,seek=0):
        if not self.source:raise RuntimeError("No source video loaded")
        self.stop()
        seek=max(0,min(self.total-.05,float(seek)))
        wav=Path(self.tmp.name)/"preview.wav"
        if wav.exists():wav.unlink()
        cmd=[FFMPEG,"-hide_banner","-loglevel","error","-y",
             "-ss",f"{self.start+seek:.3f}","-i",str(self.source),
             "-t",f"{self.total-seek:.3f}","-vn","-ac","2",
             "-ar","22050","-c:a","pcm_s16le",str(wav)]
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=90)
        if p.returncode or not wav.exists() or wav.stat().st_size<60:
            raise RuntimeError("No usable audio track: "+p.stderr[-200:])
        winsound.PlaySound(str(wav),winsound.SND_FILENAME|winsound.SND_ASYNC|winsound.SND_NODEFAULT)
        self.base=seek
        self.clock=time.monotonic()
        self.current=wav
        self.playing=True

    def now(self):
        if not self.playing:return self.base
        return min(self.total,self.base+max(0,time.monotonic()-self.clock))

    def stop(self):
        if self.playing:
            self.base=self.now()
        winsound.PlaySound(None,0)
        self.playing=False

    def close(self):
        self.stop()
        self.tmp.cleanup()
