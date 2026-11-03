"""VAW ClipForge URL input — authorized public video from URL, local cache.

Supports single public YouTube, TikTok and Vimeo video URLs via yt-dlp.
No account cookies, DRM bypass, playlist scraping, or publishing.
Downloads to a dedicated user-controlled cache; existing source is never altered.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import shutil
from pathlib import Path
from urllib.parse import urlsplit

import yt_dlp
from clip_engine import FFMPEG

# yt-dlp uses its own subprocess.Popen subclass for FFmpeg merge. Keep that
# subclass's Windows startup setting explicitly hidden (SW_HIDE).
if os.name=="nt":
    from yt_dlp.utils import Popen as YtDlpPopen
    if YtDlpPopen._startupinfo is not None:
        import subprocess as _subprocess
        YtDlpPopen._startupinfo.dwFlags |= _subprocess.STARTF_USESHOWWINDOW
        YtDlpPopen._startupinfo.wShowWindow = _subprocess.SW_HIDE

ROOT=Path(__file__).resolve().parent
CACHE=ROOT/"url-cache"
BIN=ROOT/"bin"
SAFE_DOMAINS=("youtube.com","youtu.be","youtube-nocookie.com",
              "tiktok.com","vimeo.com")
MAX_MEDIA_BYTES=4*1024**3

def validate_url(value: str) -> str:
    url=value.strip()
    if not url or len(url)>2048:
        raise ValueError("Paste one public video URL (max 2048 chars).")
    try:
        p=urlsplit(url)
    except ValueError:
        raise ValueError("Malformed video URL.") from None
    if p.scheme.lower()!="https":
        raise ValueError("Only HTTPS video URLs are supported.")
    if p.username or p.password or p.port not in (None,443):
        raise ValueError("URLs with credentials or alternate ports are blocked.")
    hostname=(p.hostname or "").rstrip(".").lower()
    if not hostname or any(ord(c)>127 for c in hostname):
        raise ValueError("Invalid video host.")
    allowed=any(hostname==domain or hostname.endswith("."+domain)
                for domain in SAFE_DOMAINS)
    if not allowed:
        raise ValueError("Supported sites: YouTube, TikTok and Vimeo (public videos only).")
    try:
        ipaddress.ip_address(hostname)
        raise ValueError("IP address URLs are not allowed.")
    except ValueError as err:
        if "not allowed" in str(err):
            raise
    if p.path in ("","/") and hostname not in ("youtu.be",):
        raise ValueError("Paste a link to one specific video, not a site home page.")
    return url

def _ensure_ffmpeg():
    """yt-dlp merger expects a conventional ffmpeg.exe filename."""
    BIN.mkdir(parents=True,exist_ok=True)
    exe=BIN/"ffmpeg.exe"
    source=Path(FFMPEG)
    if not exe.is_file() or exe.stat().st_size!=source.stat().st_size:
        shutil.copy2(source,exe)
    return str(exe)

def _slug(s):
    result=re.sub(r"[^a-z0-9]+","-",str(s).lower()).strip("-")
    return result[:46] or "video"

def _key(url):
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]

def _entry_location(url):
    key=_key(url)
    folder=CACHE/key
    return folder,folder/"source.json"

def _cached(url,log=print):
    folder,meta=_entry_location(url)
    if not meta.is_file():return None
    try:
        data=json.loads(meta.read_text(encoding="utf-8"))
        media=folder/data["filename"]
        if (data.get("key")==_key(url) and media.is_file()
            and 0<media.stat().st_size<=MAX_MEDIA_BYTES):
            log("Using previously downloaded source (cache hit).")
            return {"path":media,"title":data.get("title","video"),
                    "id":data.get("id",""),
                    "source_name":data.get("source_name",media.stem),
                    "cached":True,"resolution":data.get("resolution")}
    except (OSError,ValueError,KeyError):
        pass
    return None

def _settings(folder,log):
    ffmpeg=_ensure_ffmpeg()
    def hook(event):
        if event.get("status")=="downloading":
            pct=event.get("_percent_str","").strip()
            eta=event.get("_eta_str","").strip()
            # Progress hooks run often: show meaningful progression, not raw URLs.
            try:
                value=int(float(pct.replace("%","").strip()))
            except (ValueError,TypeError):
                return
            if value//10!=getattr(hook,"last",-1):
                hook.last=value//10
                log(f"Downloading source: ~{value}% (ETA {eta or 'unknown'})")
        elif event.get("status")=="finished":
            log("Source downloaded; preparing video/audio merge.")
    hook.last=-1
    return {
        "format":"bv[height<=1080]+ba/b[height<=1080]/best",
        "merge_output_format":"mp4",
        "outtmpl":str(folder/"source.%(ext)s"),
        "ffmpeg_location":ffmpeg,
        "noplaylist":True,
        "ignoreerrors":False,
        "no_warnings":True,
        "quiet":True,
        "retries":3,
        "fragment_retries":3,
        "socket_timeout":25,
        "max_filesize":MAX_MEDIA_BYTES,
        "progress_hooks":[hook],
        "restrictfilenames":True,
        "cachedir":False,
        "windowsfilenames":True,
        "continuedl":True,
        "overwrites":False,
    }

def _summary(info):
    if not isinstance(info,dict) or info.get("_type") in ("playlist","multi_video"):
        raise ValueError("Only a single public video is supported; playlists/channels are disabled.")
    title=str(info.get("title") or "Video")[:150]
    return {"title":title,"id":str(info.get("id") or "")[:100],
            "duration":info.get("duration"),"width":info.get("width"),
            "height":info.get("height"),"extractor":info.get("extractor_key")}

def check_link(url,log=print):
    """Check public metadata without downloading; metadata can still make web requests."""
    url=validate_url(url)
    cached=_cached(url,log=lambda _:None)
    if cached:
        return {"title":cached["title"],"id":cached["id"],"cached":True,
                "resolution":cached.get("resolution")}
    folder,_=_entry_location(url)
    settings=_settings(folder,lambda _:None)
    with yt_dlp.YoutubeDL(settings) as ydl:
        info=ydl.extract_info(url,download=False)
    return {**_summary(info),"cached":False}

def fetch_video(url,log=print):
    """Download one public video at highest available <=1080p, caching source file."""
    url=validate_url(url)
    cached=_cached(url,log)
    if cached:return cached
    folder,meta=_entry_location(url)
    folder.mkdir(parents=True,exist_ok=True)
    settings=_settings(folder,log)
    log("Resolving supported video link (YouTube / TikTok / Vimeo)...")
    try:
        with yt_dlp.YoutubeDL(settings) as ydl:
            info=ydl.extract_info(url,download=True)
            summary=_summary(info)
    except yt_dlp.utils.DownloadError:
        raise RuntimeError("Video download failed. Check that it is public, supported, "
                           "accessible from this PC and permitted for reuse. "
                           "Private, protected or restricted videos are not bypassed.") from None
    videos=sorted(
        [p for p in folder.glob("source.*") if p.suffix.lower() in
         {".mp4",".mkv",".mov",".webm",".m4v"} and p.is_file()],
        key=lambda p:p.stat().st_size,reverse=True)
    if not videos:
        raise RuntimeError("Download completed but no usable video file was found.")
    media=videos[0]
    if media.stat().st_size>MAX_MEDIA_BYTES:
        raise RuntimeError("Downloaded video exceeded 4 GiB safety limit.")
    name=_slug(summary["title"])+"-"+_slug(summary["id"])[:20]
    data={
        "key":_key(url),"filename":media.name,"title":summary["title"],
        "id":summary["id"],"source_name":name,
        "resolution":f"{summary.get('width') or '?'}x{summary.get('height') or '?'}",
        "site":urlsplit(url).hostname,
    }
    meta.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    log(f"Source ready: {summary['title'][:70]} "
        f"({round(media.stat().st_size/(1024**2),1)} MiB)")
    return {"path":media,"title":summary["title"],"id":summary["id"],
            "source_name":name,"resolution":data["resolution"],"cached":False}

def cache_stats():
    if not CACHE.exists():return 0,0
    files=list(CACHE.rglob("source.json"))
    size=sum(p.stat().st_size for p in CACHE.rglob("*") if p.is_file())
    return len(files),size

def clear_cache():
    """Only deletes app's dedicated downloaded source cache, never exported clips."""
    if CACHE.resolve()==ROOT.resolve():
        raise RuntimeError("Unsafe cache target")
    if CACHE.is_dir():shutil.rmtree(CACHE)
