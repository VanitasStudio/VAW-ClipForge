"""Bring all six v0.6 subtitle presets into ClipForge main auto-caption render."""
from pathlib import Path
root=Path(__file__).parent
p=root/"subtitle_presets.py"
s=p.read_text(encoding="utf-8")
s=s.replace('''        for j in range(n if preset.animated else 1):
            a=start+(end-start)*j/n if preset.animated else start
            b=start+(end-start)*(j+1)/n if preset.animated else end''',
'''        word_spans=row.get("word_spans",[])
        for j in range(n if preset.animated else 1):
            if preset.animated and len(word_spans)==n:
                a=max(start,min(end,float(word_spans[j][0])))
                b=max(a+0.012,min(end,float(word_spans[j+1][0]) if j+1<n else end))
            else:
                a=start+(end-start)*j/n if preset.animated else start
                b=start+(end-start)*(j+1)/n if preset.animated else end''')
p.write_text(s,encoding="utf-8")

p=root/"stylish_captions.py"
s=p.read_text(encoding="utf-8")
s=s.replace('from clip_engine import FFMPEG','from clip_engine import FFMPEG\nfrom subtitle_presets import caption_ass',1)
s=s.replace('''    srt=[];ass=[ASS_HEADER]
    previous_end=0.0''','''    srt=[];ass=[ASS_HEADER]
    rows=[]
    previous_end=0.0''')
s=s.replace('''        srt.append(f"{n}\\n{stamp(start)} --> {stamp(end)}\\n{msg}\\n")''',
'''        srt.append(f"{n}\\n{stamp(start)} --> {stamp(end)}\\n{msg}\\n")
        rows.append({"start":start,"end":end,"text":msg,
                     "word_spans":[(float(w[0]),float(w[1])) for w in group]})''')
s=s.replace('''    assfile.write_text("\\n".join(ass),encoding="utf-8-sig")''',
'''    assfile.write_text(caption_ass(rows,mode),encoding="utf-8-sig")''')
p.write_text(s,encoding="utf-8")

p=root/"clipforge_gui.py"
s=p.read_text(encoding="utf-8")
s=s.replace("VAW ClipForge v0.5 | Smart Clips + Timeline Review",
            "VAW ClipForge v0.6 | Smart Clips + Subtitle Modes")
s=s.replace('self.caption_style=tk.StringVar(value="modern")',
            'self.caption_style=tk.StringVar(value="karaoke")')
s=s.replace('values=["modern","clean"],width=11',
            'values=["karaoke","bold_pop","minimal","gaming","neon","creator"],width=12')
p.write_text(s,encoding="utf-8")
print("Six subtitle modes wired into both Review Studio and ClipForge generator.")
