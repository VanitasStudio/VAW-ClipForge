"""Patch existing ClipForge review editor to v0.6.
Adds audible preview, subtitle preset gallery, manual subject lock and cut transitions.
"""
from pathlib import Path
p=Path(__file__).with_name("review_editor.py")
s=p.read_text(encoding="utf-8")
def must(old,new,label):
    global s
    if old not in s:
        if label in ("play button", "audio transport", "style help", "audio load"):
            print("Compatibility note: replacing",label,"separately.")
            return
        raise ValueError("Missing "+label)
    s=s.replace(old,new,1)

must('from review_core import load_clip, focus_x, focus_center, crop_width, export_review, save_draft',
'''from review_core import load_clip, focus_x, focus_center, crop_width, export_review, save_draft
from subtitle_presets import PRESETS, choose, preview_image
from audio_preview import AudioPreview
from subject_tracking import track_subject''',"imports")
must('VAW ClipForge v0.5 | Review & Timeline Editor','VAW ClipForge v0.6 | Creative Review Studio',"title")
must('self.app.geometry("1320x870")','self.app.geometry("1360x940")',"size")
must('self.app.minsize(1120,760)','self.app.minsize(1120,800') if False else None
# actual minsize update
s=s.replace('self.app.minsize(1120,760)','self.app.minsize(1180,820)')
must('''        self.style=tk.StringVar(value="modern")''','''        self.style=tk.StringVar(value="karaoke")
        self.audio=AudioPreview()
        self.selecting_subject=False
        self.subject_x=0.5
        self.subject_y=0.5
        self.gallery_images=[]
        self.app.protocol("WM_DELETE_WINDOW",self.on_close)''',"state")
must('''        self.btn(info,"Pin Focus Keyframe",self.pin_focus,True).pack(anchor="w",pady=(4,0))''',
'''        trackbuttons=tk.Frame(info,bg=COLORS["bg"])
        trackbuttons.pack(anchor="w",pady=(4,0))
        self.btn(trackbuttons,"Pin Keyframe",self.pin_focus,True).pack(side="left")
        self.subject_btn=self.btn(trackbuttons,"Lock Subject",self.arm_subject)
        self.subject_btn.pack(side="left",padx=6)
        self.btn(trackbuttons,"Clear Tracks",self.clear_tracks).pack(side="left")''',"subject controls")
must('''        self.play_btn=self.btn(controls,"Ã¢â€“Â¶ Silent Preview",self.toggle_play)''',
'''        self.play_btn=self.btn(controls,"Ã¢â€“Â¶ Play with Audio",self.toggle_play)''',"play button")
must('''        self.label(controls,"Frames only; open final MP4 for audio.",9,"sub").pack(side="right")''',
'''        self.label(controls,"Audio clock sync Ã¢â‚¬Â¢ draft preview",9,"sub").pack(side="right")''',"audio hint")
must('''        self.label(left,"Timeline:  scene cuts   |   caption starts   |   manual keyframes",
                   9,"sub").pack(anchor="w",pady=(5,0))''',
'''        scenecontrols=tk.Frame(left,bg=COLORS["bg"])
        scenecontrols.pack(fill="x",pady=(4,0))
        self.label(scenecontrols,"SCENE CUTS / TRANSITIONS",9,"sub",bold=True).pack(side="left")
        self.btn(scenecontrols,"Edit transitions",self.open_scene_editor).pack(side="left",padx=12)
        self.label(left,"Blue: scene  Ã¢â‚¬Â¢  Pink: caption  Ã¢â‚¬Â¢  Yellow: focus pin  Ã¢â‚¬Â¢  Purple: soft dip",
                   9,"sub").pack(anchor="w",pady=(5,0))''',"scene panel")
must('''        ttk.Combobox(stylerow,textvariable=self.style,state="readonly",
                     values=("modern","clean"),width=12).pack(side="left")''',
'''        self.style_picker=ttk.Combobox(stylerow,textvariable=self.style,state="readonly",
                     values=tuple(p.id for p in PRESETS),width=13)
        self.style_picker.pack(side="left")
        self.style_picker.bind("<<ComboboxSelected>>",lambda e:self.update_frame())
        self.btn(stylerow,"Browse Styles",self.open_style_gallery).pack(side="left",padx=8)''',"style picker")
must('''        self.label(right,"Modern = highlighted active word; edited text uses\n"
                         "estimated word timing. Review every result before posting.",
                   9,"sub",justify="left").pack(anchor="w")''',
'''        self.label(right,"Six selectable presets. Subtitle edits use estimated word timing;\\n"
                         "review every caption before publishing.",
                   9,"sub",justify="left").pack(anchor="w")''',"style help")
