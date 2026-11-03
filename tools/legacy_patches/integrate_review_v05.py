"""Integrate v0.5 review/timeline editor into the existing ClipForge v0.4 GUI."""
from pathlib import Path
p=Path(__file__).with_name("clipforge_gui.py")
s=p.read_text(encoding="utf-8")
s=s.replace("import os\n","import os\nimport sys\nimport subprocess\n",1)
s=s.replace('v0.4 | Smart Reframe + Modern Captions',
            'v0.5 | Smart Clips + Timeline Review')
anchor='''        self.button(r,"Open Exports",self.open_export).pack(side="left",padx=10)'''
if anchor not in s:raise ValueError("Open exports button not found")
s=s.replace(anchor,anchor+'''
        self.button(r,"Review / Timeline",self.open_review).pack(side="left",padx=5)''')
method='''    def open_review(self):
        folder=self.last_export if self.last_export and self.last_export.exists() else Path(self.dest.get())/"videoplayback"
        candidate=None
        manifest=folder/"v04-manifest.json"
        if manifest.exists():
            try:
                import json
                payload=json.loads(manifest.read_text(encoding="utf-8"))
                recent=[Path(x["output"]) for x in payload.get("clips",[])
                        if x.get("ok") and Path(x["output"]).is_file()]
                if recent:candidate=recent[-1]
            except (OSError,ValueError,KeyError):
                pass
        args=[sys.executable,str(ROOT/"review_editor.py")]
        if candidate:args.extend(["--clip",str(candidate)])
        try:
            subprocess.Popen(args,cwd=str(ROOT))
            self.log("Review & Timeline editor opened. Correct captions and framing there.")
        except OSError as exc:
            messagebox.showerror("Editor launch failed",str(exc))
'''
anchor='''    def open_export(self):'''
if anchor not in s:raise ValueError("Method insertion anchor missing")
s=s.replace(anchor,method+anchor)
p.write_text(s,encoding="utf-8")
print("Main app v0.5 integration complete")
