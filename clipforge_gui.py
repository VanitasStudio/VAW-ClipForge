"""VAW ClipForge v1.0 — AI Editorial Intelligence desktop application."""
from __future__ import annotations
import os
import sys
import subprocess
from silent_process import run as silent_run, popen as silent_popen
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from clip_engine import process as process_local
from gemini_highlights import process_ai, MODEL
from secure_config import save_key, has_key, delete_key
from test_gemini import test_gemini_connection
from smart_reframe import export_v04
from url_source import (validate_url,check_link,fetch_video,clear_cache,cache_stats)
from subtitle_presets import PRESETS, preview_image
from PIL import ImageTk

ROOT=Path(__file__).resolve().parent
C={"bg":"#10141e","card":"#1b2230","white":"#f3f5fb",
   "muted":"#a9b4c6","red":"#d63b50","line":"#465067","green":"#84ddb1"}

class ClipForge:
    def __init__(self):
        self.root=tk.Tk()
        self.root.title("VAW ClipForge v1.1 | AI Editorial Studio")
        self.root.geometry("1080x920")
        self.root.minsize(960,760)
        self.root.configure(bg=C["bg"])
        default_source=Path.home()/"Downloads"/"videoplayback.mp4"
        self.src=tk.StringVar(value=str(default_source) if default_source.exists() else "")
        self.local_path=tk.StringVar(value=self.src.get())
        self.video_url=tk.StringVar(value="")
        self.source_type=tk.StringVar(value="Local File")
        self.resolution=tk.StringVar(value="1080p")
        self.dest=tk.StringVar(value=str(ROOT/"exports"))
        self.count=tk.IntVar(value=3)
        self.seconds=tk.IntVar(value=30)
        self.context_duration=tk.BooleanVar(value=True)
        self.layout=tk.StringVar(value="blur")
        self.mode=tk.StringVar(value="Gemini AI (audio)")
        self.model=tk.StringVar(value="gemini-3.5-flash-lite")
        self.caption=tk.BooleanVar(value=True)
        self.burn=tk.BooleanVar(value=True)
        self.visual=tk.BooleanVar(value=True)
        self.autoframe=tk.BooleanVar(value=True)
        self.subject_mode=tk.StringVar(value="universal")
        self.scenedetect=tk.BooleanVar(value=True)
        self.caption_style=tk.StringVar(value="karaoke")
        self.caption_label=tk.StringVar(value="Karaoke")
        self.busy=False
        self.last_export=None
        self.messages=queue.Queue()
        self.create_ui()
        self.root.after(200,self.poll)

    def label(self,parent,text,size=10,color="white",bold=False):
        font=("Segoe UI Semibold" if bold else "Segoe UI",size)
        return tk.Label(parent,text=text,bg=C["bg"],fg=C.get(color,color),
                        font=font,anchor="w",justify="left")
    def button(self,parent,text,fn,primary=False):
        normal=C["red"] if primary else "#273247"
        hover="#ec5267" if primary else "#35445e"
        widget=tk.Button(parent,text=text,command=fn,relief="flat",bd=0,
                         cursor="hand2",padx=15,pady=9,
                         bg=normal,fg=C["white"],
                         activebackground=hover,activeforeground=C["white"],
                         font=("Segoe UI Semibold",10),highlightthickness=0)
        widget.bind("<Enter>",lambda _e:widget.configure(bg=hover))
        widget.bind("<Leave>",lambda _e:widget.configure(bg=normal))
        return widget
    def entry(self,parent,var):
        widget=tk.Entry(parent,textvariable=var,font=("Segoe UI",10),
                        bg="#202a3b",fg=C["white"],insertbackground="white",
                        relief="flat",highlightthickness=1,
                        highlightbackground=C["line"],highlightcolor="#7187ad",
                        bd=0)
        return widget
    def create_ui(self):
        # Refined desktop layout: clear sections, readable spacing and a fixed action area.
        style=ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TCombobox",fieldbackground="#202a3b",background="#273247",
                        foreground=C["white"],arrowcolor=C["white"],borderwidth=0,
                        padding=(9,7),selectbackground="#273247",
                        selectforeground=C["white"])
        style.map("TCombobox",
                  fieldbackground=[("readonly","#202a3b"),("focus","#26344a")],
                  foreground=[("readonly",C["white"])],
                  selectbackground=[("readonly","#273247")])
        style.configure("Vertical.TScrollbar",background="#273247",
                        troughcolor=C["bg"],bordercolor=C["bg"],arrowcolor=C["muted"])

        shell=tk.Frame(self.root,bg=C["bg"])
        shell.pack(fill="both",expand=True,padx=22,pady=14)

        header=tk.Frame(shell,bg=C["bg"])
        header.pack(fill="x",pady=(0,12))
        tk.Label(header,text="VAW / CLIPFORGE",bg=C["bg"],fg=C["white"],
                 font=("Segoe UI Semibold",23)).pack(side="left")
        tk.Label(header,text="AI EDITORIAL STUDIO",bg="#263247",fg="#c7d4e8",
                 font=("Segoe UI Semibold",9),padx=11,pady=6).pack(side="right",anchor="center")
        tk.Label(shell,text="Turn long-form videos into story-led vertical clips.",
                 bg=C["bg"],fg=C["muted"],font=("Segoe UI",10)).pack(anchor="w",pady=(0,10))

        # Scrollable settings; the primary action and activity log stay visible.
        scroll_area=tk.Frame(shell,bg=C["bg"])
        scroll_area.pack(fill="both",expand=True)
        canvas=tk.Canvas(scroll_area,bg=C["bg"],highlightthickness=0,bd=0)
        scrollbar=ttk.Scrollbar(scroll_area,orient="vertical",command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right",fill="y")
        canvas.pack(side="left",fill="both",expand=True)
        content=tk.Frame(canvas,bg=C["bg"])
        window=canvas.create_window((0,0),window=content,anchor="nw")
        content.bind("<Configure>",lambda _e:canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",lambda e:canvas.itemconfigure(window,width=e.width))
        canvas.bind_all("<MouseWheel>",lambda e:canvas.yview_scroll(int(-e.delta/120),"units"))

        def label(parent,text,size=10,color="white",bold=False):
            return tk.Label(parent,text=text,bg=parent.cget("bg"),
                            fg=C.get(color,color),
                            font=("Segoe UI Semibold" if bold else "Segoe UI",size),
                            anchor="w",justify="left")
        def section(title,subtitle):
            card=tk.Frame(content,bg=C["card"],highlightbackground=C["line"],
                          highlightthickness=1,bd=0)
            card.pack(fill="x",pady=(0,11))
            head=tk.Frame(card,bg=C["card"])
            head.pack(fill="x",padx=17,pady=(12,2))
            label(head,title,11,"white",True).pack(anchor="w")
            if subtitle:
                label(head,subtitle,9,"muted").pack(anchor="w",pady=(2,7))
            body=tk.Frame(card,bg=C["card"])
            body.pack(fill="x",padx=17,pady=(2,14))
            return body

        # 01 — Source and destination.
        source=section("01  SOURCE VIDEO","Choose a local file or paste a public video URL.")
        sourcebar=tk.Frame(source,bg=C["card"])
        sourcebar.pack(fill="x",pady=(0,8))
        label(sourcebar,"INPUT TYPE",9,"muted",True).pack(side="left",padx=(0,10))
        self.source_switch=ttk.Combobox(sourcebar,textvariable=self.source_type,
            state="readonly",values=["Local File","Video URL"],width=16)
        self.source_switch.pack(side="left")
        self.source_switch.bind("<<ComboboxSelected>>",self.switch_source)
        self.button(sourcebar,"Check Link",self.check_url).pack(side="left",padx=(9,6))
        self.button(sourcebar,"Clear URL Cache",self.clear_url_cache).pack(side="left")
        inputrow=tk.Frame(source,bg=C["card"])
        inputrow.pack(fill="x",pady=(0,9))
        self.source_entry=self.entry(inputrow,self.src)
        self.source_entry.pack(side="left",fill="x",expand=True,ipady=9)
        self.browse_source=self.button(inputrow,"Browse",self.browse)
        self.browse_source.pack(side="left",padx=(9,0))
        label(source,"EXPORT LOCATION",9,"muted",True).pack(anchor="w",pady=(2,5))
        destrow=tk.Frame(source,bg=C["card"])
        destrow.pack(fill="x")
        self.entry(destrow,self.dest).pack(side="left",fill="x",expand=True,ipady=8)
        self.button(destrow,"Choose Folder",self.browse_out).pack(side="left",padx=(9,0))

        # 02 — Output settings.
        output=section("02  CLIP SETTINGS","Duration is a soft target. Complete story boundaries take priority.")
        for col in range(4):
            output.grid_columnconfigure(col,weight=1)
        settings=[
            ("CLIP COUNT",self.count,"spin",1,20),
            ("TARGET DURATION",self.seconds,"spin",5,180),
            ("OUTPUT QUALITY",self.resolution,"combo",["1080p","720p"]),
            ("VERTICAL LAYOUT",self.layout,"combo",["blur","fit","crop"]),
        ]
        for col,(title,var,kind,*opts) in enumerate(settings):
            box=tk.Frame(output,bg=C["card"])
            box.grid(row=0,column=col,sticky="ew",padx=(0 if col==0 else 12,8))
            label(box,title,9,"muted",True).pack(anchor="w",pady=(0,7))
            if kind=="spin":
                widget=tk.Spinbox(box,from_=opts[0],to=opts[1],width=9,
                    textvariable=var,bg="#202a3b",fg=C["white"],
                    insertbackground="white",buttonbackground="#354158",
                    relief="flat",bd=0,font=("Segoe UI",11),
                    highlightthickness=1,highlightbackground=C["line"])
            else:
                widget=ttk.Combobox(box,textvariable=var,state="readonly",
                                    values=opts[0],width=11)
            widget.pack(anchor="w",fill="x",ipady=3)

        # 03 — AI engine.
        ai=section("03  AI HIGHLIGHT ENGINE","Gemini finds complete stories; offline audio mode is available as a fallback.")
        ai.grid_columnconfigure(1,weight=1)
        label(ai,"DETECTION MODE",9,"muted",True).grid(row=0,column=0,sticky="w",pady=(0,6))
        label(ai,"GEMINI MODEL",9,"muted",True).grid(row=0,column=1,sticky="w",padx=(15,0),pady=(0,6))
        ttk.Combobox(ai,textvariable=self.mode,state="readonly",width=27,
            values=["Gemini AI (audio)","Audio Activity (offline)"]).grid(
                row=1,column=0,sticky="ew",padx=(0,10))
        self.model_combo=ttk.Combobox(ai,textvariable=self.model,state="normal",
            values=["gemini-3.6-flash","gemini-3.5-flash-lite",
                    "gemini-3.8-flash","gemini-3.7-flash",
                    "gemini-3.1-flash-lite","gemini-2.5-flash"])
        self.model_combo.grid(row=1,column=1,sticky="ew",padx=(5,0))
        keyrow=tk.Frame(ai,bg=C["card"])
        keyrow.grid(row=2,column=0,columnspan=2,sticky="ew",pady=(11,0))
        self.key_status=tk.Label(keyrow,text="",bg=C["card"],fg=C["muted"],
                                 font=("Segoe UI",9),anchor="w")
        self.key_status.pack(side="left",fill="x",expand=True)
        self.button(keyrow,"Set API Key",self.set_key).pack(side="right",padx=(7,0))
        self.button(keyrow,"Remove Key",self.remove_key).pack(side="right",padx=(7,0))
        self.button(keyrow,"Test Connection",self.test_api).pack(side="right")
        self.refresh_key_status()

        # 04 — Intelligent processing.
        smart=section("04  SMART PROCESSING","Choose which local analysis and enhancement stages run during export.")
        smart.grid_columnconfigure(0,weight=1)
        smart.grid_columnconfigure(1,weight=1)
        checks=[
            (self.visual,"AI visual analysis (sample frames)",0,0),
            (self.caption,"Automatic subtitles (local Whisper)",0,1),
            (self.burn,"Burn subtitles into exported clips",1,0),
            (self.context_duration,"Context-aware duration (local Whisper)",1,1),
            (self.autoframe,"Auto-reframe universal subjects",2,0),
            (self.scenedetect,"Intelligent scene detection",2,1),
        ]
        for var,text,row,col in checks:
            tk.Checkbutton(smart,text=text,variable=var,anchor="w",
                bg=C["card"],fg=C["white"],selectcolor="#354158",
                activebackground=C["card"],activeforeground=C["white"],
                font=("Segoe UI",9),padx=2,pady=5,
                highlightthickness=0).grid(row=row,column=col,sticky="w",padx=(0,12))
        focus=tk.Frame(smart,bg=C["card"])
        focus.grid(row=3,column=0,columnspan=2,sticky="ew",pady=(8,0))
        label(focus,"AUTO FOCUS",9,"muted",True).pack(side="left",padx=(0,12))
        ttk.Combobox(focus,textvariable=self.subject_mode,state="readonly",
            values=["universal","people","motion","center"],width=16).pack(side="left")
        label(focus,"Universal works with animation, icons, diagrams and objects.",
              9,"muted").pack(side="left",padx=12)

        # 05 — Captions.
        captions=section("05  SUBTITLE STYLE","Select a visual preset. All Capital forces every spoken word into uppercase.")
        caprow=tk.Frame(captions,bg=C["card"])
        caprow.pack(fill="x")
        label(caprow,"SUBTITLE MODE",9,"muted",True).pack(side="left",padx=(0,12))
        self.caption_picker=ttk.Combobox(caprow,textvariable=self.caption_label,
            state="readonly",values=[p.name for p in PRESETS],width=25)
        self.caption_picker.pack(side="left")
        self.caption_picker.bind("<<ComboboxSelected>>",self.set_caption_from_label)
        self.button(caprow,"Browse Styles",self.show_caption_styles).pack(side="left",padx=(9,0))
        self.caption_hint=label(captions,"Karaoke — word-by-word crimson highlight.",9,"muted")
        self.caption_hint.pack(anchor="w",pady=(9,0))
        label(captions,"Subtitle files (.SRT and .ASS) are saved beside each exported clip.",
              9,"muted").pack(anchor="w",pady=(4,0))
        label(content,"Only process videos you own or have permission to repurpose.",
              9,"muted").pack(anchor="w",pady=(0,10))

        # Fixed action bar and compact activity log.
        footer=tk.Frame(shell,bg=C["bg"])
        footer.pack(fill="x",pady=(9,0))
        actions=tk.Frame(footer,bg=C["bg"])
        actions.pack(fill="x",pady=(0,8))
        self.run_btn=self.button(actions,"GENERATE CLIPS",self.start,True)
        self.run_btn.pack(side="left")
        self.button(actions,"Open Exports",self.open_export).pack(side="left",padx=(9,0))
        self.button(actions,"Review / Timeline",self.open_review).pack(side="left",padx=(8,0))
        self.button(actions,"Editorial Report",self.open_editorial_report).pack(side="left",padx=(8,0))
        logcard=tk.Frame(footer,bg=C["card"],highlightbackground=C["line"],
                         highlightthickness=1,bd=0)
        logcard.pack(fill="x")
        loghead=tk.Frame(logcard,bg=C["card"])
        loghead.pack(fill="x",padx=12,pady=(7,2))
        label(loghead,"ACTIVITY",9,"muted",True).pack(side="left")
        label(loghead,"Processing messages and export status",8,"muted").pack(side="right")
        self.logview=tk.Text(logcard,height=5,bg="#171e2b",fg="#d9e1ef",
            insertbackground="white",font=("Consolas",9),relief="flat",
            wrap="word",padx=11,pady=8,bd=0)
        self.logview.pack(fill="both",expand=True,padx=8,pady=(2,8))
        self.log("Ready. AI ranks story structure, visuals and retention potential.")
        self.log("Context-aware duration keeps complete thoughts together; target duration is not a hard cut.")
        self.log("URL mode downloads one authorized public video into a reusable local cache.")
        self.log("No video is published automatically.")

    def set_caption_from_label(self,_=None):
        selected=self.caption_label.get()
        preset=next((p for p in PRESETS if p.name==selected),None)
        if not preset:
            return
        self.caption_style.set(preset.id)
        if hasattr(self,"caption_hint"):
            self.caption_hint.configure(text=f"{preset.name} — {preset.sub}.")
        self.log("Subtitle mode selected: "+preset.name)

    def show_caption_styles(self):
        dialog=tk.Toplevel(self.root)
        dialog.title("Subtitle Modes | VAW ClipForge")
        dialog.geometry("870x650")
        dialog.configure(bg=C["bg"])
        self.label(dialog,"CHOOSE A SUBTITLE MODE",18,"white",True).pack(
            anchor="w",padx=20,pady=(16,5))
        self.label(dialog,"Click a style to apply it to newly exported clips.",
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
                chosen=next((p for p in PRESETS if p.id==style),None)
                self.caption_style.set(style)
                if chosen:
                    self.caption_label.set(chosen.name)
                    if hasattr(self,"caption_hint"):
                        self.caption_hint.configure(text=f"{chosen.name} — {chosen.sub}.")
                self.log("Subtitle mode selected: "+(chosen.name if chosen else style))
                dialog.destroy()
            tk.Button(frame,image=photo,command=select,borderwidth=0,
                      relief="flat",bg=C["card"],cursor="hand2").pack()
            tk.Label(frame,text=preset.name,bg=C["card"],fg=C["white"],
                     font=("Segoe UI Semibold",11),anchor="w").pack(fill="x",pady=(6,0))
            tk.Label(frame,text=preset.sub,bg=C["card"],fg=C["muted"],
                     font=("Segoe UI",9),anchor="w").pack(fill="x")
        dialog._images=previews

    def refresh_key_status(self):
        self.key_status.configure(text="Gemini key configured" if has_key()
                                  else "Gemini key missing — click Set Gemini Key",
                                  fg=C["green"] if has_key() else C["muted"])
    def switch_source(self,_=None):
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
        if self.busy:
            messagebox.showwarning("Processing in progress","Finish the current clip job before clearing downloaded source files.")
            return
        videos,bytes_used=cache_stats()
        if not videos:
            messagebox.showinfo("URL cache","There are no cached downloads.")
            return
        if messagebox.askyesno("Clear URL cache?",
            f"Delete {videos} downloaded source(s), ~{bytes_used/(1024**2):.0f} MiB?\n"
            "Exported clips stay safe, but Review Studio needs cached sources\n"
            "for re-editing. Reimport the same URL to restore them."):
            try:
                clear_cache()
                self.log("Downloaded URL source cache cleared; exports preserved.")
            except Exception as exc:
                messagebox.showerror("Cache cleanup failed",str(exc))
    def browse_out(self):
        p=filedialog.askdirectory()
        if p:self.dest.set(p)
    def set_key(self):
        key=simpledialog.askstring("Gemini API key","Paste Gemini API key (hidden):",
                                   parent=self.root,show="*")
        if key is None:return
        try:
            save_key(key)
            self.refresh_key_status()
            messagebox.showinfo("Configured","API key encrypted for this Windows account. "
                                "It is not written into project source code.")
        except Exception as exc:
            messagebox.showerror("Key storage error",str(exc))
    def test_api(self):
        if not has_key():
            messagebox.showwarning("Key missing","Set the Gemini API key first.")
            return
        model=self.model.get().strip()
        self.log("Testing Gemini model access (text only)...")
        def work():
            try:
                result=test_gemini_connection(model)
                self.messages.put(("api_ok",result))
            except Exception as exc:
                self.messages.put(("api_error",str(exc)))
        threading.Thread(target=work,daemon=True).start()
    def remove_key(self):
        if messagebox.askyesno("Remove key","Remove saved Gemini API key from this PC?"):
            delete_key()
            self.refresh_key_status()
    def log(self,msg):
        self.logview.insert("end",msg+"\n")
        self.logview.see("end")
    def start(self):
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
                "ClipForge will download one PUBLIC video to a local reusable cache.\n"
                "Only proceed with content you own or have permission to reuse.\n"
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
            "This sends compressed audio and (if enabled) sparse timestamped frames to Google AI for story and visual editorial scoring.\n"
            "Visual analysis describes generic content (animation, objects, diagrams, etc.); it does not identify people.\n"
            "Context-aware duration uses local Whisper on this PC; the transcript is not uploaded.\n"
            "Up to 6 sections; failed calls may retry. API quota/cost may apply.\n"
            "Continue?"):
            return
        dest_base=Path(self.dest.get().strip()).expanduser().resolve()
        style=self.layout.get()
        model=self.model.get().strip()
        captions=self.caption.get()
        burn=self.burn.get()
        visual=self.visual.get()
        context_aware=self.context_duration.get()
        subject_mode=self.subject_mode.get()
        auto=self.autoframe.get()
        scene=self.scenedetect.get()
        cap_style=self.caption_style.get()
        self.busy=True
        self.run_btn.configure(state="disabled")
        self.log("Starting "+("URL import -> " if from_url else "local file -> ")
                 +("Gemini story analysis" if ai else "offline audio analysis")
                 +f" -> {resolution} vertical.")
        if ai and context_aware:
            self.log(f"Context-aware duration ON. {seconds}s is a soft target; natural sentence endings take priority.")
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
                        visual=visual,render=False,
                        context_aware=context_aware,duration_model="base")
                else:
                    if context_aware:
                        self.messages.put(("log","Context-aware sentence alignment requires Gemini AI; offline audio mode keeps the requested fixed duration."))
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
                    f"{resolution} export complete: {completed}/{len(outcome['clips'])} clips\n{dest}"))
            except Exception as exc:
                self.messages.put(("error",str(exc)[:900]))
        threading.Thread(target=work,daemon=True).start()

    def poll(self):
        try:
            while True:
                kind,msg=self.messages.get_nowait()
                if kind=="log":
                    self.log(msg)
                elif kind=="api_ok":
                    self.log(msg)
                    messagebox.showinfo("API ready",msg)
                elif kind=="api_error":
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
                else:
                    self.busy=False;self.run_btn.configure(state="normal")
                    self.log(msg)
                    if kind=="done":messagebox.showinfo("Clips exported",msg)
                    else:messagebox.showerror("ClipForge",msg)
        except queue.Empty:
            pass
        self.root.after(200,self.poll)
    def open_editorial_report(self):
        folder=self.last_export if self.last_export and self.last_export.exists() else Path(self.dest.get())/"videoplayback"
        report=folder/"ai-editorial-report.html"
        if not report.is_file():
            messagebox.showinfo("Editorial Report","No report found yet. Run a Gemini AI clipping job first.")
            return
        try:
            os.startfile(str(report))
            self.log("AI Editorial Report opened in your default browser.")
        except OSError as exc:
            messagebox.showerror("Report open failed",str(exc))

    def open_review(self):
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
            silent_popen(args,cwd=str(ROOT))
            self.log("Review & Timeline editor opened. Correct captions and framing there.")
        except OSError as exc:
            messagebox.showerror("Editor launch failed",str(exc))
    def open_export(self):
        p=self.last_export if self.last_export and self.last_export.exists() else Path(self.dest.get())
        p.mkdir(parents=True,exist_ok=True)
        os.startfile(str(p))

if __name__=="__main__":
    ClipForge().root.mainloop()
