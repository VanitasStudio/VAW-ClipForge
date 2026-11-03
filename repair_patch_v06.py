from pathlib import Path
p=Path(__file__).with_name("patch_review_ui_v06.py")
s=p.read_text(encoding="utf-8")
s=s.replace('    if old not in s: raise ValueError("Missing "+label)',
'''    if old not in s:
        if label in ("play button", "audio transport"):
            print("Compatibility note: replacing",label,"separately.")
            return
        raise ValueError("Missing "+label)''')
anchor='p.write_text(s,encoding="utf-8")'
inject=r'''# Unicode-safe audio transport patch, independent of the v0.5 play icon.
import re
s=re.sub(r'self\.play_btn=self\.btn\(controls,"[^"]*Silent Preview",self\.toggle_play\)',
         'self.play_btn=self.btn(controls,"Play with Audio",self.toggle_play)',s)
start=s.index("    def scrub(self,_=None):")
end=s.index("    def focus_changed(self,_=None):",start)
replacement="""    def scrub(self,_=None):
        if self.in_scrub:return
        if self.playing:
            self.audio.stop()
            self.playing=False
            self.play_btn.configure(text="Play with Audio")
        self.pending_focus=None
        self.update_frame()

    def toggle_play(self):
        if not self.data:return
        if self.playing:
            self.audio.stop()
            self.playing=False
            self.play_btn.configure(text="Play with Audio")
            return
        try:
            self.audio.play(self.position.get())
            self.playing=True
            self.play_btn.configure(text="Pause Audio")
            self.tick()
        except Exception as exc:
            self.status.set("Audio playback failed: "+str(exc)[:110])
            messagebox.showerror("Audio preview",str(exc))

    def tick(self):
        if not self.playing or not self.data:return
        target=self.audio.now()
        if target>=self.data["duration"]-.05:
            self.audio.stop()
            self.playing=False
            self.play_btn.configure(text="Play with Audio")
            return
        self.in_scrub=True
        self.position.set(round(target,2))
        self.in_scrub=False
        self.pending_focus=None
        self.update_frame()
        self.app.after(110,self.tick)

"""
s=s[:start]+replacement+s[end:]
s=s.replace("VAW ClipForge v0.5 | Review & Timeline Editor",
            "VAW ClipForge v0.6 | Creative Review Studio")
'''
if anchor not in s:raise RuntimeError("write anchor missing")
s=s.replace(anchor,inject+anchor)
p.write_text(s,encoding="utf-8")
print("Patched script to tolerate Unicode transport strings.")
