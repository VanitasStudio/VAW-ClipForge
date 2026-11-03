"""Real URL download + cache QA using licensed Blender Foundation CC BY 3.0 footage.
Source listed by Wikimedia Commons: a 23-second Big Buck Bunny excerpt.
No credentials, Gemini calls or publication.
"""
from clipforge.url_source import check_link,fetch_video,cache_stats
from pathlib import Path
URL="https://www.youtube.com/watch?v=qzfWVYJNmAM"
print("METADATA",check_link(URL),flush=True)
item=fetch_video(URL,log=lambda x:print("URL_QA",x,flush=True))
print("URL_FILE",item["path"],"BYTES",Path(item["path"]).stat().st_size,flush=True)
again=fetch_video(URL,log=lambda x:print("CACHE_QA",x,flush=True))
print("CACHE_HIT",again["cached"],flush=True)
print("CACHE_SIZE",cache_stats(),flush=True)
