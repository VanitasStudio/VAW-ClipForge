"""Patch VAW ClipForge GUI for multimodal AI + local auto captions."""
from pathlib import Path
p=Path(__file__).with_name("clipforge_gui.py")
s=p.read_text(encoding="utf-8")
s=s.replace("v0.2 | Gemini Highlight AI","v0.3 | Gemini AI + Auto-Captions")
s=s.replace('self.root.geometry("820x765")','self.root.geometry("850x825")')
s=s.replace('self.root.minsize(740,675)','self.root.minsize(750,745)')
s=s.replace('        self.model=tk.StringVar(value=MODEL)',
'''        self.model=tk.StringVar(value=MODEL)
        self.caption=tk.BooleanVar(value=True)
        self.burn=tk.BooleanVar(value=True)
        self.visual=tk.BooleanVar(value=True)''')
old='''        self.label(frame,"Gemini sends compressed audio excerpts to Google (up to 6 per run).",
                   10,"muted").pack(anchor="w",pady=(5,3))'''
new='''        checks=tk.Frame(frame,bg=C["bg"])
        checks.pack(fill="x",pady=(7,5))
        for var,label in [
            (self.visual,"AI analyzes sample frames too"),
            (self.caption,"Local auto-caption"),
            (self.burn,"Burn captions into Shorts"),
        ]:
            tk.Checkbutton(checks,text=label,variable=var,
                bg=C["bg"],fg=C["white"],selectcolor=C["card"],
                activebackground=C["bg"],activeforeground=C["white"],
                font=("Segoe UI",9)).pack(side="left",padx=(0,11))
        self.label(frame,"Gemini: compressed audio + optional sampled frames; up to 6 sections (retries possible).",
                   10,"muted").pack(anchor="w",pady=(5,3))'''
if old not in s:raise ValueError("GUI warning anchor missing")
s=s.replace(old,new)
s=s.replace(
'''            "This will send compressed audio excerpts from this video to Google AI.\n"
            "Maximum six requests. Costs or quotas depend on your Google project.\n"''',
'''            "This will send compressed audio excerpts and optionally sampled\n"
            "video frames to Google Gemini. Up to 6 sections; failures may retry.\n"
            "Costs/quotas depend on your Google API project.\n"'''
)
s=s.replace('''        model=self.model.get().strip()
        self.busy=True;self.run_btn.configure(state="disabled")''',
'''        model=self.model.get().strip()
        captions=self.caption.get()
        burn=self.burn.get()
        visual=self.visual.get()
        self.busy=True;self.run_btn.configure(state="disabled")''')
s=s.replace(
'''                    outcome=process_ai(source,dest,count,seconds,style,model,
                                       log=lambda x:self.messages.put(("log",x)))''',
'''                    outcome=process_ai(source,dest,count,seconds,style,model,
                                       log=lambda x:self.messages.put(("log",x)),visual=visual)'''
)
needle='''                self.messages.put(("done",f"Export complete: {len(outcome['clips'])} clips\n{dest}"))'''
if needle not in s:
    # Handle original f-string escape sequence representation
    needle='                self.messages.put(("done",f"Export complete: {len(outcome[\'clips\'])} clips\\n{dest}"))'
new='''                if captions:
                    from auto_captions import caption_output
                    outputs=[Path(x["path"]) for x in outcome["clips"]
                             if Path(x["path"]).is_file()]
                    if outputs:
                        outcome["caption_results"]=caption_output(
                            outputs,size="base",burn=burn,
                            log=lambda x:self.messages.put(("log",x)))
                        import json
                        manifest=dest/("ai-highlights.json" if ai else "clip-manifest.json")
                        if manifest.exists():
                            current=json.loads(manifest.read_text(encoding="utf-8"))
                            current["captions"]=outcome["caption_results"]
                            manifest.write_text(json.dumps(current,indent=2),encoding="utf-8")
                self.messages.put(("done",f"Export complete: {len(outcome['clips'])} clips\\n{dest}"))'''
if needle not in s:raise ValueError("GUI complete anchor missing")
s=s.replace(needle,new)
p.write_text(s,encoding="utf-8")
print("ClipForge GUI v0.3 patch applied")
