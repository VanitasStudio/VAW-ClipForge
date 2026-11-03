from faster_whisper import WhisperModel
from pathlib import Path
print("loading",flush=True)
model=WhisperModel("base",device="cpu",compute_type="int8",download_root="D:/YouTubeAutomation/VAW-ClipForge/models")
print("transcribing",flush=True)
segments,info=model.transcribe(str(Path("samples/spoken-test.mp4")),beam_size=1,word_timestamps=True,vad_filter=True)
for segment in segments: print(segment.text)
