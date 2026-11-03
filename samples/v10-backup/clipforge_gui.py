"""VAW ClipForge v0.2 — offline GUI with optional Gemini AI highlight selection."""
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
        self.root.title("VAW ClipForge v0.9 | Context-Aware AI Clipping")
        self.root.geometry("940x970")
        self.root.minsize(860,870)
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
        return tk.Button(parent,text=text,command=fn,relief="flat",bd=0,
                         cursor="hand2",padx=15,pady=8,
                         bg=C["red"] if primary else C["card"],fg=C["white"],
                         activebackground="#b32c43" if primary else "#333b51",
                         activeforeground=C["white"],font=("Segoe UI Semibold",10))
    def entry(self,parent,var):
        return tk.Entry(parent,textvariable=var,font=("Segoe UI",10),
                        bg=C["card"],fg=C["white"],insertbackground="white",
                        relief="flat",highlightthickness=1,
                        highlightbackground=C["line"])
    def create_ui(self):
        frame=tk.Frame(self.root,bg=C["bg"])
        frame.pack(fill="both",expand=True,padx=31,pady=20)
        self.label(frame,"VAW / CLIPFORGE",22,bold=True).pack(anchor="w")
        self.label(frame,"AI understands the story → selects complete moments → context-aware 9:16 clips",11,"muted").pack(anchor="w",pady=(0,13))

        sourcebar=tk.Frame(frame,bg=C["bg"])
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

        self.label(frame,"EXPORT FOLDER",10,"muted",True).pack(anchor="w")
        r=tk.Frame(frame,bg=C["bg"]);r.pack(fill="x",pady=(6,12))
        self.entry(r,self.dest).pack(side="left",fill="x",expand=True,ipady=9)
        self.button(r,"Choose",self.browse_out).pack(side="left",padx=(8,0))

        r=tk.Frame(frame,bg=C["bg"]);r.pack(fill="x",pady=(1,13))
        def spin(title,var,lo,hi):
            box=tk.Frame(r,bg=C["bg"]);box.pack(side="left",padx=(0,28))
            self.label(box,title,10,"muted",True).pack(anchor="w")
            tk.Spinbox(box,from_=lo,to=hi,width=10,textvariable=var,
                       bg=C["card"],fg=C["white"],insertbackground="white",
                       font=("Segoe UI",11),relief="flat").pack(anchor="w",pady=7)
        spin("CLIP COUNT",self.count,1,20)
        spin("TARGET SEC (SOFT)",self.seconds,5,180)
        box=tk.Frame(r,bg=C["bg"]);box.pack(side="left",padx=(0,22))
        self.label(box,"OUTPUT QUALITY",10,"muted",True).pack(anchor="w")
        ttk.Combobox(box,textvariable=self.resolution,state="readonly",
                     values=["1080p","720p"],width=11).pack(pady=(7,0))
        box=tk.Frame(r,bg=C["bg"]);box.pack(side="left")
        self.label(box,"9:16 LAYOUT",10,"muted",True).pack(anchor="w")
        ttk.Combobox(box,textvariable=self.layout,state="readonly",
                     values=["blur","fit","crop"],width=12).pack(pady=(8,0))

        self.label(frame,"HIGHLIGHT DETECTION",10,"muted",True).pack(anchor="w")
        r=tk.Frame(frame,bg=C["bg"]);r.pack(fill="x",pady=(6,11))
        ttk.Combobox(r,textvariable=self.mode,state="readonly",width=27,
                     values=["Gemini AI (audio)","Audio Activity (offline)"]).pack(side="left")
        self.button(r,"Set Gemini Key",self.set_key).pack(side="left",padx=9)
        self.button(r,"Remove Key",self.remove_key).pack(side="left")
        self.button(r,"Test API",self.test_api).pack(side="left",padx=(8,0))
        self.key_status=self.label(frame,"",10,"muted")
        self.key_status.pack(anchor="w",pady=(0,6))
        self.refresh_key_status()

        modelrow=tk.Frame(frame,bg=C["bg"]);modelrow.pack(fill="x",pady=(3,6))
        self.label(modelrow,"MODEL",10,"muted",True).pack(side="left",padx=(0,10))
        ttk.Combobox(modelrow,textvariable=self.model,state="normal",
                     values=["gemini-3.6-flash","gemini-3.5-flash-lite",
                             "gemini-3.8-flash","gemini-3.7-flash",
                             "gemini-3.1-flash-lite","gemini-2.5-flash"],
                     width=28).pack(side="left",fill="x",expand=True,ipady=6)
        checks=tk.Frame(frame,bg=C["bg"])
        checks.pack(fill="x",pady=(7,5))
        for var,label in [
            (self.visual,"AI analyzes sample frames too"),
            (self.caption,"Local auto-caption"),
            (self.burn,"Burn captions into Shorts"),
            (self.context_duration,"Context-aware duration (local Whisper)"),
        ]:
            tk.Checkbutton(checks,text=label,variable=var,
                bg=C["bg"],fg=C["white"],selectcolor=C["card"],
                activebackground=C["bg"],activeforeground=C["white"],
                font=("Segoe UI",9)).pack(side="left",padx=(0,11))
        advanced=tk.Frame(frame,bg=C["bg"])
        advanced.pack(fill="x",pady=(3,7))
        tk.Checkbutton(advanced,text="Auto-reframe: universal objects",
            variable=self.autoframe,bg=C["bg"],fg=C["white"],
            activebackground=C["bg"],activeforeground=C["white"],
            selectcolor=C["card"],font=("Segoe UI",9)).pack(side="left",padx=(0,18))
        tk.Checkbutton(advanced,text="Intelligent scene detection",
            variable=self.scenedetect,bg=C["bg"],fg=C["white"],
            activebackground=C["bg"],activeforeground=C["white"],
            selectcolor=C["card"],font=("Segoe UI",9)).pack(side="left",padx=(0,18))
        self.label(advanced,"Captions",9,"muted",True).pack(side="left",padx=(0,6))
        ttk.Combobox(advanced,textvariable=self.caption_style,state="readonly",
            values=["karaoke","bold_pop","minimal","gaming","neon","creator"],width=12).pack(side="left")
        focusrow=tk.Frame(frame,bg=C["bg"])
        focusrow.pack(fill="x",pady=(1,5))
        self.label(focusrow,"AUTO FOCUS",10,"muted",True).pack(side="left",padx=(0,12))
        ttk.Combobox(focusrow,textvariable=self.subject_mode,state="readonly",
            values=["universal","people","motion","center"],width=16).pack(side="left")
        self.label(focusrow,"Universal: animation, icons, diagrams, objects",9,"muted").pack(side="left",padx=12)
        self.button(frame,"Browse Subtitle Modes",self.show_caption_styles).pack(anchor="w",pady=(3,8))
        self.label(frame,"Gemini: compressed audio + optional sampled frames. Whisper boundary transcript stays local.",
                   10,"muted").pack(anchor="w",pady=(5,3))
        self.label(frame,"Use only videos you own or have permission to repurpose.",
                   10,"muted").pack(anchor="w")

        r=tk.Frame(frame,bg=C["bg"]);r.pack(fill="x",pady=(14,9))
        self.run_btn=self.button(r,"GENERATE CLIPS",self.start,True)
        self.run_btn.pack(side="left")
        self.button(r,"Open Exports",self.open_export).pack(side="left",padx=10)
        self.button(r,"Review / Timeline",self.open_review).pack(side="left",padx=5)
        self.label(frame,"ACTIVITY LOG",10,"muted",True).pack(anchor="w")
        panel=tk.Frame(frame,bg=C["card"]);panel.pack(fill="both",expand=True,pady=(8,0))
        self.logview=tk.Text(panel,height=11,bg=C["card"],fg=C["white"],
                             insertbackground="white",font=("Consolas",10),
                             relief="flat",wrap="word",padx=12,pady=10)
        self.logview.pack(fill="both",expand=True)
        self.log("Ready. Gemini ranks complete story moments; local Whisper aligns natural sentence boundaries.")
        self.log("Gemini target seconds is a soft preference; context-aware clips can vary from 12 to 180 seconds.")
        self.log("URL Mode automatically downloads one authorized public video into local cache.")
        self.log("No video is published automatically.")

    def show_caption_styles(self):
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
            "This sends compressed audio and (if enabled) sampled frames to Google AI.\n"
            "If enabled, context-aware duration uses local Whisper on this PC; the transcript is not uploaded.\n"
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
