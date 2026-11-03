"""Small real-audio API test using synthetic sine wave; no personal audio uploaded."""
from pathlib import Path
from tempfile import TemporaryDirectory
from secure_config import load_key
from gemini_highlights import request_gemini, extract_audio, MODEL
source=Path(__file__).with_name("samples")/"synthetic-demo.mp4"
with TemporaryDirectory(prefix="vaw-audio-test-") as temp:
    file=Path(temp)/"tone.mp3"
    extract_audio(source,0,8,file)
    print("AUDIO_TEST_INPUT_BYTES",file.stat().st_size,flush=True)
    for model in [MODEL,"gemini-3.5-flash-lite"]:
        try:
            clips=request_gemini(file.read_bytes(),8,10,load_key(),model)
            print("AUDIO_TEST",model,"SUCCESS","CANDIDATES",len(clips),flush=True)
            break
        except Exception as e:
            print("AUDIO_TEST",model,"ERROR",str(e)[:190],flush=True)