must('''            self.playing=False;self.play_btn.configure(text="Ã¢â€“Â¶ Silent Preview")
            self.pending_focus=None''',
'''            self.audio.load(data["source"],data["source_start"],data["duration"])
            self.playing=False;self.play_btn.configure(text="Ã¢â€“Â¶ Play with Audio")
            self.pending_focus=None''',"audio load")
must('''        if msg:
            self.paint_caption(cropped,msg,t)''',
'''        if msg:
            self.paint_caption(cropped,msg,t)''',"canvas caption") # noop
must('''    def scrub(self,_=None):
        if self.in_scrub:return
        self.pending_focus=None
        self.update_frame()

    def toggle_play(self):
        if not self.data:return
        self.playing=not self.playing
        self.play_btn.configure(text="Ã¢ÂÂ¸ Pause" if self.playing else "Ã¢â€“Â¶ Silent Preview")
        if self.playing:self.tick()
    def tick(self):
        if not self.playing or not self.data:return
        target=self.position.get()+0.25
        if target>=self.data["duration"]:
            self.playing=False;self.play_btn.configure(text="Ã¢â€“Â¶ Silent Preview")
            return
        self.position.set(round(target,2));self.scrub()
        self.app.after(250,self.tick)
''',
'''    def scrub(self,_=None):
        if self.in_scrub:return
        if self.playing:
            self.audio.stop()
            self.playing=False
            self.play_btn.configure(text="Ã¢â€“Â¶ Play with Audio")
        self.pending_focus=None
        self.update_frame()

    def toggle_play(self):
        if not self.data:return
        if self.playing:
            self.audio.stop()
            self.playing=False
            self.play_btn.configure(text="Ã¢â€“Â¶ Play with Audio")
            return
        try:
            self.audio.play(self.position.get())
            self.playing=True
            self.play_btn.configure(text="Ã¢ÂÂ¸ Pause")
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
            self.play_btn.configure(text="Ã¢â€“Â¶ Play with Audio")
            return
        self.in_scrub=True
        self.position.set(round(target,2))
        self.in_scrub=False
        self.pending_focus=None
        self.update_frame()
        self.app.after(110,self.tick)
''',"audio transport")
must('''    def click_focus(self,event):
        if not self.data:return
        value=max(0,min(100,event.x/450*100))
        self.focus.set(value)
        self.pending_focus=value/100
        self.update_frame()
''',
'''    def click_focus(self,event):
        if not self.data:return
        value=max(0,min(100,event.x/450*100))
        if self.selecting_subject:
            self.selecting_subject=False
            self.subject_btn.configure(text="Lock Subject")
            self.track_clicked(value/100,max(0,min(1,event.y/255)))
            return
        self.focus.set(value)
        self.pending_focus=value/100
        self.update_frame()
''',"subject click")
# Add subject, gallery, transitions methods immediately before save method.
newmethods='''    def on_close(self):
        self.playing=False
        self.audio.close()
        if self.capture:self.capture.release()
        self.app.destroy()

    def arm_subject(self):
        if not self.data or self.busy:return
        self.selecting_subject=not self.selecting_subject
        self.subject_btn.configure(text="Click Subject NOW" if self.selecting_subject else "Lock Subject")
        self.status.set("Click the face/object in SOURCE FRAME to track up to 4 seconds.")

    def track_clicked(self,x,y):
        self.busy=True
        at=float(self.position.get())
        self.status.set("Analyzing subject motion near "+self.sec_label(at)+"...")
        data=copy.deepcopy(self.data)
        def worker():
            try:
                track=track_subject(data["source"],data["source_start"],at,
                    data["duration"],x,y,data.get("cuts",[]),seconds=4)
                self.messages.put(("subject",track))
            except Exception as exc:
                self.messages.put(("subject_error",str(exc)))
        threading.Thread(target=worker,daemon=True).start()

    def clear_tracks(self):
        if not self.data:return
        count=len(self.data.get("subject_tracks",[]))
        if count and messagebox.askyesno("Clear subject tracking","Clear all "+str(count)+" subject track(s)?"):
            self.data["subject_tracks"]=[]
            self.update_frame()
            self.status.set("Removed subject tracking pins from editor; original untouched.")

    def open_scene_editor(self):
        if not self.data:return
        dialog=tk.Toplevel(self.app)
        dialog.title("Scene Transitions")
        dialog.geometry("480x450")
        dialog.configure(bg=COLORS["bg"])
        self.label(dialog,"SCENE TRANSITIONS",16,bold=True).pack(anchor="w",padx=20,pady=(18,4))
        self.label(dialog,"Choose a transition for each detected scene boundary.",10,"sub").pack(anchor="w",padx=20,pady=(0,12))
        container=tk.Frame(dialog,bg=COLORS["bg"])
        container.pack(fill="both",expand=True,padx=20)
        vars=[]
        for cut in self.data.get("cuts",[]):
            key=f"{float(cut):.2f}"
            row=tk.Frame(container,bg=COLORS["bg"])
            row.pack(fill="x",pady=5)
            self.label(row,f"Scene at {float(cut):.2f}s",11).pack(side="left")
            variable=tk.StringVar(value=self.data["transitions"].get(key,"hard"))
            ttk.Combobox(row,textvariable=variable,state="readonly",
                         values=("hard","dip"),width=14).pack(side="right")
            vars.append((key,variable))
        if not vars:self.label(container,"No cuts detected.",11,"sub").pack()
        def save():
            for key,var in vars:
                self.data["transitions"][key]=var.get()
            self.draw_timeline()
            self.status.set(f"Saved {sum(v.get()=='dip' for _,v in vars)} soft dip transition(s).")
            dialog.destroy()
        self.btn(dialog,"Apply Transitions",save,True).pack(pady=14)
        self.label(dialog,"Hard = instant cut. Dip = brief brightness fade at cut.\\n"
                         "Audio remains continuous. Preview rendered MP4 for timing.",
                   9,"sub",justify="left").pack(pady=(0,10))

    def open_style_gallery(self):
        dialog=tk.Toplevel(self.app)
        dialog.title("Subtitle Modes | ClipForge v0.6")
        dialog.geometry("810x610")
        dialog.configure(bg=COLORS["bg"])
        self.label(dialog,"CHOOSE A SUBTITLE MODE",18,bold=True).pack(anchor="w",padx=18,pady=(16,4))
        self.label(dialog,"Visual presets for 9:16 Shorts Ã¢â‚¬Â¢ click a card to apply",10,"sub").pack(anchor="w",padx=18,pady=(0,14))
        gallery=tk.Frame(dialog,bg=COLORS["bg"])
        gallery.pack(fill="both",expand=True,padx=12)
        photos=[]
        for i,preset in enumerate(PRESETS):
            card=tk.Frame(gallery,bg=COLORS["panel"],padx=7,pady=7)
            card.grid(row=i//3,column=i%3,padx=6,pady=8,sticky="n")
            photo=ImageTk.PhotoImage(preview_image(preset.id,240,150,selected=self.style.get()==preset.id))
            photos.append(photo)
            button=tk.Button(card,image=photo,borderwidth=0,relief="flat",
                             bg=COLORS["panel"],activebackground=COLORS["panel"],
                             cursor="hand2")
            button.pack()
            self.label(card,preset.name,11,bold=True).pack(anchor="w",pady=(6,0))
            self.label(card,preset.sub,9,"sub").pack(anchor="w")
            def choose_style(style=preset.id):
                self.style.set(style)
                self.update_frame()
                self.status.set("Subtitle preset: "+choose(style).name)
                dialog.destroy()
            button.configure(command=choose_style)
        dialog._photos=photos
        self.label(dialog,"Rendered captions use a safe bottom region (720Ãƒâ€”1280).",
                   10,"sub").pack(anchor="w",padx=20,pady=(4,14))

'''
anchor="    def save(self):"
if anchor not in s:raise ValueError("Methods insertion anchor missing")
s=s.replace(anchor,newmethods+anchor,1)
# Show new cut setting colors.
s=s.replace('''                can.create_line(x,9,x,61,fill=COLORS["blue"],width=2)''',
'''                mode=self.data.get("transitions",{}).get(f"{float(t):.2f}","hard")
                can.create_line(x,9,x,61,fill="#ad70f1" if mode=="dip" else COLORS["blue"],width=2)''')
