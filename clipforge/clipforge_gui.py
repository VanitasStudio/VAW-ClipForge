"""VAW ClipForge v1.2  -  AI editorial intelligence and story composition desktop application."""
from __future__ import annotations
import os
import sys
import subprocess
import ctypes
import argparse
from clipforge.silent_process import run as silent_run, popen as silent_popen
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog
from clipforge.vanitas_widgets import (VanitasCombo, VanitasScrollbar, VanitasEntry, VanitasSpinbox, VanitasCheckbutton, VanitasButton)

from clipforge.clip_engine import process as process_local
from clipforge.gemini_highlights import process_ai, MODEL
from clipforge.secure_config import save_key, has_key, delete_key
from clipforge.gemini_connection import test_gemini_connection
from clipforge.smart_reframe import export_v04
from clipforge.url_source import (validate_url,check_link,fetch_video,clear_cache,cache_stats)
from clipforge.subtitle_presets import PRESETS, preview_image
from clipforge.production_queue import QueueManager, QueueScheduler, QueueStore
from clipforge.production_queue.runner import run_job
from PIL import ImageTk

BUNDLE_ROOT=Path(getattr(sys,"_MEIPASS",Path(__file__).resolve().parent.parent))
ROOT=Path(sys.executable).resolve().parent if getattr(sys,"frozen",False) else Path(__file__).resolve().parent.parent
ASSET_ROOT=BUNDLE_ROOT/"assets"
C={"bg":"#05070B","card":"#101827","white":"#DCE6F5",
   "muted":"#8E9DB4","red":"#075BFF","blue":"#075BFF",
   "orange":"#20BFFF","line":"#29364B","green":"#79CBA5",
   "field":"#0B111C","raised":"#172235","hover":"#1C2B42"}

def load_brand_fonts():
    """Load bundled Vanitas typefaces privately; no system installation required."""
    if os.name != "nt":
        return
    add_font=ctypes.windll.gdi32.AddFontResourceExW
    for filename in ("Archivo.ttf","Quantico-Regular.ttf","Quantico-Bold.ttf"):
        path=ASSET_ROOT/"fonts"/filename
        if path.is_file():
            add_font(str(path),0x10,None)  # FR_PRIVATE

