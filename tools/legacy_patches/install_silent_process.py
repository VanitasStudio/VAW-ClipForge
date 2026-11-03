"""Install silent subprocess launching across ClipForge production modules."""
from pathlib import Path

BASE=Path(__file__).resolve().parent
FILES=[
    "audio_preview.py",
    "auto_captions.py",
    "clip_engine.py",
    "clipforge_gui.py",
    "gemini_highlights.py",
    "review_core.py",
    "secure_config.py",
    "smart_reframe.py",
    "stylish_captions.py",
]
for name in FILES:
    p=BASE/name
    code=p.read_text(encoding="utf-8")
    before=code
    if "import subprocess" not in code:
        raise RuntimeError(f"Missing expected import in {name}")
    imports="from silent_process import run as silent_run, popen as silent_popen"
    if imports not in code:
        code=code.replace("import subprocess\n", "import subprocess\n"+imports+"\n",1)
    code=code.replace("subprocess.run(", "silent_run(")
    code=code.replace("subprocess.Popen(", "silent_popen(")
    if code==before:
        raise RuntimeError(f"Nothing patched in {name}")
    # Keep original backups in a separate dev QA folder, never overwrite originals.
    backup=BASE/"samples"/"console-free-backup"
    backup.mkdir(parents=True,exist_ok=True)
    old=backup/name
    if not old.exists():
        old.write_text(before,encoding="utf-8")
    p.write_text(code,encoding="utf-8")
    print(name,"RUN_CALLS",code.count("silent_run("),
          "POPEN_CALLS",code.count("silent_popen("))

# yt-dlp already has Popen startupinfo/SW_HIDE, explicitly confirm at app import
p=BASE/"url_source.py"
s=p.read_text(encoding="utf-8")
original=s
anchor="from clip_engine import FFMPEG\n"
if anchor not in s:
    raise RuntimeError("Missing URL module import anchor")
s=s.replace(anchor,anchor+'''
# yt-dlp uses its own subprocess.Popen subclass for FFmpeg merge. Keep that
# subclass's Windows startup setting explicitly hidden (SW_HIDE).
if os.name=="nt":
    from yt_dlp.utils import Popen as YtDlpPopen
    if YtDlpPopen._startupinfo is not None:
        import subprocess as _subprocess
        YtDlpPopen._startupinfo.dwFlags |= _subprocess.STARTF_USESHOWWINDOW
        YtDlpPopen._startupinfo.wShowWindow = _subprocess.SW_HIDE
''',1)
backup=BASE/"samples"/"console-free-backup"/"url_source.py"
if not backup.exists():backup.write_text(original,encoding="utf-8")
p.write_text(s,encoding="utf-8")
print("yt-dlp ffmpeg merge window hide enabled")
