"""v0.4: wire scene-aware render and modern captions into existing GUI."""
from pathlib import Path
root=Path(__file__).resolve().parent
g=root/"gemini_highlights.py"
s=g.read_text(encoding="utf-8")
sig='dry_run=False,provider=None,visual=True):'
# already patched or safe to patch again
s=s.replace(sig,'dry_run=False,provider=None,visual=True,render=True):')
needle='''        if dry_run:
            continue
        cmd=[FFMPEG'''
# already patched or safe to patch again
s=s.replace(needle,'''        if dry_run or not render:
            continue
        cmd=[FFMPEG''')
g.write_text(s,encoding="utf-8")

p=root/"clipforge_gui.py"
s=p.read_text(encoding="utf-8")
s=s.replace("v0.3 | Gemini AI + Auto-Captions","v0.4 | Smart Reframe + Modern Captions")
s=s.replace('self.root.geometry("850x825")','self.root.geometry("900x885")')
s=s.replace('self.root.minsize(750,745)','self.root.minsize(805,780)')
s=s.replace('from test_gemini import test_gemini_connection',
            'from test_gemini import test_gemini_connection\nfrom smart_reframe import export_v04')
s=s.replace('        self.visual=tk.BooleanVar(value=True)',
'''        self.visual=tk.BooleanVar(value=True)
        self.autoframe=tk.BooleanVar(value=True)
        self.scenedetect=tk.BooleanVar(value=True)
        self.caption_style=tk.StringVar(value="modern")''')
anchor='''        self.label(frame,"Gemini: compressed audio + optional sampled frames; up to 6 sections (retries possible).",'''
if anchor not in s:raise ValueError("GUI checkboxes insert missing")
extra='''        advanced=tk.Frame(frame,bg=C["bg"])
        advanced.pack(fill="x",pady=(3,7))
        tk.Checkbutton(advanced,text="Auto-reframe: face + motion",
            variable=self.autoframe,bg=C["bg"],fg=C["white"],
            activebackground=C["bg"],activeforeground=C["white"],
            selectcolor=C["card"],font=("Segoe UI",9)).pack(side="left",padx=(0,18))
        tk.Checkbutton(advanced,text="Intelligent scene detection",
            variable=self.scenedetect,bg=C["bg"],fg=C["white"],
            activebackground=C["bg"],activeforeground=C["white"],
            selectcolor=C["card"],font=("Segoe UI",9)).pack(side="left",padx=(0,18))
        self.label(advanced,"Captions",9,"muted",True).pack(side="left",padx=(0,6))
        ttk.Combobox(advanced,textvariable=self.caption_style,state="readonly",
            values=["modern","clean"],width=11).pack(side="left")
'''
s=s.replace(anchor,extra+anchor)
s=s.replace(
'''        visual=self.visual.get()
        self.busy=True''',
'''        visual=self.visual.get()
        auto=self.autoframe.get()
        scene=self.scenedetect.get()
        cap_style=self.caption_style.get()
        self.busy=True''')
start='''                if ai:
                    outcome=process_ai(source,dest,count,seconds,style,model,
                                       log=lambda x:self.messages.put(("log",x)),visual=visual)
                else:
                    outcome=process_local(source,dest,count,seconds,style,
                                          log=lambda x:self.messages.put(("log",x)))
                if captions:'''
if start not in s:raise ValueError("GUI worker start anchor missing")
end='''                self.messages.put(("done",f"Export complete: {len(outcome['clips'])} clips\n{dest}"))'''
# end match intentionally uses except anchor instead
i=s.index(start)
j=s.index("            except Exception as exc:",i)
replacement='''                if ai:
                    selection=process_ai(source,dest,count,seconds,style,model,
                        log=lambda x:self.messages.put(("log",x)),
                        visual=visual,render=False)
                else:
                    selection=process_local(source,dest,count,seconds,style,
                        log=lambda x:self.messages.put(("log",x)),dry_run=True)
                self.messages.put(("log","Selecting scene-aware crops and styling captions..."))
                outcome=export_v04(source,dest,selection["clips"],
                    auto=auto,scenes=scene,captions=captions,
                    burn=burn,style=cap_style,layout=style,
                    log=lambda x:self.messages.put(("log",x)))
                completed=sum(bool(x.get("ok")) for x in outcome["clips"])
                if not completed:
                    raise RuntimeError("No clips exported. Check the activity log.")
                self.messages.put(("done",
                    f"V0.4 export complete: {completed}/{len(outcome['clips'])} clips\\n{dest}"))'''
s=s[:i]+replacement+s[j:]
p.write_text(s,encoding="utf-8")
print("v0.4 GUI and Gemini selectable-only render patch ready")
