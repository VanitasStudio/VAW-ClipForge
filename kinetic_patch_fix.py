from pathlib import Path
p=Path(__file__).with_name("stylish_captions.py")
s=p.read_text(encoding="utf-8")
s=s.replace("def emphasized_text(tokens):","def emphasized_text(tokens,active_index=None):")
s=s.replace("    chosen=max(candidates,key=lambda x:x[1])[0] if candidates else -1",
            "    chosen=active_index if active_index is not None else (max(candidates,key=lambda x:x[1])[0] if candidates else -1)")
start=s.index('        phrase=emphasized_text(words)')
end=s.index('    srtfile=clip.with_suffix(".srt")',start)
replace=r'''        # Absolute baseline 1088/1280; no libass font scaling surprises.
        if mode=="modern":
            # Stable phrase, animated color follows the spoken word.
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
                       f"Clean,,0,0,0,,{effect}{safe_text(msg)}\n")
'''
s=s[:start]+replace+s[end:]
p.write_text(s,encoding="utf-8")
print("Kinetic captions patched")
