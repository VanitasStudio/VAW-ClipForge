from pathlib import Path
import re
root=Path(__file__).parent
p=root/"review_editor.py"
s=p.read_text(encoding="utf-8")
# Replace mojibake labels without changing the functional code.
s=re.sub(r'self\.label\(dialog,"Visual presets for 9:16 Shorts[^"]*"',
         'self.label(dialog,"Visual presets for 9:16 Shorts | click a card to apply"',s)
s=re.sub(r'self\.label\(dialog,"Rendered captions use a safe bottom region[^"]*"',
         'self.label(dialog,"Rendered captions use a safe bottom region (720x1280)."',s)
s=s.replace('''            self.label(card,preset.name,11,bold=True).pack(anchor="w",pady=(6,0))
            self.label(card,preset.sub,9,"sub").pack(anchor="w")''',
'''            tk.Label(card,text=preset.name,font=("Segoe UI Semibold",11),
                     bg=COLORS["panel"],fg=COLORS["text"],
                     anchor="w").pack(fill="x",pady=(6,0))
            tk.Label(card,text=preset.sub,font=("Segoe UI",9),
                     bg=COLORS["panel"],fg=COLORS["sub"],
                     anchor="w").pack(fill="x")''')
p.write_text(s,encoding="utf-8")
p=root/"subtitle_presets.py"
s=p.read_text(encoding="utf-8")
s=s.replace('''    draw.text((16,height-28),preset.name,font=font2,fill="#FFFFFF")
    return image''',
'''    return image''')
p.write_text(s,encoding="utf-8")
print("Gallery label encoding and card backgrounds polished.")
