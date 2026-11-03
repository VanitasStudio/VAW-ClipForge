from pathlib import Path
p=Path(__file__).with_name("patch_review_ui_v06.py")
s=p.read_text(encoding="utf-8")
bad="â–¶"
print("bad_unicode_count",s.count(bad))
try:
    repaired=s.encode("cp1252").decode("utf-8")
except UnicodeError as e:
    print("Cannot globally undo encoding",type(e).__name__)
    repaired=s.replace("â–¶","▶").replace("â¸","⏸").replace("â€¢","•")
p.write_text(repaired,encoding="utf-8")
print("ready")
