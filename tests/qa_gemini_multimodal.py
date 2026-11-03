from pathlib import Path
from tempfile import TemporaryDirectory
from clipforge.gemini_highlights import extract_audio, sampled_frames, request_gemini, probe_duration, MODEL
from clipforge.secure_config import load_key
source=Path(__file__).resolve().parents[1]/"samples"/"spoken-test.mp4"
length=probe_duration(source)
with TemporaryDirectory(prefix="vaw-gemini-qa-") as folder:
    t=Path(folder)
    audio=t/"clip.mp3"
    extract_audio(source,0,length,audio)
    frames=sampled_frames(source,0,length,t)
    print("QA_INPUT_SECONDS",round(length,1),"FRAMES",len(frames),flush=True)
    for model in [MODEL,"gemini-3.5-flash-lite"]:
        try:
            result=request_gemini(audio.read_bytes(),length,8,load_key(),model,frames)
            print("QA_GEMINI_SUCCESS",model,"CLIPS",len(result),flush=True)
            print("QA_HIGHLIGHT_TIMES",[(round(x["start"],1),round(x["end"],1),x["score"]) for x in result],flush=True)
            break
        except Exception as exc:
            print("QA_GEMINI_ERROR",model,type(exc).__name__,str(exc)[:130],flush=True)
