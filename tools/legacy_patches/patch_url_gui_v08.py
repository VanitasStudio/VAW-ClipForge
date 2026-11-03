"""Add Video URL mode and Full HD output selection to ClipForge v0.8 GUI."""
from pathlib import Path

p=Path(__file__).resolve().parent/"clipforge_gui.py"
s=p.read_text(encoding="utf-8")

def replace_once(before,after):
    global s
    if before not in s:
        raise RuntimeError("Cannot find GUI patch anchor: "+before[:100])
    s=s.replace(before,after,1)

replace_once('from smart_reframe import export_v04',
'''from smart_reframe import export_v04
from url_source import (validate_url,check_link,fetch_video,clear_cache,cache_stats)''')

replace_once('''        self.root.title("VAW ClipForge v0.7 | Universal Object Tracking")''',
'''        self.root.title("VAW ClipForge v0.8 | URL Import + 1080p Shorts")''')

replace_once('''        self.root.geometry("900x885")
        self.root.minsize(805,780)''',
'''        self.root.geometry("940x970")
        self.root.minsize(860,870)''')

replace_once('''        self.src=tk.StringVar(value=str(default_source) if default_source.exists() else "")''',
'''        self.src=tk.StringVar(value=str(default_source) if default_source.exists() else "")
        self.local_path=tk.StringVar(value=self.src.get())
        self.video_url=tk.StringVar(value="")
        self.source_type=tk.StringVar(value="Local File")
        self.resolution=tk.StringVar(value="1080p")''')

replace_once('''        self.label(frame,"SOURCE VIDEO",10,"muted",True).pack(anchor="w")
        r=tk.Frame(frame,bg=C["bg"]);r.pack(fill="x",pady=(6,12))
        self.entry(r,self.src).pack(side="left",fill="x",expand=True,ipady=9)
        self.button(r,"Browse",self.browse).pack(side="left",padx=(8,0))
''',
'''        sourcebar=tk.Frame(frame,bg=C["bg"])
        sourcebar.pack(fill="x",pady=(0,4))
        self.label(sourcebar,"SOURCE INPUT",10,"muted",True).pack(side="left")
        self.source_switch=ttk.Combobox(
            sourcebar,textvariable=self.source_type,state="readonly",
            values=["Local File","Video URL"],width=15)
        self.source_switch.pack(side="left",padx=(14,10))
        self.source_switch.bind("<<ComboboxSelected>>",self.switch_source)
        self.button(sourcebar,"Check Link",self.check_url).pack(side="left",padx=(0,8))
        self.button(sourcebar,"Clear URL Cache",self.clear_url_cache).pack(side="left")
        r=tk.Frame(frame,bg=C["bg"]);r.pack(fill="x",pady=(6,12))
        self.source_entry=self.entry(r,self.src)
        self.source_entry.pack(side="left",fill="x",expand=True,ipady=9)
        self.browse_source=self.button(r,"Browse",self.browse)
        self.browse_source.pack(side="left",padx=(8,0))
''')

replace_once('''        spin("SECONDS",self.seconds,5,180)
        box=tk.Frame(r,bg=C["bg"]);box.pack(side="left")''',
'''        spin("SECONDS",self.seconds,5,180)
        box=tk.Frame(r,bg=C["bg"]);box.pack(side="left",padx=(0,22))
        self.label(box,"OUTPUT QUALITY",10,"muted",True).pack(anchor="w")
        ttk.Combobox(box,textvariable=self.resolution,state="readonly",
                     values=["1080p","720p"],width=11).pack(pady=(7,0))
        box=tk.Frame(r,bg=C["bg"]);box.pack(side="left")''')

replace_once('''        self.log("No video is published automatically.")''',
'''        self.log("1080p mode exports vertical 1080x1920 MP4. Low-res sources remain low-detail.")
        self.log("URL Mode automatically downloads one authorized public video into local cache.")
        self.log("No video is published automatically.")''')

replace_once('''    def browse(self):
        f=filedialog.askopenfilename(filetypes=[("Videos","*.mp4 *.mkv *.mov *.webm *.avi *.m4v")])
        if f:self.src.set(f)
''',
'''    def switch_source(self,_=None):
        mode=self.source_type.get()
        if mode=="Video URL":
            self.local_path.set(self.src.get())
            self.src.set(self.video_url.get())
            self.browse_source.configure(text="Paste Link",command=self.paste_url)
            self.source_entry.configure(fg=C["white"])
            self.log("Video URL Mode enabled. Supports public YouTube, TikTok and Vimeo links.")
        else:
            self.video_url.set(self.src.get())
            self.src.set(self.local_path.get())
            self.browse_source.configure(text="Browse",command=self.browse)
            self.log("Local File Mode enabled.")

    def paste_url(self):
        try:
            value=self.root.clipboard_get().strip()
            self.src.set(validate_url(value))
        except tk.TclError:
            messagebox.showinfo("Clipboard empty","Copy a public YouTube, TikTok or Vimeo URL first.")
        except ValueError as exc:
            messagebox.showwarning("Invalid URL",str(exc))

    def browse(self):
        if self.source_type.get()=="Video URL":
            return self.paste_url()
        f=filedialog.askopenfilename(filetypes=[("Videos","*.mp4 *.mkv *.mov *.webm *.avi *.m4v")])
        if f:
            self.src.set(f)
            self.local_path.set(f)

    def check_url(self):
        value=self.src.get().strip()
        try:
            validated=validate_url(value)
        except ValueError as exc:
            messagebox.showwarning("Video URL needed",str(exc))
            return
        self.log("Checking video link (no download)...")
        def work():
            try:
                item=check_link(validated,log=lambda m:self.messages.put(("log",m)))
                duration=item.get("duration")
                label=(f"{item['title']} | {int(duration)}s" if duration else item["title"])
                label+= " | cached" if item.get("cached") else " | accessible"
                self.messages.put(("link_ok",label))
            except Exception as exc:
                self.messages.put(("link_error",str(exc)[:250]))
        threading.Thread(target=work,daemon=True).start()

    def clear_url_cache(self):
        videos,bytes_used=cache_stats()
        if not videos:
            messagebox.showinfo("URL cache","There are no cached downloads.")
            return
        if messagebox.askyesno("Clear URL cache?",
            f"Delete {videos} downloaded source(s), ~{bytes_used/(1024**2):.0f} MiB?\\n"
            "Existing exported clips are not deleted."):
            try:
                clear_cache()
                self.log("Downloaded URL source cache cleared; exports preserved.")
            except Exception as exc:
                messagebox.showerror("Cache cleanup failed",str(exc))
''')

