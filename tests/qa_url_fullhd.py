from pathlib import Path
import subprocess
from clip_engine import FFMPEG
from smart_reframe import smart_render
from url_source import validate_url,_ensure_ffmpeg,cache_stats,check_link
root=Path(__file__).resolve().parents[1]
source=root/"samples"/"spoken-test.mp4"
output=root/"samples"/"quality-1080-test.mp4"
result=smart_render(source,output,auto=True,scenes=False,
                    subject_mode="universal",resolution="1080p")
print("HD_RENDER",output.exists(),output.stat().st_size,"DIMENSIONS",result.get("output_resolution"),flush=True)
probe=subprocess.run([FFMPEG,"-hide_banner","-i",str(output)],
                     capture_output=True,text=True,timeout=25)
print("HD_STREAM",[line.strip() for line in probe.stderr.splitlines() if "Video:" in line][:1],flush=True)
print("URL_VALID_YOUTUBE",validate_url("https://www.youtube.com/watch?v=jNQXAC9IVRw"),flush=True)
print("URL_VALID_TIKTOK",validate_url("https://www.tiktok.com/@creator/video/761234567890"),flush=True)
for bad in ("file:///c:/Users/test/test.mp4","http://www.youtube.com/watch?v=1",
            "https://example.com/watch?v=1","https://youtube.com.evil.example/watch?v=1",
            "https://127.0.0.1/video.mp4"):
    try:
        validate_url(bad)
        print("BLOCK_TEST_FAILED",bad)
    except ValueError:
        print("BLOCK_OK",bad.split("/")[2] if "/" in bad else "file")
binary=Path(_ensure_ffmpeg())
print("YT_DLP_FFMPEG",binary.exists(),binary.stat().st_size,flush=True)
print("CACHE_STATS",cache_stats(),flush=True)
