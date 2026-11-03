from pathlib import Path
p=Path(__file__).with_name("review_editor.py")
s=p.read_text(encoding="utf-8")
a=s.index('        self.label(right,"Modern = highlighted active word;')
b=s.index('9,"sub",justify="left").pack(anchor="w")',a)+len('9,"sub",justify="left").pack(anchor="w")')
s=s[:a]+'''        self.label(right,"Choose from six caption presets. Edited words use\\n"
                         "approximate timing; verify the final video before posting.",
                   9,"sub",justify="left").pack(anchor="w")'''+s[b:]
a=s.index('''        self.label(controls,"Audio clock sync''')
b=s.index('''pack(side="right")''',a)+len('pack(side="right")')
s=s[:a]+'''        self.label(controls,"Audio clock preview - near-real-time sync",9,"sub").pack(side="right")'''+s[b:]
a=s.index('''        self.label(left,"Blue: scene''')
b=s.index('''pack(anchor="w",pady=(5,0))''',a)+len('pack(anchor="w",pady=(5,0))')
s=s[:a]+'''        self.label(left,"Blue = scene | Pink = caption | Yellow = focus | Purple = dip",
                   9,"sub").pack(anchor="w",pady=(5,0))'''+s[b:]
s=s.replace('''        words=text.split()
        active=0''','''        preset=choose(self.style.get())
        words=text.upper().split() if preset.uppercase else text.split()
        active=0''',1)
s=s.replace('''                is_active=(index==active and self.style.get()=="modern")
                draw.text((x,y),word,font=font,
                          fill="#ff5e73" if is_active else "#ffffff",''',
'''                is_active=(index==active and preset.animated)
                draw.text((x,y),word,font=font,
                          fill=preset.accent if is_active else preset.white,''',1)
p.write_text(s,encoding="utf-8")
print("Review Studio UI text and subtitle live preview polished.")