a=s.index("    def start(self):")
b=s.index("    def poll(self):",a)
new_start='''    def start(self):
        if self.busy:return
        raw=self.src.get().strip()
        from_url=(self.source_type.get()=="Video URL" or raw.startswith("https://"))
        if from_url:
            try:
                raw=validate_url(raw)
            except ValueError as exc:
                messagebox.showerror("Invalid source URL",str(exc))
                return
            if not messagebox.askyesno(
                "Use video URL?",
                "ClipForge will download one PUBLIC video to a local reusable cache.\\n"
                "Only proceed with content you own or have permission to reuse.\\n"
                "Private/DRM/restricted videos are not bypassed. Continue?"):
                return
            source=None
        else:
            source=Path(raw)
            if not source.is_file():
                messagebox.showerror("Select video","Choose a local video or switch to Video URL.")
                return
        try:
            count,seconds=int(self.count.get()),int(self.seconds.get())
        except (ValueError,tk.TclError):
            messagebox.showerror("Invalid settings","Clip count/duration must be numbers.")
            return
        resolution=self.resolution.get()
        if resolution not in ("720p","1080p"):
            messagebox.showerror("Invalid output quality","Select 720p or 1080p.")
            return
        ai=self.mode.get().startswith("Gemini")
        if ai and not has_key():
            messagebox.showwarning("API key needed","Click Set Gemini Key first.")
            return
        if ai and not messagebox.askyesno(
            "Send video excerpts to Google Gemini?",
            "This sends compressed audio and (if enabled) sampled frames to Google AI.\\n"
            "Up to 6 sections; failed calls may retry. API quota/cost may apply.\\n"
            "Continue?"):
            return
        dest_base=Path(self.dest.get().strip()).expanduser().resolve()
        style=self.layout.get()
        model=self.model.get().strip()
        captions=self.caption.get()
        burn=self.burn.get()
        visual=self.visual.get()
        subject_mode=self.subject_mode.get()
        auto=self.autoframe.get()
        scene=self.scenedetect.get()
        cap_style=self.caption_style.get()
        self.busy=True
        self.run_btn.configure(state="disabled")
        self.log("Starting "+("URL import -> " if from_url else "local file -> ")
                 +("Gemini analysis" if ai else "offline audio analysis")
                 +f" -> {resolution} vertical.")
        def work():
            try:
                if from_url:
                    item=fetch_video(raw,log=lambda m:self.messages.put(("log",m)))
                    current=Path(item["path"])
                    folder_name=item["source_name"]
                    self.messages.put(("log",f"Video: {item['title'][:80]}"))
                    self.messages.put(("log","Source resolution: "+str(item.get("resolution") or "unknown")))
                else:
                    current=source
                    folder_name=current.stem
                dest=dest_base/folder_name
                self.messages.put(("set_export",str(dest)))
                if ai:
                    selection=process_ai(current,dest,count,seconds,style,model,
                        log=lambda x:self.messages.put(("log",x)),
                        visual=visual,render=False)
                else:
                    selection=process_local(current,dest,count,seconds,style,
                        log=lambda x:self.messages.put(("log",x)),dry_run=True)
                self.messages.put(("log","Selecting scene-aware crops and styling captions..."))
                outcome=export_v04(current,dest,selection["clips"],
                    auto=auto,scenes=scene,captions=captions,
                    burn=burn,style=cap_style,layout=style,
                    subject_mode=subject_mode,resolution=resolution,
                    log=lambda x:self.messages.put(("log",x)))
                completed=sum(bool(x.get("ok")) for x in outcome["clips"])
                if not completed:
                    raise RuntimeError("No clips exported. Check activity log.")
                self.messages.put(("done",
                    f"{resolution} export complete: {completed}/{len(outcome['clips'])} clips\\n{dest}"))
            except Exception as exc:
                self.messages.put(("error",str(exc)[:900]))
        threading.Thread(target=work,daemon=True).start()

'''
s=s[:a]+new_start+s[b:]

replace_once('''                elif kind=="api_error":
                    self.log(msg)
                    messagebox.showerror("API test failed",msg)
                else:''',
'''                elif kind=="api_error":
                    self.log(msg)
                    messagebox.showerror("API test failed",msg)
                elif kind=="link_ok":
                    self.log("Link OK: "+msg)
                    messagebox.showinfo("Video link",msg)
                elif kind=="link_error":
                    self.log("Link check failed: "+msg)
                    messagebox.showwarning("URL check failed",msg)
                elif kind=="set_export":
                    self.last_export=Path(msg)
                else:''')

p.write_text(s,encoding="utf-8")
print("ClipForge GUI v0.8: direct Video URL mode + 1080p output + cache")
