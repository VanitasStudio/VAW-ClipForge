from pathlib import Path
p=Path(__file__).with_name("clipforge_gui.py")
s=p.read_text(encoding="utf-8")
if "from subtitle_presets import PRESETS, preview_image" not in s:
    s=s.replace("from smart_reframe import export_v04",
                "from smart_reframe import export_v04\nfrom subtitle_presets import PRESETS, preview_image\nfrom PIL import ImageTk")
anchor='''        self.label(frame,"Gemini: compressed audio + optional sampled frames; up to 6 sections (retries possible).",'''
if anchor not in s:raise ValueError("main gallery insert anchor missing")
s=s.replace(anchor,'''        self.button(frame,"Browse Subtitle Modes",self.show_caption_styles).pack(anchor="w",pady=(3,8))
'''+anchor,1)
anchor='''    def refresh_key_status(self):'''
if anchor not in s:raise ValueError("main gallery method anchor missing")
method='''    def show_caption_styles(self):
        dialog=tk.Toplevel(self.root)
        dialog.title("Subtitle Modes | VAW ClipForge")
        dialog.geometry("870x650")
        dialog.configure(bg=C["bg"])
        self.label(dialog,"CHOOSE A SUBTITLE MODE",18,"white",True).pack(
            anchor="w",padx=20,pady=(16,5))
        self.label(dialog,"Click a style to apply it to new AI-generated clips.",
                   10,"muted").pack(anchor="w",padx=20,pady=(0,15))
        gallery=tk.Frame(dialog,bg=C["bg"])
        gallery.pack(fill="both",expand=True,padx=17)
        previews=[]
        for index,preset in enumerate(PRESETS):
            frame=tk.Frame(gallery,bg=C["card"],padx=7,pady=7)
            frame.grid(row=index//3,column=index%3,padx=7,pady=8,sticky="n")
            photo=ImageTk.PhotoImage(preview_image(preset.id,240,150,
                                         selected=self.caption_style.get()==preset.id))
            previews.append(photo)
            def select(style=preset.id):
                self.caption_style.set(style)
                self.log("Subtitle mode selected: "+style)
                dialog.destroy()
            tk.Button(frame,image=photo,command=select,borderwidth=0,
                      relief="flat",bg=C["card"],cursor="hand2").pack()
            tk.Label(frame,text=preset.name,bg=C["card"],fg=C["white"],
                     font=("Segoe UI Semibold",11),anchor="w").pack(fill="x",pady=(6,0))
            tk.Label(frame,text=preset.sub,bg=C["card"],fg=C["muted"],
                     font=("Segoe UI",9),anchor="w").pack(fill="x")
        dialog._images=previews

'''
s=s.replace(anchor,method+anchor,1)
p.write_text(s,encoding="utf-8")
print("Main ClipForge Subtitle Modes visual picker integrated.")
