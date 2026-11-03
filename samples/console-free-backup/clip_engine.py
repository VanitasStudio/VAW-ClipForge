"""VAW ClipForge v0.1: offline heuristic candidate clips from user-owned local videos.
No semantic AI, no upload, no deletion of original media.
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
import imageio_ffmpeg
import numpy as np

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
EXTS = {".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4v"}

def probe_duration(src):
    result = subprocess.run([FFMPEG, "-hide_banner", "-i", str(src)],
                            capture_output=True, text=True, timeout=30)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
    if not m:
        raise ValueError("Video duration not detected")
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])

def scan_audio(src, log=print):
    proc = subprocess.Popen(
        [FFMPEG, "-hide_banner", "-loglevel", "error", "-i", str(src),
         "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "pipe:1"],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    energies = []
    while True:
        chunk = proc.stdout.read(16000)
        if not chunk:
            break
        samples = np.frombuffer(chunk, dtype="<i2").astype(np.float32)
        if len(samples):
            energies.append(float(np.sqrt(np.mean(samples*samples)) / 32768))
        if len(energies) % 120 == 0 and energies:
            log(f"Audio analyzed: {len(energies)} seconds")
    proc.stdout.close()
    proc.wait(timeout=30)
    return np.array(energies, dtype=np.float32)

def candidates(total, energies, seconds, clips):
    if total < 5:
        raise ValueError("Source is too short; need at least 5 seconds")
    seconds = min(seconds, int(total))
    if len(energies) < 3 or float(energies.max()) < 0.00001:
        count = min(clips, max(1, int(total // seconds)))
        starts = np.linspace(0, max(0, total-seconds), count)
        return [{"start": float(x), "duration": seconds, "score": 0} for x in starts]
    smooth = np.convolve(energies, [0.25,0.5,0.25], "same")
    loud = np.log1p(45 * smooth)
    sums = np.r_[0.0, np.cumsum(loud)]
    possible = []
    for t in range(0, max(1, int(total-seconds)+1), 2):
        b = min(t, len(loud)-1)
        e = min(len(loud), b+seconds)
        if e <= b:
            continue
        value = float(0.8 * (sums[e]-sums[b])/(e-b) +
                      0.2 * np.quantile(loud[b:e], 0.85))
        possible.append((value,t))
    possible.sort(reverse=True)
    picks = []
    for score,t in possible:
        if all(abs(t-v["start"]) >= seconds+2 for v in picks):
            picks.append({"start": t, "duration": seconds, "score": round(score,4)})
        if len(picks) >= clips:
            break
    return sorted(picks, key=lambda v:v["start"])

OUTPUT_SIZES={"720p":(720,1280),"1080p":(1080,1920)}

def filter_graph(style,resolution="720p"):
    if resolution not in OUTPUT_SIZES:
        raise ValueError("Choose 720p or 1080p vertical output")
    w,h=OUTPUT_SIZES[resolution]
    if style=="crop":
        return (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                f"crop={w}:{h},setsar=1,format=yuv420p")
    if style=="fit":
        return (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,format=yuv420p")
    if style!="blur":
        raise ValueError("Invalid layout")
    return (f"split=2[fg][bg];[bg]scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},boxblur=18:1[back];"
            f"[fg]scale={w}:{h}:force_original_aspect_ratio=decrease[front];"
            "[back][front]overlay=(W-w)/2:(H-h)/2,setsar=1,format=yuv420p")


def process(src, dest, clips=3, seconds=30, style="blur", log=print, dry_run=False):
    src, dest = Path(src).resolve(), Path(dest).resolve()
    if not src.is_file() or src.suffix.lower() not in EXTS:
        raise ValueError("Choose a valid video file: MP4, MKV, MOV, WEBM, AVI, M4V")
    if not 1 <= clips <= 20 or not 5 <= seconds <= 180:
        raise ValueError("Clips 1â€“20 and duration 5â€“180 seconds only")
    if style not in {"blur", "crop", "fit"}:
        raise ValueError("Invalid 9:16 style")
    total = probe_duration(src)
    log(f"Input: {src.name} ({total:.1f} seconds)")
    levels = scan_audio(src, log)
    items = candidates(total, levels, seconds, clips)
    if not dry_run:
        dest.mkdir(parents=True, exist_ok=True)
    output = {"version":"0.1", "source":str(src), "created":datetime.now().isoformat(),
              "method":"audio energy heuristics (NOT semantic AI)", "style":style, "clips":[]}
    for i, item in enumerate(items,1):
        path = dest / f"{src.stem}_clip_{i:02d}_{int(item['start']):05d}s.mp4"
        output["clips"].append({**item, "path":str(path)})
        log(f"Clip {i}: {item['start']:.1f} â€“ {item['start']+item['duration']:.1f}s")
        if dry_run:
            continue
        cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
               "-ss", str(item["start"]), "-i", str(src),
               "-t", str(item["duration"]), "-vf", filter_graph(style), "-r", "30",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
               "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(path)]
        r = subprocess.run(cmd, text=True, capture_output=True, timeout=420)
        if r.returncode:
            raise RuntimeError(f"Render failed for clip {i}: {r.stderr[-900:]}")
        log(f"Saved {path.name}")
    if not dry_run:
        (dest/"clip-manifest.json").write_text(json.dumps(output,indent=2),encoding="utf-8")
    return output

if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input",type=Path)
    ap.add_argument("--output","-o",type=Path,default=Path("exports"))
    ap.add_argument("--clips",type=int,default=3)
    ap.add_argument("--seconds",type=int,default=30)
    ap.add_argument("--style",choices=["blur","fit","crop"],default="blur")
    ap.add_argument("--dry-run",action="store_true")
    a=ap.parse_args()
    process(a.input,a.output,a.clips,a.seconds,a.style,dry_run=a.dry_run)
