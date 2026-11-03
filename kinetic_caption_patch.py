"""ClipForge kinetic subtitles: highlight the word being spoken, not just a static word."""
from pathlib import Path
p=Path(__file__).with_name("stylish_captions.py")
s=p.read_text(encoding="utf-8")
s=s.replace('def emphasized_text(tokens):','def emphasized_text(tokens,active_index=None):')
s=s.replace('    chosen=max(candidates,key=lambda x:x[1])[0] if candidates else -1',
            '    chosen=active_index if active_index is not None else (max(candidates,key=lambda x:x[1])[0] if candidates else -1)')
old='''        phrase=emphasized_text(words) if mode=="modern" else safe_text(msg)
        style="Modern" if mode=="modern" else "Clean"
        # Absolute baseline 1088/1280; no libass font scaling surprises.
        effect=r"{\an2\pos(360,1088)\fad(70,65)\fscx102\fscy102\t(0,160,\fscx100\fscy100)}"
        ass.append(f"Dialogue: 0,{timestamp_ass(start)},{timestamp_ass(end)},"
                   f"{style},,0,0,0,,{effect}{phrase}\n")'''
new='''        # Absolute baseline 1088/1280; no libass font scaling surprises.
        if mode=="modern":
            # Keep the same short phrase visible while the red accent follows
            # the current spoken word. ASS overlays never overlap in time.
            boundaries=[start]
            for item in group[1:]:
                boundaries.append(max(boundaries[-1],min(end,float(item[0]))))
            boundaries.append(end)
            for word_index in range(len(group)):
                a,b=boundaries[word_index:word_index+2]
                if b<=a+0.02:
                    continue
                active=emphasized_text(words,word_index)
                fade=(r"\fad(55,0)" if word_index==0 else
                      r"\fad(0,55)" if word_index==len(group)-1 else "")
                effect=r"{\an2\pos(360,1088)"+fade+"}"
                ass.append(f"Dialogue: 0,{timestamp_ass(a)},{timestamp_ass(b)},"
                           f"Modern,,0,0,0,,{effect}{active}\n")
        else:
            effect=r"{\an2\pos(360,1088)\fad(70,65)}"
            ass.append(f"Dialogue: 0,{timestamp_ass(start)},{timestamp_ass(end)},"
                       f"Clean,,0,0,0,,{effect}{safe_text(msg)}\n")'''
if old not in s:
    raise ValueError("Caption generation block missing")
s=s.replace(old,new)
p.write_text(s,encoding="utf-8")
print("Word-synchronous karaoke emphasis implemented.")