class ClipForge:
    def __init__(self):
        load_brand_fonts()
        self.root=tk.Tk()
        self.root.title("VAW ClipForge | Vanitas Studio")
        self.root.geometry("1180x900")
        self.root.minsize(1040,720)
        icon_path=ASSET_ROOT/"branding"/"vanitas.ico"
        if icon_path.is_file():
            try:self.root.iconbitmap(str(icon_path))
            except tk.TclError:pass
        self.root.configure(bg=C["bg"])
        default_source=Path.home()/"Downloads"/"videoplayback.mp4"
        self.src=tk.StringVar(value=str(default_source) if default_source.exists() else "")
        self.local_path=tk.StringVar(value=self.src.get())
        self.video_url=tk.StringVar(value="")
        self.source_type=tk.StringVar(value="Local File")
        self.resolution=tk.StringVar(value="1080p")
        default_exports=(Path.home()/"Videos"/"VAW ClipForge" if getattr(sys,"frozen",False) else ROOT/"exports")
        self.dest=tk.StringVar(value=str(default_exports))
        self.count=tk.IntVar(value=3)
        self.seconds=tk.IntVar(value=30)
        self.standalone_output=tk.BooleanVar(value=True)
        self.smart_compilation_output=tk.BooleanVar(value=True)
        self.narrative_output=tk.BooleanVar(value=True)
        self.story_seconds=tk.IntVar(value=60)
        self.context_duration=tk.BooleanVar(value=True)
        self.layout=tk.StringVar(value="blur")
        self.mode=tk.StringVar(value="Gemini AI (audio)")
        self.model=tk.StringVar(value="gemini-3.5-flash-lite")
        self.caption=tk.BooleanVar(value=True)
        self.burn=tk.BooleanVar(value=True)
        self.visual=tk.BooleanVar(value=True)
        self.video_vision=tk.BooleanVar(value=False)
        self.autoframe=tk.BooleanVar(value=True)
        self.subject_mode=tk.StringVar(value="universal")
        self.scenedetect=tk.BooleanVar(value=True)
        self.caption_style=tk.StringVar(value="karaoke")
        self.caption_label=tk.StringVar(value="Karaoke")
        self.busy=False
        self.last_export=None
        self.messages=queue.Queue()
        app_data=Path(os.environ.get("LOCALAPPDATA",Path.home()/"AppData"/"Local"))
        queue_db=app_data/"VanitasStudio"/"VAWClipForge"/"production_queue.sqlite3"
        self.queue_manager=QueueManager(QueueStore(queue_db),default_exports,
            on_event=lambda event:self.messages.put(("queue_event",event)))
        self.queue_scheduler=QueueScheduler(self.queue_manager,
            lambda job,progress:run_job(job,progress,
                log=lambda msg:self.messages.put(("log",f"[{job.source_name}] {msg}"))),
            on_event=lambda event:self.messages.put(("queue_event",event)))
        self.queue_window=None
        self._queue_refresh_id=None
        self.create_ui()
        self._poll_after_id=self.root.after(200,self.poll)
        self.root.protocol("WM_DELETE_WINDOW",self.close)

    def label(self,parent,text,size=10,color="white",bold=False):
        font=("Archivo",size,"bold" if bold else "normal")
        return tk.Label(parent,text=text,bg=C["bg"],fg=C.get(color,color),
                        font=font,anchor="w",justify="left")
    def button(self,parent,text,fn,primary=False):
        normal=C["red"] if primary else C["raised"]
        hover="#20BFFF" if primary else "#263A58"
        return VanitasButton(parent,text=text,command=fn,primary=primary,
                             font=("Archivo",10,"bold"),padx=15,pady=9)
    def entry(self,parent,var):
        return VanitasEntry(parent,textvariable=var,font=("Archivo",10),
                            bg=C["field"],fg=C["white"],insertbackground=C["white"])
    def create_ui(self):
        # Refined desktop layout: clear sections, readable spacing and a fixed action area.
        shell=tk.Frame(self.root,bg=C["bg"])
        shell.pack(fill="both",expand=True,padx=26,pady=20)

        header=tk.Frame(shell,bg=C["bg"])
        header.pack(fill="x",pady=(0,12))
        mark=tk.Canvas(header,width=42,height=42,bg=C["bg"],highlightthickness=0)
        mark.pack(side="left",padx=(0,12))
        mark.create_polygon(5,7,15,7,22,25,29,7,39,7,25,37,19,37,fill=C["white"],outline="")
        mark.create_polygon(29,7,39,7,34,18,29,18,fill=C["blue"],outline="")
        mark.create_line(5,7,15,7,22,25,29,7,39,7,fill=C["white"],width=1)
        brand=tk.Frame(header,bg=C["bg"])
        brand.pack(side="left",anchor="center")
        tk.Label(brand,text="CLIPFORGE",bg=C["bg"],fg=C["white"],
                 font=("Quantico",21)).pack(anchor="w")
        tk.Label(brand,text="VANITAS STUDIO",bg=C["bg"],fg=C["muted"],
                 font=("Archivo",8,"bold")).pack(anchor="w",pady=(0,1))
        tk.Label(header,text="V1.2.1  /  EDITORIAL WORKSPACE",bg=C["bg"],fg=C["muted"],
                 font=("Archivo",8,"bold")).pack(side="right",anchor="center")

        # Scrollable settings; the primary action and activity log stay visible.
        scroll_area=tk.Frame(shell,bg=C["bg"])
        scroll_area.pack(fill="both",expand=True)
        canvas=tk.Canvas(scroll_area,bg=C["bg"],highlightthickness=0,bd=0)
        scrollbar=VanitasScrollbar(scroll_area,orient="vertical",command=canvas.yview)
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
                            font=("Archivo",size,"bold" if bold else "normal"),
                            anchor="w",justify="left")
        def section(title,subtitle):
            card=tk.Frame(content,bg=C["card"],highlightbackground=C["line"],
                          highlightthickness=1,bd=0)
            card.pack(fill="x",pady=(0,11))
            head=tk.Frame(card,bg=C["card"])
            head.pack(fill="x",padx=17,pady=(12,2))
            label(head,title,11,"white",True).pack(anchor="w")
            body=tk.Frame(card,bg=C["card"])
            body.pack(fill="x",padx=17,pady=(2,14))
            return body

        # 01  -  Source and destination.
        source=section("SOURCE","")
        sourcebar=tk.Frame(source,bg=C["card"])
        sourcebar.pack(fill="x",pady=(0,8))
        label(sourcebar,"INPUT TYPE",9,"muted",True).pack(side="left",padx=(0,10))
        self.source_switch=VanitasCombo(sourcebar,textvariable=self.source_type,
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

        # 02  -  Output settings.
        output=section("CLIP SETTINGS","")
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
                widget=VanitasSpinbox(box,from_=opts[0],to=opts[1],width=9,
                    textvariable=var,font=("Archivo",11))
            else:
                widget=VanitasCombo(box,textvariable=var,state="readonly",
                                    values=opts[0],width=11)
            widget.pack(anchor="w",fill="x",ipady=3)

        # 02B  -  Output modes.
        outputs=section("OUTPUTS","")
        for col in range(2):
            outputs.grid_columnconfigure(col,weight=1)
        output_checks=[
            (self.standalone_output,"Standalone Highlights",0,0),
            (self.smart_compilation_output,"Story Composer  -  Smart Compilation",0,1),
            (self.narrative_output,"Story Composer  -  Narrative Reconstruction",1,0),
        ]
        for variable,text,row,col in output_checks:
            VanitasCheckbutton(outputs,text=text,variable=variable,
                bg=C["card"],font=("Archivo",9)).grid(
                    row=row,column=col,sticky="w",padx=(0,12),pady=4)
        story_target=tk.Frame(outputs,bg=C["card"])
        story_target.grid(row=1,column=1,sticky="e")
        label(story_target,"COMPOSED DURATION (12 - 180s)",9,"muted",True).pack(side="left",padx=(0,9))
        VanitasSpinbox(story_target,from_=12,to=180,width=7,
            textvariable=self.story_seconds,font=("Archivo",10)).pack(side="left")

        # 03  -  AI engine.
        ai=section("AI ENGINE","")
        ai.grid_columnconfigure(1,weight=1)
        label(ai,"DETECTION MODE",9,"muted",True).grid(row=0,column=0,sticky="w",pady=(0,6))
        label(ai,"GEMINI MODEL",9,"muted",True).grid(row=0,column=1,sticky="w",padx=(15,0),pady=(0,6))
        VanitasCombo(ai,textvariable=self.mode,state="readonly",width=27,
            values=["Gemini AI (audio)","Audio Activity (offline)"]).grid(
                row=1,column=0,sticky="ew",padx=(0,10))
        self.model_combo=VanitasCombo(ai,textvariable=self.model,state="normal",
            values=["gemini-3.6-flash","gemini-3.5-flash-lite",
                    "gemini-3.8-flash","gemini-3.7-flash",
                    "gemini-3.1-flash-lite","gemini-2.5-flash"])
        self.model_combo.grid(row=1,column=1,sticky="ew",padx=(5,0))
        keyrow=tk.Frame(ai,bg=C["card"])
        keyrow.grid(row=2,column=0,columnspan=2,sticky="ew",pady=(11,0))
        self.key_status=tk.Label(keyrow,text="",bg=C["card"],fg=C["muted"],
                                 font=("Archivo",9),anchor="w")
        self.key_status.pack(side="left",fill="x",expand=True)
        self.button(keyrow,"Set API Key",self.set_key).pack(side="right",padx=(7,0))
        self.button(keyrow,"Remove Key",self.remove_key).pack(side="right",padx=(7,0))
        self.button(keyrow,"Test Connection",self.test_api).pack(side="right")
        self.refresh_key_status()

        # 04  -  Intelligent processing.
        smart=section("PROCESSING","")
        smart.grid_columnconfigure(0,weight=1)
        smart.grid_columnconfigure(1,weight=1)
        checks=[
            (self.visual,"AI visual analysis (sample frames)",0,0),
            (self.caption,"Automatic subtitles (local Whisper)",0,1),
            (self.burn,"Burn subtitles into exported clips",1,0),
            (self.context_duration,"Context-aware duration (local Whisper)",1,1),
            (self.autoframe,"Auto-reframe universal subjects",2,0),
            (self.scenedetect,"Intelligent scene detection",2,1),
            (self.video_vision,"Extra local frame sampling (Video Vision MCP)",3,0),
        ]
        for var,text,row,col in checks:
            VanitasCheckbutton(smart,text=text,variable=var,
                bg=C["card"],font=("Archivo",9)).grid(
                    row=row,column=col,sticky="w",padx=(0,12),pady=4)
        focus=tk.Frame(smart,bg=C["card"])
        focus.grid(row=4,column=0,columnspan=2,sticky="ew",pady=(8,0))
        label(focus,"AUTO FOCUS",9,"muted",True).pack(side="left",padx=(0,12))
        VanitasCombo(focus,textvariable=self.subject_mode,state="readonly",
            values=["universal","people","motion","center"],width=16).pack(side="left")

        # 05  -  Captions.
        captions=section("CAPTIONS","")
        caprow=tk.Frame(captions,bg=C["card"])
        caprow.pack(fill="x")
        label(caprow,"SUBTITLE MODE",9,"muted",True).pack(side="left",padx=(0,12))
        self.caption_picker=VanitasCombo(caprow,textvariable=self.caption_label,
            state="readonly",values=[p.name for p in PRESETS],width=25)
        self.caption_picker.pack(side="left")
        self.caption_picker.bind("<<ComboboxSelected>>",self.set_caption_from_label)
        self.button(caprow,"Browse Styles",self.show_caption_styles).pack(side="left",padx=(9,0))
        self.caption_hint=label(captions,"Karaoke  -  word-by-word crimson highlight.",9,"muted")
        self.caption_hint.pack(anchor="w",pady=(9,0))
        label(content,"Only process videos you own or have permission to repurpose.",
              9,"muted").pack(anchor="w",pady=(0,10))

        # Fixed action bar and compact activity log.
        footer=tk.Frame(shell,bg=C["bg"])
        footer.pack(fill="x",pady=(9,0))
        actions=tk.Frame(footer,bg=C["bg"])
        actions.pack(fill="x",pady=(0,8))
        self.run_btn=self.button(actions,"GENERATE CLIPS",self.start,True)
        self.run_btn.pack(side="left")
        self.button(actions,"Production Queue",self.open_queue).pack(side="left",padx=(9,0))
        self.button(actions,"Open Exports",self.open_export).pack(side="left",padx=(9,0))
        self.button(actions,"Review / Timeline",self.open_review).pack(side="left",padx=(8,0))
        self.button(actions,"Editorial Report",self.open_editorial_report).pack(side="left",padx=(8,0))
        logcard=tk.Frame(footer,bg=C["card"],highlightbackground=C["line"],
                         highlightthickness=1,bd=0)
        logcard.pack(fill="x")
        loghead=tk.Frame(logcard,bg=C["card"])
        loghead.pack(fill="x",padx=12,pady=(7,2))
        label(loghead,"ACTIVITY",9,"muted",True).pack(side="left")
        self.logview=tk.Text(logcard,height=3,bg="#0E131B",fg="#D9E0E8",
            insertbackground=C["white"],font=("Archivo",9),relief="flat",
            wrap="word",padx=11,pady=8,bd=0)
        self.logview.pack(fill="both",expand=True,padx=8,pady=(2,8))
        self.log("Ready.")

    def set_caption_from_label(self,_=None):
        selected=self.caption_label.get()
        preset=next((p for p in PRESETS if p.name==selected),None)
        if not preset:
            return
        self.caption_style.set(preset.id)
        if hasattr(self,"caption_hint"):
            self.caption_hint.configure(text=f"{preset.name}  -  {preset.sub}.")
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
                        self.caption_hint.configure(text=f"{chosen.name}  -  {chosen.sub}.")
                self.log("Subtitle mode selected: "+(chosen.name if chosen else style))
                dialog.destroy()
            tk.Button(frame,image=photo,command=select,borderwidth=0,
                      relief="flat",bg=C["card"],cursor="hand2").pack()
            tk.Label(frame,text=preset.name,bg=C["card"],fg=C["white"],
                     font=("Archivo",11,"bold"),anchor="w").pack(fill="x",pady=(6,0))
            tk.Label(frame,text=preset.sub,bg=C["card"],fg=C["muted"],
                     font=("Archivo",9),anchor="w").pack(fill="x")
        dialog._images=previews

    def refresh_key_status(self):
        self.key_status.configure(text="Gemini key configured" if has_key()
                                  else "Gemini key not configured",
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
        if self.queue_scheduler.current_job_id or any(job.status.value in {"queued","processing"} for job in self.queue_manager.list_jobs()):
            messagebox.showwarning("Production Queue active","Finish or pause the batch queue before starting a separate single-video job. This keeps heavy processing sequential.")
            return
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
        visual=self.visual.get()
        use_vision=self.video_vision.get()
        standalone=self.standalone_output.get()
        smart_compilation=self.smart_compilation_output.get()
        narrative_reconstruction=self.narrative_output.get()
        try:
            story_seconds=int(self.story_seconds.get())
        except (ValueError,tk.TclError):
            messagebox.showerror("Invalid duration","Story Composer duration must be a number from 12 to 180 seconds.")
            return
        if not (standalone or smart_compilation or narrative_reconstruction):
            messagebox.showwarning("Choose an output","Enable at least one output mode.")
            return
        if not 12 <= story_seconds <= 180:
            messagebox.showerror("Invalid duration","Story Composer duration must be between 12 and 180 seconds.")
            return
        if (smart_compilation or narrative_reconstruction) and not ai:
            messagebox.showwarning("Gemini required","Story Composer needs Gemini AI editorial analysis. Standalone Highlights can still use offline audio mode.")
            return
        if ai and not has_key():
            messagebox.showwarning("API key needed","Click Set Gemini Key first.")
            return
        if use_vision and (not ai or not visual):
            messagebox.showwarning(
                "Visual analysis required",
                "Video Vision MCP needs Gemini AI and AI visual analysis enabled. It does not run in offline audio mode."
            )
            return
        consent=(
            "This sends compressed audio and (if enabled) sparse timestamped frames to Google AI for story and visual editorial scoring.\n"
            "Visual analysis describes generic content (animation, objects, diagrams, etc.); it does not identify people.\n"
            + ("Video Vision MCP adds up to 8 extra local frames; that MCP step sends no transcript or video to a cloud service.\n" if use_vision else "")
            + "Context-aware duration uses local Whisper on this PC; the transcript is not uploaded.\n"
            + "Up to 6 sections; failed calls may retry. API quota/cost may apply.\n"
            + "Continue?"
        )
        if ai and not messagebox.askyesno("Send video excerpts to Google Gemini?",consent):
            return
        dest_base=Path(self.dest.get().strip()).expanduser().resolve()
        style=self.layout.get()
        model=self.model.get().strip()
        captions=self.caption.get()
        burn=self.burn.get()
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
                vision_result=None
                if ai:
                    vision_frames=None
                    if use_vision:
                        self.messages.put(("log","Video Vision MCP: extracting a bounded set of local frames..."))
                        try:
                            from clipforge.video_vision_adapter import VideoVisionMCPProvider
                            from clipforge.vision_cache import CachedVisionProvider
                            from clipforge.vision_quality import filter_vision_frames
                            from clipforge.clip_engine import probe_duration
                            vision_provider=CachedVisionProvider(VideoVisionMCPProvider())
                            vision_result=vision_provider.analyze(
                                current,duration_seconds=float(probe_duration(current)),
                                max_frames=8,
                            )
                            quality=filter_vision_frames(
                                vision_result.frames,
                                duration_seconds=float(probe_duration(current)),
                                max_frames=8,
                            )
                            vision_frames=quality.frames
                            self.messages.put(("log",f"Video Vision MCP supplied {len(vision_frames)} additional frames (cache: {vision_result.metadata.get('cache','miss')})."))
                            for quality_warning in quality.warnings:
                                self.messages.put(("log","Vision quality: "+quality_warning))
                            for warning in vision_result.warnings:
                                self.messages.put(("log","Vision note: "+warning))
                        except Exception as vision_exc:
                            self.messages.put(("log",f"Video Vision MCP unavailable; using built-in frame sampling instead. {type(vision_exc).__name__}: {str(vision_exc)[:160]}"))
                    selection=process_ai(current,dest,count,seconds,style,model,
                        log=lambda x:self.messages.put(("log",x)),
                        visual=visual,render=False,
                        context_aware=context_aware,duration_model="base",
                        vision_frames=vision_frames)
                else:
                    if context_aware:
                        self.messages.put(("log","Context-aware sentence alignment requires Gemini AI; offline audio mode keeps the requested fixed duration."))
                    selection=process_local(current,dest,count,seconds,style,
                        log=lambda x:self.messages.put(("log",x)),dry_run=True)

                successes=[]
                failures=[]
                suggestion_items=[]
                if standalone:
                    self.messages.put(("log","Rendering Standalone Highlights..."))
                    outcome=export_v04(current,dest,selection["clips"],
                        auto=auto,scenes=scene,captions=captions,
                        burn=burn,style=cap_style,layout=style,
                        subject_mode=subject_mode,resolution=resolution,
                        log=lambda x:self.messages.put(("log",x)))
                    completed=sum(bool(x.get("ok")) for x in outcome["clips"])
                    suggestion_items.extend({
                        "output": item.get("output"),
                        "start": item.get("start", 0),
                        "duration": item.get("duration", 0),
                        "title": item.get("title", "Standalone Highlight"),
                        "reason": item.get("reason", ""),
                        "summary": item.get("payoff", ""),
                    } for item in outcome["clips"] if item.get("ok"))
                    if completed:
                        successes.append(f"Standalone Highlights: {completed}/{len(outcome['clips'])} clips")
                    else:
                        failures.append("Standalone Highlights: no clips rendered.")
                if smart_compilation or narrative_reconstruction:
                    self.messages.put(("log","Building the unified analysis bundle for Story Composer..."))
                    from dataclasses import replace
                    from clipforge.unified_analyzer import probe_source, build_analysis_bundle
                    from clipforge.smart_reframe import shot_boundaries
                    from clipforge.gemini_highlights import request_story_compositions
                    from clipforge.clipforge_contracts import (
                        CaptionPlan, CompositionStrategy, RenderSettings,
                    )
                    from clipforge.story_composer import build_composition
                    from clipforge.composition_renderer import render_composition

                    media=probe_source(current)
                    cuts=shot_boundaries(current) if scene else []
                    bundle=build_analysis_bundle(
                        media,
                        transcript_rows=selection.get("transcript_spans",[]),
                        scene_cuts=cuts,
                        editorial_rows=selection.get("ranked_candidates",[]),
                    )
                    if vision_result is not None:
                        try:
                            from clipforge.multimodal_fusion import fuse_visual_evidence
                            bundle=fuse_visual_evidence(bundle,vision_result,max_frames=8)
                        except Exception as fusion_exc:
                            self.messages.put(("log",f"Visual evidence fusion skipped: {str(fusion_exc)[:160]}"))
                    try:
                        story=request_story_compositions(bundle.events)
                        bundle=replace(
                            bundle,
                            composition_orders=story["composition_orders"],
                            event_roles=story["event_roles"],
                            event_dependencies=story["event_dependencies"],
                        )
                        self.messages.put(("log","Gemini supplied separate Smart Compilation and Narrative Reconstruction story maps."))
                    except Exception as story_exc:
                        self.messages.put(("log",f"Story map unavailable; deterministic editorial ordering will be used. {type(story_exc).__name__}: {str(story_exc)[:150]}"))

                    strategies=[]
                    if smart_compilation:
                        strategies.append(CompositionStrategy.SMART_COMPILATION)
                    if narrative_reconstruction:
                        strategies.append(CompositionStrategy.NARRATIVE_RECONSTRUCTION)
                    width=1080 if resolution=="1080p" else 720
                    height=1920 if resolution=="1080p" else 1280
                    for strategy in strategies:
                        try:
                            edl=build_composition(
                                bundle,strategy,
                                target_duration_seconds=story_seconds,
                            )
                            edl=replace(
                                edl,
                                captions=CaptionPlan(
                                    enabled=captions,preset_id=cap_style,
                                    burn_in=burn,export_srt=True,
                                ),
                                render=RenderSettings(width=width,height=height,fps=30),
                            )
                            output_path=dest/f"{current.stem}_{strategy.value}.mp4"
                            rendered=render_composition(
                                bundle,edl,output_path,
                                layout=style,auto_reframe=auto,
                                scene_detection=scene,subject_mode=subject_mode,
                                resolution=resolution,
                                log=lambda x:self.messages.put(("log",x)),
                            )
                            successes.append(f"{edl.title}: {rendered['duration_seconds']:.1f}s")
                            for segment in edl.segments:
                                event=next((event for event in bundle.events if event.event_id in segment.event_ids),None)
                                suggestion_items.append({
                                    "output": str(rendered["output"]),
                                    "start": segment.source_in,
                                    "duration": segment.duration_seconds,
                                    "title": event.topic if event else edl.title,
                                    "reason": segment.reason,
                                    "summary": event.summary if event else "",
                                })
                        except Exception as composition_exc:
                            failures.append(f"{strategy.value}: {type(composition_exc).__name__}: {str(composition_exc)[:220]}")
                            self.messages.put(("log",f"{strategy.value} failed: {str(composition_exc)[:220]}"))
                if not successes:
                    raise RuntimeError("No requested output completed. " + " | ".join(failures))
                try:
                    from clipforge.title_hashtag_suggestions import write_suggestion_markdown
                    suggestion_file=write_suggestion_markdown(
                        dest,
                        suggestion_items,
                        selection.get("transcript_spans",[]),
                        allow_ai=ai,
                    )
                    if suggestion_file:
                        self.messages.put(("log",f"Title and hashtag suggestions saved: {suggestion_file.name}"))
                        successes.append("Title & Hashtag Suggestions: " + suggestion_file.name)
                except Exception as suggestion_exc:
                    failures.append("Title & Hashtag Suggestions: " + str(suggestion_exc)[:180])
                    self.messages.put(("log","Title/hashtag suggestions could not be generated: "+str(suggestion_exc)[:180]))
                summary=os.linesep.join(successes)+f"{os.linesep}{os.linesep}Output folder: {dest}"
                if failures:
                    summary+=os.linesep*2+"Some outputs could not be created:"+os.linesep+os.linesep.join(failures)
                self.messages.put(("done",summary))
            except Exception as exc:
                self.messages.put(("error",str(exc)[:900]))
        threading.Thread(target=work,daemon=True).start()

    def _queue_config_snapshot(self):
        return {
            "ai": self.mode.get().startswith("Gemini"),
            "visual": bool(self.visual.get()),
            "video_vision": bool(self.video_vision.get()),
            "standalone": bool(self.standalone_output.get()),
            "smart_compilation": bool(self.smart_compilation_output.get()),
            "narrative_reconstruction": bool(self.narrative_output.get()),
            "count": int(self.count.get()), "seconds": int(self.seconds.get()),
            "story_seconds": int(self.story_seconds.get()),
            "resolution": self.resolution.get(), "layout": self.layout.get(),
            "model": self.model.get().strip(), "captions": bool(self.caption.get()),
            "burn": bool(self.burn.get()), "context_duration": bool(self.context_duration.get()),
            "subject_mode": self.subject_mode.get(), "autoframe": bool(self.autoframe.get()),
            "scenedetect": bool(self.scenedetect.get()), "caption_style": self.caption_style.get(),
        }

    def open_queue(self):
        if self.queue_window and self.queue_window.winfo_exists():
            self.queue_window.lift()
            self.refresh_queue_window()
            return
        window=tk.Toplevel(self.root)
        self.queue_window=window
        window.title("VAW ClipForge | Production Queue")
        window.geometry("940x650")
        window.minsize(760,500)
        window.configure(bg=C["bg"])
        window.protocol("WM_DELETE_WINDOW",self._close_queue_window)
        shell=tk.Frame(window,bg=C["bg"])
        shell.pack(fill="both",expand=True,padx=22,pady=18)
        header=tk.Frame(shell,bg=C["bg"])
        header.pack(fill="x",pady=(0,14))
        tk.Label(header,text="PRODUCTION QUEUE",bg=C["bg"],fg=C["white"],
            font=("Quantico",18)).pack(anchor="w")
        tk.Label(header,text="BATCH PRODUCTION  /  SEQUENTIAL LOCAL WORKER",
            bg=C["bg"],fg=C["muted"],font=("Archivo",8,"bold")).pack(anchor="w",pady=(2,0))
        stats=tk.Frame(shell,bg=C["card"],highlightbackground=C["line"],highlightthickness=1)
        stats.pack(fill="x",pady=(0,12))
        self.queue_stats=tk.Label(stats,text="",bg=C["card"],fg=C["white"],
            font=("Archivo",10,"bold"),anchor="w")
        self.queue_stats.pack(fill="x",padx=14,pady=11)
        list_card=tk.Frame(shell,bg=C["card"],highlightbackground=C["line"],highlightthickness=1)
        list_card.pack(fill="both",expand=True)
        list_head=tk.Frame(list_card,bg=C["card"])
        list_head.pack(fill="x",padx=12,pady=(10,5))
        tk.Label(list_head,text="JOBS",bg=C["card"],fg=C["muted"],
            font=("Archivo",9,"bold")).pack(side="left")
        self.queue_list=tk.Listbox(list_card,bg=C["field"],fg=C["white"],
            selectbackground=C["blue"],selectforeground="#FFFFFF",
            font=("Archivo",9),relief="flat",highlightthickness=0,
            activestyle="none",height=16)
        self.queue_list.pack(side="left",fill="both",expand=True,padx=(10,0),pady=(0,10))
        queue_scroll=VanitasScrollbar(list_card,orient="vertical",command=self.queue_list.yview)
        queue_scroll.pack(side="right",fill="y",padx=(0,10),pady=(0,10))
        self.queue_list.configure(yscrollcommand=queue_scroll.set)
        self.queue_list.bind("<Double-Button-1>",self.show_selected_job)
        actions=tk.Frame(shell,bg=C["bg"])
        actions.pack(fill="x",pady=(12,0))
        primary_actions=tk.Frame(actions,bg=C["bg"])
        primary_actions.pack(fill="x")
        secondary_actions=tk.Frame(actions,bg=C["bg"])
        secondary_actions.pack(fill="x",pady=(7,0))
        self.button(primary_actions,"ADD VIDEOS",self.add_videos_to_queue,True).pack(side="left")
        self.button(primary_actions,"START QUEUE",self.start_queue).pack(side="left",padx=(7,0))
        self.button(primary_actions,"PAUSE AFTER CURRENT",self.pause_queue).pack(side="left",padx=(7,0))
        self.button(primary_actions,"RESUME",self.resume_queue).pack(side="left",padx=(7,0))
        self.button(secondary_actions,"CONFIGURE SELECTED",self.configure_selected_job).pack(side="left")
        self.button(secondary_actions,"RETRY FAILED",self.retry_selected_job).pack(side="left",padx=(7,0))
        self.button(secondary_actions,"REMOVE PENDING",self.remove_selected_job).pack(side="left",padx=(7,0))
        self.refresh_queue_window()
        self._schedule_queue_refresh()

    def _close_queue_window(self):
        if self._queue_refresh_id:
            try:self.root.after_cancel(self._queue_refresh_id)
            except tk.TclError:pass
            self._queue_refresh_id=None
        if self.queue_window:
            self.queue_window.destroy()
        self.queue_window=None

    def _schedule_queue_refresh(self):
        if self.queue_window and self.queue_window.winfo_exists():
            self._queue_refresh_id=self.root.after(1000,self._queue_refresh_tick)

    def _queue_refresh_tick(self):
        self._queue_refresh_id=None
        if self.queue_window and self.queue_window.winfo_exists():
            self.refresh_queue_window()
            self._schedule_queue_refresh()

    def refresh_queue_window(self):
        if not (self.queue_window and self.queue_window.winfo_exists()):
            return
        jobs=self.queue_manager.list_jobs()
        counts={status.value:sum(job.status.value==status.value for job in jobs)
                for status in __import__("clipforge.production_queue.models",fromlist=["JobStatus"]).JobStatus}
        self.queue_stats.configure(text=(
            f"TOTAL  {len(jobs):02d}     QUEUED  {counts['queued']:02d}     "
            f"PROCESSING  {counts['processing']:02d}     COMPLETED  {counts['completed']:02d}     "
            f"FAILED  {counts['failed']:02d}     CANCELLED  {counts['cancelled']:02d}"
        ))
        selected=self.queue_list.curselection()
        selected_id=self.queue_job_ids[selected[0]] if selected and hasattr(self,"queue_job_ids") and selected[0]<len(self.queue_job_ids) else None
        self.queue_list.delete(0,"end")
        self.queue_job_ids=[]
        for job in jobs:
            stage=job.current_stage or "Waiting"
            percent=f"{job.progress:.0f}%" if job.status.value=="processing" and job.progress>0 else ""
            retry=f"  /  retry {job.retry_count}" if job.retry_count else ""
            line=f"{job.source_name}   |   {job.status.value.upper()}   |   {stage}   {percent}{retry}"
            self.queue_job_ids.append(job.job_id)
            self.queue_list.insert("end",line)
            if job.status.value=="failed":
                self.queue_list.itemconfigure("end",fg="#FF8A8A")
            elif job.status.value=="completed":
                self.queue_list.itemconfigure("end",fg=C["green"])
            elif job.status.value=="processing":
                self.queue_list.itemconfigure("end",fg="#20BFFF")
        if selected_id in self.queue_job_ids:
            index=self.queue_job_ids.index(selected_id)
            self.queue_list.selection_set(index)
            self.queue_list.see(index)

    def add_videos_to_queue(self):
        paths=filedialog.askopenfilenames(title="Add source videos to production queue",
            filetypes=[("Video files","*.mp4 *.mov *.mkv *.avi *.webm *.m4v"),("All files","*.*")])
        if not paths:return
        try:
            config=self._queue_config_snapshot()
        except (ValueError,tk.TclError) as exc:
            messagebox.showerror("Invalid production settings",str(exc));return
        if not (config["standalone"] or config["smart_compilation"] or config["narrative_reconstruction"]):
            messagebox.showwarning("Choose an output","Enable at least one output mode before adding videos.");return
        if (config["smart_compilation"] or config["narrative_reconstruction"]) and not config["ai"]:
            messagebox.showwarning("Gemini required","Story Composer needs Gemini AI editorial analysis.");return
        if config["ai"] and not has_key():
            messagebox.showwarning("API key needed","Configure the Gemini API key before adding this batch.");return
        if config["ai"]:
            consent=("This batch sends compressed audio and optional sparse timestamped frames to Gemini for editorial analysis. "
                "Original source video and full transcript are not uploaded. Local Whisper remains on this PC. "
                "API quota/cost may apply. Continue?")
            if not messagebox.askyesno("Gemini batch processing consent",consent):return
        destination=self.dest.get().strip()
        if not destination:
            messagebox.showwarning("Export location required","Choose an export folder before adding videos.");return
        try:
            self.queue_manager.output_root=Path(destination).expanduser().resolve()
            self.queue_manager.output_root.mkdir(parents=True,exist_ok=True)
            added=self.queue_manager.add_sources(paths,"creator-default",config)
        except Exception as exc:
            messagebox.showerror("Queue import failed",str(exc));return
        self.log(f"Added {len(added)} video(s) to Production Queue.")
        self.refresh_queue_window()

    def start_queue(self):
        if self.busy:
            messagebox.showwarning("Single-video production active","Wait for the current single-video job to finish before starting the batch queue.")
            return
        if not any(job.status.value=="queued" for job in self.queue_manager.list_jobs()):
            messagebox.showinfo("Production Queue","There are no queued jobs to process.");return
        self.queue_scheduler.start()
        self.queue_scheduler.notify_new_jobs()
        self.log("Production Queue started with one sequential worker.")

    def pause_queue(self):
        self.queue_scheduler.pause_after_current()

    def resume_queue(self):
        self.queue_scheduler.resume()

    def _selected_queue_job(self):
        selected=self.queue_list.curselection() if hasattr(self,"queue_list") else ()
        if not selected:return None
        index=selected[0]
        if index>=len(getattr(self,"queue_job_ids",[])):return None
        return next((job for job in self.queue_manager.list_jobs()
                     if job.job_id==self.queue_job_ids[index]),None)

    def retry_selected_job(self):
        job=self._selected_queue_job()
        if not job:
            messagebox.showinfo("Production Queue","Select a failed job first.");return
        try:self.queue_manager.retry(job.job_id)
        except Exception as exc:messagebox.showwarning("Retry unavailable",str(exc));return
        self.refresh_queue_window()

    def remove_selected_job(self):
        job=self._selected_queue_job()
        if not job:
            messagebox.showinfo("Production Queue","Select a pending job first.");return
        try:self.queue_manager.remove_pending(job.job_id)
        except Exception as exc:messagebox.showwarning("Remove unavailable",str(exc));return
        self.refresh_queue_window()

    def show_selected_job(self,_event=None):
        job=self._selected_queue_job()
        if not job:return
        details=(f"Source: {job.source_path}\\nStatus: {job.status.value}\\n"
            f"Stage: {job.current_stage or '-'}\\nOutput: {job.output_directory}\\n"
            f"Preset: {job.preset_id}\\nRetries: {job.retry_count}\\n"
            f"Error: {job.error or '-'}")
        messagebox.showinfo("Production Job Details",details)

    def configure_selected_job(self):
        job=self._selected_queue_job()
        if not job:
            messagebox.showinfo("Production Queue","Select a queued job to configure.");return
        if job.status.value!="queued":
            messagebox.showwarning("Configuration locked","Only queued jobs can be configured.");return
        cfg=job.config_snapshot
        dialog=tk.Toplevel(self.queue_window)
        dialog.title("Configure Production Job")
        dialog.configure(bg=C["bg"])
        dialog.transient(self.queue_window)
        dialog.grab_set()
        body=tk.Frame(dialog,bg=C["card"],highlightbackground=C["line"],highlightthickness=1)
        body.pack(fill="both",expand=True,padx=16,pady=16)
        tk.Label(body,text=job.source_name,bg=C["card"],fg=C["white"],
            font=("Archivo",11,"bold")).grid(row=0,column=0,columnspan=2,sticky="w",padx=14,pady=(14,10))
        resolution=tk.StringVar(value=cfg.get("resolution","1080p"))
        count=tk.IntVar(value=cfg.get("count",3))
        seconds=tk.IntVar(value=cfg.get("seconds",30))
        story_seconds=tk.IntVar(value=cfg.get("story_seconds",60))
        captions=tk.BooleanVar(value=cfg.get("captions",True))
        standalone=tk.BooleanVar(value=cfg.get("standalone",True))
        smart=tk.BooleanVar(value=cfg.get("smart_compilation",False))
        narrative=tk.BooleanVar(value=cfg.get("narrative_reconstruction",False))
        fields=[("Resolution",VanitasCombo(body,textvariable=resolution,state="readonly",values=["1080p","720p"],width=12)),
                ("Highlight count",VanitasSpinbox(body,from_=1,to=20,textvariable=count,width=10)),
                ("Highlight target (sec)",VanitasSpinbox(body,from_=5,to=180,textvariable=seconds,width=10)),
                ("Story target (sec)",VanitasSpinbox(body,from_=12,to=180,textvariable=story_seconds,width=10))]
        for row,(name,widget) in enumerate(fields,1):
            tk.Label(body,text=name,bg=C["card"],fg=C["muted"],font=("Archivo",9)).grid(row=row,column=0,sticky="w",padx=14,pady=5)
            widget.grid(row=row,column=1,sticky="e",padx=14,pady=5)
        checks=tk.Frame(body,bg=C["card"])
        checks.grid(row=5,column=0,columnspan=2,sticky="w",padx=14,pady=8)
        for variable,label_text in [(standalone,"Standalone Highlights"),(smart,"Smart Compilation"),(narrative,"Narrative Reconstruction"),(captions,"Automatic captions")]:
            VanitasCheckbutton(checks,text=label_text,variable=variable,bg=C["card"],font=("Archivo",9)).pack(anchor="w",pady=2)
        def save_override():
            if not (standalone.get() or smart.get() or narrative.get()):
                messagebox.showwarning("Choose an output","At least one output mode is required.",parent=dialog);return
            if (smart.get() or narrative.get()) and not cfg.get("ai",False):
                messagebox.showwarning("Gemini required","Story Composer requires Gemini AI.",parent=dialog);return
            try:
                self.queue_manager.update_config(job.job_id,{
                    "resolution":resolution.get(),"count":int(count.get()),"seconds":int(seconds.get()),
                    "story_seconds":int(story_seconds.get()),"captions":captions.get(),
                    "standalone":standalone.get(),"smart_compilation":smart.get(),
                    "narrative_reconstruction":narrative.get()})
            except Exception as exc:
                messagebox.showerror("Configuration failed",str(exc),parent=dialog);return
            dialog.destroy()
            self.refresh_queue_window()
        self.button(body,"SAVE JOB OVERRIDE",save_override,True).grid(row=6,column=0,columnspan=2,padx=14,pady=(8,14),sticky="ew")

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
                elif kind=="queue_event":
                    event=msg
                    self.log(f"[Queue] {event.get('message','')}")
                    if self.queue_window and self.queue_window.winfo_exists():
                        self.refresh_queue_window()
                else:
                    self.busy=False;self.run_btn.configure(state="normal")
                    self.log(msg)
                    if kind=="done":messagebox.showinfo("Clips exported",msg)
                    else:messagebox.showerror("ClipForge",msg)
        except queue.Empty:
            pass
        self._poll_after_id=self.root.after(200,self.poll)

    def close(self):
        if self.queue_scheduler.current_job_id:
            messagebox.showwarning(
                "Production still running",
                "ClipForge will not close while a production job is active. Use PAUSE AFTER CURRENT, wait for the active job to finish, then close safely."
            )
            return
        self.queue_scheduler.shutdown(wait=True,timeout=3)
        after_id=getattr(self,"_queue_refresh_id",None)
        if after_id:
            try:self.root.after_cancel(after_id)
            except tk.TclError:pass
            self._queue_refresh_id=None
        after_id=getattr(self,"_poll_after_id",None)
        if after_id:
            try:self.root.after_cancel(after_id)
            except tk.TclError:pass
            self._poll_after_id=None
        self.root.destroy()

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
        compositions=sorted(
            folder.glob("*.edl.json"),
            key=lambda item:item.stat().st_mtime,
            reverse=True,
        ) if folder.exists() else []
        if compositions:
            chosen=compositions[0]
            if len(compositions)>1:
                selected=filedialog.askopenfilename(
                    title="Choose a composition to review",
                    initialdir=str(folder),
                    filetypes=[("ClipForge composition EDL","*.edl.json")],
                )
                if not selected:
                    return
                chosen=Path(selected)
            args=([sys.executable,"--composition-review","--edl",str(chosen)]
                  if getattr(sys,"frozen",False)
                  else [sys.executable,"-m","clipforge.composition_review","--edl",str(chosen)])
            try:
                silent_popen(args,cwd=str(ROOT))
                self.log("Multi-segment Composition Review Studio opened.")
            except OSError as exc:
                messagebox.showerror("Composition Review launch failed",str(exc))
            return
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
        args=([sys.executable,"--review-editor"] if getattr(sys,"frozen",False)
              else [sys.executable,"-m","clipforge.review_editor"])
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

def main():
    if "--composition-review" in sys.argv:
        from clipforge.composition_review import main as review_main
        sys.argv=[sys.argv[0]]+[arg for arg in sys.argv[1:] if arg!="--composition-review"]
        review_main()
        return
    if "--review-editor" in sys.argv:
        from clipforge.review_editor import main as editor_main
        sys.argv=[sys.argv[0]]+[arg for arg in sys.argv[1:] if arg!="--review-editor"]
        editor_main()
        return
    ClipForge().root.mainloop()

if __name__=="__main__":
    main()