# GUI queue subject returns, not a full export.
s=s.replace('''                if kind=="log":self.status.set(val)
                else:''',
'''                if kind=="log":self.status.set(val)
                elif kind=="subject":
                    self.busy=False
                    self.data.setdefault("subject_tracks",[]).append(val)
                    self.update_frame()
                    self.status.set(f"Subject tracked for {val['end']-val['start']:.1f}s. Save draft or export.")
                elif kind=="subject_error":
                    self.busy=False
                    self.status.set("Subject tracking failed: "+val[:110])
                    messagebox.showwarning("Subject tracking",val)
                else:''')
# Unicode-safe audio transport patch, independent of the v0.5 play icon.
import re
s=re.sub(r'self\.play_btn=self\.btn\(controls,"[^"]*Silent Preview",self\.toggle_play\)',
         'self.play_btn=self.btn(controls,"Play with Audio",self.toggle_play)',s)
s=re.sub(r'self\.playing=False;self\.play_btn\.configure\(text="[^"]*Silent Preview"\)',
         'self.audio.load(data["source"],data["source_start"],data["duration"])\n            self.playing=False;self.play_btn.configure(text="Play with Audio")',s)
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
p.write_text(s,encoding="utf-8")
print("v0.6 UI patched: audio, subject lock, scene transitions, subtitle gallery")
