from pathlib import Path
import ast
import re

from subtitle_presets import PRESETS, choose, caption_ass, preview_image
from stylish_captions import format_caption_text

ids=[p.id for p in PRESETS]
names=[p.name for p in PRESETS]
assert len(ids)==len(set(ids))
assert "all_caps" in ids
assert "All Capital Subtitle" in names

preset=choose("all_caps")
assert preset.uppercase is True
assert preset.animated is True

rows=[{
    "start":0.0,
    "end":1.8,
    "text":"This is the result",
    "word_spans":[(0.0,0.3),(0.31,0.55),(0.56,0.85),(0.86,1.35)]
}]
ass=caption_ass(rows,"all_caps")
dialogues=[line for line in ass.splitlines() if line.startswith("Dialogue:")]
plain=re.sub(r"\{[^}]*\}","",dialogues[0].split(",,")[-1])
assert plain=="THIS IS THE RESULT",plain
assert "THIS" in ass and "RESULT" in ass
assert choose("all capital subtitle").id=="all_caps"
assert format_caption_text("This is the result","all_caps")=="THIS IS THE RESULT"
assert format_caption_text("This is the result","karaoke")=="This is the result"

# Exercise the real caption-file writer with a mocked local Whisper response.
import stylish_captions
from types import SimpleNamespace
class MockWhisper:
    def transcribe(self,*args,**kwargs):
        words=[
            SimpleNamespace(word="This",start=0.0,end=0.28),
            SimpleNamespace(word="is",start=0.30,end=0.48),
            SimpleNamespace(word="the",start=0.50,end=0.70),
            SimpleNamespace(word="result",start=0.72,end=1.20),
        ]
        return [SimpleNamespace(words=words)],None
original_get_model=stylish_captions.get_model
stylish_captions.get_model=lambda model,log:MockWhisper()
try:
    import tempfile
    with tempfile.TemporaryDirectory(prefix="clipforge-allcaps-") as tmp:
        clip=Path(tmp)/"sample.mp4"
        clip.write_bytes(b"mock")
        assfile,srtfile,count=stylish_captions.generate_caption_files(
            clip,mode="all_caps",log=lambda _m:None)
        srt_text=srtfile.read_text(encoding="utf-8")
        ass_text=assfile.read_text(encoding="utf-8-sig")
        assert count==1
        assert "THIS IS THE RESULT" in srt_text,srt_text
        assert "THIS" in ass_text and "RESULT" in ass_text
finally:
    stylish_captions.get_model=original_get_model

preview=preview_image("all_caps",240,150,selected=True)
assert preview.size==(240,150)

source=(Path(__file__).resolve().parents[1] / "clipforge_gui.py").read_text(encoding="utf-8")
ast.parse(source)
assert "def create_ui(self):" in source
assert "def set_caption_from_label(self,_=None):" in source
assert "AI EDITORIAL STUDIO" in source
assert "All Capital forces every spoken word into uppercase." in source
assert "values=[p.name for p in PRESETS]" in source
print("PRESET_COUNT",len(PRESETS))
print("ALL_CAPITAL_RENDERED",plain)
print("ALL_CAPITAL_ALIAS_PASS")
print("SUBTITLE_PREVIEW_PASS")
print("GUI_AST_AND_MODE_BINDING_PASS")
print("UI_REFRESH_QA_PASS")
