"""VAW ClipForge v0.5 Review & Timeline Editor, local desktop tool."""
from __future__ import annotations
import argparse
import copy
import os
import queue
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from clipforge.vanitas_widgets import VanitasCombo, VanitasScrollbar, VanitasEntry, VanitasButton, VanitasSlider, load_brand_fonts

import cv2
from PIL import Image, ImageDraw, ImageFont, ImageTk

from clipforge.review_core import load_clip, focus_x, focus_center, crop_width, export_review, save_draft
from clipforge.subtitle_presets import PRESETS, choose, preview_image
from audio_preview import AudioPreview
from clipforge.subject_tracking import track_subject

ROOT=Path(__file__).resolve().parent.parent
COLORS={"bg":"#05070B","panel":"#101827","surface":"#172235",
        "text":"#DCE6F5","sub":"#8E9DB4","red":"#075BFF",
        "blue":"#075BFF","yellow":"#20BFFF","line":"#29364B"}
DEFAULT_CLIP=ROOT/"exports"/"videoplayback"/"videoplayback_v04_01_00243s_rev3.mp4"

class ReviewEditor:
    def __init__(self,clip=None):
        load_brand_fonts()
        self.app=tk.Tk()
        self.app.title("VAW ClipForge v0.7 | Universal Object Review")
        self.app.configure(bg=COLORS["bg"])
        self.app.geometry("1360x940")
        self.app.minsize(1180,820)
        self.data=None
        self.capture=None
        self.playing=False
        self.position=tk.DoubleVar(value=0.0)
        self.focus=tk.DoubleVar(value=50.0)
        self.style=tk.StringVar(value="karaoke")
        self.audio=AudioPreview()
        self.selecting_subject=False
        self.drag_start=None
        self.drag_shape=None
        self.subject_x=0.5
        self.subject_y=0.5
        self.gallery_images=[]
        self.app.protocol("WM_DELETE_WINDOW",self.on_close)
        self.caption_index=None
        self.pending_focus=None
        self.last_render=None
        self.in_scrub=False
        self.messages=queue.Queue()
        self.busy=False
        self.build()
        self.app.after(180,self.poll)
        self.app.after(400,lambda:self.open_file(str(clip) if clip else None,first=True))

    def label(self,parent,text,size=10,color="text",bold=False,**kw):
        font=("Archivo",size,"bold" if bold else "normal")
        return tk.Label(parent,text=text,font=font,bg=COLORS["bg"],fg=COLORS[color],
                        **kw)

    def btn(self,parent,text,command,important=False):
        return VanitasButton(parent,text=text,command=command,primary=important,
                             font=("Archivo",10,"bold"),padx=13,pady=8)

    def build(self):
        header=tk.Frame(self.app,bg=COLORS["bg"])
        header.pack(fill="x",padx=21,pady=(14,9))
        self.label(header,"VAW / REVIEW STUDIO",18,bold=True).pack(side="left")
        self.btn(header,"Open Clip",self.browse).pack(side="right",padx=(7,0))
        self.btn(header,"Open Exports",self.open_exports).pack(side="right",padx=(7,0))
        self.save_btn=self.btn(header,"Save Draft",self.save)
        self.save_btn.pack(side="right",padx=(7,0))
        self.export_btn=self.btn(header,"EXPORT EDITED MP4",self.export,important=True)
        self.export_btn.pack(side="right",padx=(7,0))
        self.file_label=self.label(self.app,"Open a v0.4 ClipForge MP4 with its v04-manifest.json",
                                   10,"sub",anchor="w")
        self.file_label.pack(fill="x",padx=22)

        body=tk.Frame(self.app,bg=COLORS["bg"])
        body.pack(fill="both",expand=True,padx=20,pady=7)
        left=tk.Frame(body,bg=COLORS["bg"],width=760)
        left.pack(side="left",fill="both",expand=True,padx=(0,15))
        right=tk.Frame(body,bg=COLORS["bg"],width=480)
        right.pack(side="left",fill="both",expand=False)
        right.pack_propagate(False)

        visuals=tk.Frame(left,bg=COLORS["bg"])
        visuals.pack(fill="x")
        large=tk.Frame(visuals,bg=COLORS["bg"])
        large.pack(side="left",anchor="n")
        self.label(large,"PORTRAIT CROP PREVIEW",10,"sub",bold=True).pack(anchor="w")
        self.portrait=tk.Canvas(large,width=252,height=448,bg="#0b0d14",
                                highlightbackground=COLORS["line"],highlightthickness=1)
        self.portrait.pack(pady=(6,0))
        self.portrait_photo=None
        info=tk.Frame(visuals,bg=COLORS["bg"])
        info.pack(side="left",fill="x",anchor="n",padx=(17,0))
        self.label(info,"SOURCE FRAME (click focus / drag to track object)",10,"sub",bold=True).pack(anchor="w")
        self.source_preview=tk.Canvas(info,width=450,height=255,bg="#080b11",
                                      highlightbackground=COLORS["line"],highlightthickness=1,
                                      cursor="crosshair")
        self.source_preview.pack(pady=(6,14))
        self.source_preview.bind("<ButtonPress-1>",self.selection_start)
        self.source_preview.bind("<B1-Motion>",self.selection_drag)
        self.source_preview.bind("<ButtonRelease-1>",self.selection_end)
        self.source_photo=None
        self.label(info,"Focus position  •  LEFT  ←  →  RIGHT",10,"sub").pack(anchor="w")
        self.focus_control=VanitasSlider(info,variable=self.focus,from_=0,to=100,resolution=0.2,
                                         command=self.focus_changed,length=440,
                                         showvalue=True,bg=COLORS["bg"],
                                         activebackground=COLORS["blue"],
                                         troughcolor=COLORS["surface"])
        self.focus_control.pack(anchor="w")
        trackbuttons=tk.Frame(info,bg=COLORS["bg"])
        trackbuttons.pack(anchor="w",pady=(4,0))
        self.btn(trackbuttons,"Pin Keyframe",self.pin_focus,True).pack(side="left")
        self.subject_btn=self.btn(trackbuttons,"Track Any Object",self.arm_subject)
        self.subject_btn.pack(side="left",padx=6)
        self.btn(trackbuttons,"Clear Tracks",self.clear_tracks).pack(side="left")
        self.label(info,"Keyframes adjust framing near selected moments;\n"
                        "automatic tracking remains elsewhere.",9,"sub",
                        justify="left").pack(anchor="w",pady=(9,0))

        controls=tk.Frame(left,bg=COLORS["bg"])
        controls.pack(fill="x",pady=(8,5))
        self.play_btn=self.btn(controls,"Play with Audio",self.toggle_play)
        self.play_btn.pack(side="left",padx=(0,9))
        self.time_label=self.label(controls,"00:00 / 00:30",11,bold=True)
        self.time_label.pack(side="left")
        self.label(controls,"Audio clock preview - near-real-time sync",9,"sub").pack(side="right")
        self.scale=VanitasSlider(left,variable=self.position,from_=0,to=30,
                                 resolution=0.1,command=self.scrub,length=710,
                                 showvalue=False,bg=COLORS["bg"],
                                 troughcolor=COLORS["surface"],
                                 activebackground=COLORS["blue"])
        self.scale.pack(fill="x",pady=(0,4))
        self.timeline=tk.Canvas(left,height=70,bg=COLORS["panel"],highlightthickness=0,
                                cursor="hand2")
        self.timeline.pack(fill="x")
        self.timeline.bind("<Button-1>",self.click_timeline)
        self.timeline.bind("<Configure>",lambda _:self.draw_timeline())
        scenecontrols=tk.Frame(left,bg=COLORS["bg"])
        scenecontrols.pack(fill="x",pady=(4,0))
        self.label(scenecontrols,"SCENE CUTS / TRANSITIONS",9,"sub",bold=True).pack(side="left")
        self.btn(scenecontrols,"Edit transitions",self.open_scene_editor).pack(side="left",padx=12)
        self.label(left,"Blue = scene | Pink = caption | Yellow = focus | Purple = dip",
                   9,"sub").pack(anchor="w",pady=(5,0))

        self.label(left,"MANUAL FOCUS KEYFRAMES",10,"sub",bold=True).pack(anchor="w",pady=(8,4))
        keybar=tk.Frame(left,bg=COLORS["bg"])
        keybar.pack(fill="x")
        self.keys=ttk.Treeview(keybar,columns=("time","focus"),show="headings",height=3)
        self.keys.heading("time",text="Time (s)")
        self.keys.heading("focus",text="Horizontal focus (%)")
        self.keys.column("time",width=88,anchor="center")
        self.keys.column("focus",width=200,anchor="center")
        self.keys.pack(side="left",fill="x",expand=True)
        self.btn(keybar,"Delete Selected",self.remove_focus).pack(side="left",padx=8)
        self.btn(keybar,"Reset All",self.reset_focus).pack(side="left")
        self.keys.bind("<Double-1>",self.jump_keyframe)

        self.label(right,"CAPTION TIMELINE",12,bold=True).pack(anchor="w")
        self.label(right,"Select a line → correct text/time → Apply Line",
                   9,"sub").pack(anchor="w",pady=(3,9))
        caption_panel=tk.Frame(right,bg=COLORS["bg"])
        caption_panel.pack(fill="both",expand=True)
        self.subtitles=ttk.Treeview(caption_panel,columns=("start","end","text"),
                                   show="headings",height=13)
        for name,width in (("start",68),("end",68),("text",312)):
            self.subtitles.heading(name,text=name.upper())
            self.subtitles.column(name,width=width,anchor="w")
        caption_scroll=VanitasScrollbar(caption_panel,orient="vertical",command=self.subtitles.yview)
        self.subtitles.configure(yscrollcommand=caption_scroll.set)
        self.subtitles.pack(side="left",fill="both",expand=True)
        caption_scroll.pack(side="right",fill="y")
        self.subtitles.bind("<<TreeviewSelect>>",self.select_caption)
        editrow=tk.Frame(right,bg=COLORS["bg"])
        editrow.pack(fill="x",pady=(12,4))
        self.label(editrow,"START",9,"sub").pack(side="left")
        self.start_var=tk.StringVar()
        self.start_entry=self.entry(editrow,self.start_var,7)
        self.start_entry.pack(side="left",padx=(6,12))
        self.label(editrow,"END",9,"sub").pack(side="left")
        self.end_var=tk.StringVar()
        self.end_entry=self.entry(editrow,self.end_var,7)
        self.end_entry.pack(side="left",padx=(6,10))
        self.label(editrow,"sec",9,"sub").pack(side="left")
        self.caption_text=tk.Text(right,height=3,wrap="word",bg=COLORS["panel"],
                                  fg=COLORS["text"],insertbackground="white",
                                  font=("Archivo",11),relief="flat",padx=10,pady=8)
        self.caption_text.pack(fill="x")
        caprow=tk.Frame(right,bg=COLORS["bg"])
        caprow.pack(fill="x",pady=(8,0))
        self.btn(caprow,"Apply Line",self.apply_caption,True).pack(side="left")
        self.btn(caprow,"Add Line",self.add_caption).pack(side="left",padx=6)
        self.btn(caprow,"Delete",self.delete_caption).pack(side="left")
        stylerow=tk.Frame(right,bg=COLORS["bg"])
        stylerow.pack(fill="x",pady=(18,9))
        self.label(stylerow,"CAPTION STYLE",10,"sub",bold=True).pack(side="left",padx=(0,10))
        self.style_picker=VanitasCombo(stylerow,textvariable=self.style,state="readonly",
                     values=tuple(p.id for p in PRESETS),width=13)
        self.style_picker.pack(side="left")
        self.style_picker.bind("<<ComboboxSelected>>",lambda e:self.update_frame())
        self.btn(stylerow,"Browse Styles",self.open_style_gallery).pack(side="left",padx=8)
        self.label(right,"Choose from six caption presets. Edited words use\n"
                         "approximate timing; verify the final video before posting.",
                   9,"sub",justify="left").pack(anchor="w")

        self.status=tk.StringVar(value="Ready. No files will be modified until you export.")
        statusbar=tk.Frame(self.app,bg=COLORS["bg"])
        statusbar.pack(fill="x",padx=21,pady=(3,12))
        self.label(statusbar,"●",12,"red").pack(side="left")
        tk.Label(statusbar,textvariable=self.status,anchor="w",bg=COLORS["bg"],
                 fg=COLORS["sub"],font=("Archivo",10)).pack(side="left",padx=7)

        style=ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",background=COLORS["panel"],
                        foreground=COLORS["text"],fieldbackground=COLORS["panel"],
                        rowheight=26,borderwidth=0,font=("Archivo",9))
        style.configure("Treeview.Heading",background=COLORS["surface"],
                        foreground=COLORS["text"],font=("Archivo",9))
        style.map("Treeview",background=[("selected",COLORS["red"])])
        style.configure("TCombobox",fieldbackground=COLORS["surface"])

    def entry(self,parent,var,width=8):
        return VanitasEntry(parent,textvariable=var,width=width,
                            bg=COLORS["surface"],fg=COLORS["text"],
                            insertbackground="white",font=("Archivo",11))

    def browse(self):
        path=filedialog.askopenfilename(title="Open ClipForge v0.4 export",
              filetypes=[("MP4 video","*.mp4")])
        if path:self.open_file(path)
    def open_file(self,filename=None,first=False):
        filename=filename or (str(DEFAULT_CLIP) if DEFAULT_CLIP.exists() else None)
        if not filename and first:
            self.status.set("Use Open Clip to select a v0.4 MP4 export.")
            return
        try:
            data=load_clip(filename)
            if self.capture:self.capture.release()
            cap=cv2.VideoCapture(data["source"])
            if not cap.isOpened():raise RuntimeError("Cannot open original footage.")
            self.data=data;self.capture=cap
            self.position.set(0)
            self.scale.configure(to=data["duration"])
            self.style.set(data["caption_style"])
            self.audio.load(data["source"],data["source_start"],data["duration"])
            self.playing=False;self.play_btn.configure(text="Play with Audio")
            self.pending_focus=None
            self.file_label.configure(text=Path(data["clip"]).name+"  ·  original: "+Path(data["source"]).name)
            self.refresh_captions()
            self.refresh_keys()
            self.update_frame()
            self.draw_timeline()
            self.status.set("Loaded "+Path(filename).name+"; edits are non-destructive.")
        except Exception as exc:
            self.status.set("Open failed: "+str(exc)[:120])
            if not first:messagebox.showerror("Open error",str(exc))

    def sec_label(self,t):
        t=max(0,float(t))
        return f"{int(t//60):02}:{int(t%60):02}.{int((t%1)*10)}"

    def frame_at(self,t):
        self.capture.set(cv2.CAP_PROP_POS_MSEC,(self.data["source_start"]+t)*1000)
        ok,frame=self.capture.read()
        return frame if ok else None

    def current_caption(self,t):
        if not self.data:return ""
        for row in self.data["subtitles"]:
            if row["start"]<=t<row["end"]:
                return row["text"]
        return ""

    def update_frame(self):
        if not self.data or not self.capture:return
        t=min(float(self.position.get()),float(self.data["duration"])-0.02)
        frame=self.frame_at(t)
        if frame is None:
            self.status.set("Preview frame unavailable at this timestamp.")
            return
        h,w=frame.shape[:2]
        cw=crop_width(self.data)
        center=self.pending_focus*w if self.pending_focus is not None else focus_center(self.data,t)
        x=int(max(0,min(w-cw,center-cw/2)))
        x-=x%2
        frame_rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
        original=Image.fromarray(frame_rgb).resize((450,255),Image.Resampling.LANCZOS)
        overlay=ImageDraw.Draw(original)
        x1=round(x*450/w);x2=round((x+cw)*450/w)
        overlay.rectangle((x1,0,x2,254),outline="#ee5261",width=3)
        overlay.text((10,10),f"Source {w}x{h} • crop {cw}px",fill="white",stroke_width=2,
                     stroke_fill="black")
        self.source_photo=ImageTk.PhotoImage(original)
        self.source_preview.delete("all")
        self.source_preview.create_image(0,0,image=self.source_photo,anchor="nw")
        cropped=Image.fromarray(frame_rgb[:,x:x+cw]).resize((252,448),Image.Resampling.LANCZOS)
        msg=self.current_caption(t)
        if msg:
            self.paint_caption(cropped,msg,t)
        self.portrait_photo=ImageTk.PhotoImage(cropped)
        self.portrait.delete("all")
        self.portrait.create_image(0,0,image=self.portrait_photo,anchor="nw")
        self.time_label.configure(text=f"{self.sec_label(t)} / {self.sec_label(self.data['duration'])}")
        self.in_scrub=True
        self.focus.set(round(100*center/w,1))
        self.in_scrub=False
        self.draw_timeline()

    def paint_caption(self,image,text,t):
        draw=ImageDraw.Draw(image)
        font_path="C:/Windows/Fonts/segoeuib.ttf"
        font=ImageFont.truetype(font_path,18) if Path(font_path).exists() else ImageFont.load_default()
        preset=choose(self.style.get())
        words=text.upper().split() if preset.uppercase else text.split()
        active=0
        for row in self.data["subtitles"]:
            if row["start"]<=t<row["end"] and row["text"]==text:
                progress=(t-row["start"])/max(.05,row["end"]-row["start"])
                active=min(len(words)-1,max(0,int(progress*len(words))))
                break
        lines=[];line=[];length=0
        for i,word in enumerate(words):
            if line and length+len(word)+1>23:
                lines.append(line);line=[];length=0
            line.append((i,word))
            length+=len(word)+1
        if line:lines.append(line)
        shown=lines[:3]
        for rowidx,row in enumerate(shown):
            widths=[draw.textlength(word+" ",font=font) for _,word in row]
            x=(252-sum(widths))/2
            y=350+28*rowidx-(len(shown)-1)*12
            for (index,word),width in zip(row,widths):
                is_active=(index==active and preset.animated)
                draw.text((x,y),word,font=font,
                          fill=preset.accent if is_active else preset.white,
                          stroke_width=2,stroke_fill="#06080b")
                x+=width

    def scrub(self,_=None):
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

    def focus_changed(self,_=None):
        if not self.data or self.in_scrub:return
        self.pending_focus=float(self.focus.get())/100
        self.update_frame()
    def selection_start(self,event):
        if not self.data:return
        self.drag_start=(max(0,min(450,event.x)),max(0,min(255,event.y)))

    def selection_drag(self,event):
        if not self.data or not self.selecting_subject or self.drag_start is None:return
        if self.drag_shape is not None:
            self.source_preview.delete(self.drag_shape)
        x,y=self.drag_start
        ex=max(0,min(450,event.x));ey=max(0,min(255,event.y))
        self.drag_shape=self.source_preview.create_rectangle(
            x,y,ex,ey,outline="#FF5970",width=3,dash=(7,3))

    def selection_end(self,event):
        if not self.data or self.drag_start is None:return
        x0,y0=self.drag_start
        x1=max(0,min(450,event.x));y1=max(0,min(255,event.y))
        self.drag_start=None
        if self.drag_shape is not None:
            self.source_preview.delete(self.drag_shape)
            self.drag_shape=None
        if self.selecting_subject:
            self.selecting_subject=False
            self.subject_btn.configure(text="Track Any Object")
            center_x=(x0+x1)/900
            center_y=(y0+y1)/510
            region=(min(x0,x1)/450,min(y0,y1)/255,
                    max(x0,x1)/450,max(y0,y1)/255)
            self.track_clicked(center_x,center_y,bbox=region)
        else:
            self.click_focus(event)

    def click_focus(self,event):
        if not self.data:return
        value=max(0,min(100,event.x/450*100))
        self.focus.set(value)
        self.pending_focus=value/100
        self.update_frame()
    def pin_focus(self):
        if not self.data:return
        t=round(float(self.position.get()),2)
        center=float(self.focus.get())/100
        frames=self.data["keyframes"]
        frames[:]=[k for k in frames if abs(float(k["time"])-t)>0.15]
        frames.append({"time":t,"center":round(center,4)})
        frames.sort(key=lambda x:x["time"])
        self.pending_focus=None
        self.refresh_keys();self.update_frame()
        self.status.set(f"Framing pinned at {t:.2f}s. Save or export to keep.")
    def remove_focus(self):
        if not self.data:return
        selection=self.keys.selection()
        if not selection:return
        idx=int(selection[0])
        del self.data["keyframes"][idx]
        self.refresh_keys();self.update_frame()
    def reset_focus(self):
        if not self.data:return
        self.data["keyframes"]=[]
        self.refresh_keys();self.update_frame()
    def refresh_keys(self):
        for row in self.keys.get_children():self.keys.delete(row)
        if not self.data:return
        for idx,k in enumerate(self.data["keyframes"]):
            self.keys.insert("","end",iid=str(idx),values=(f"{k['time']:.2f}",f"{k['center']*100:.1f}%"))
        self.draw_timeline()
    def jump_keyframe(self,_=None):
        sel=self.keys.selection()
        if sel:
            idx=int(sel[0])
            self.position.set(self.data["keyframes"][idx]["time"])
            self.scrub()

    def refresh_captions(self,selected=None):
        for row in self.subtitles.get_children():self.subtitles.delete(row)
        if not self.data:return
        for idx,c in enumerate(self.data["subtitles"]):
            self.subtitles.insert("","end",iid=str(idx),
                 values=(f"{c['start']:.2f}",f"{c['end']:.2f}",c["text"]))
        if selected is not None and str(selected) in self.subtitles.get_children():
            self.subtitles.selection_set(str(selected))
            self.subtitles.see(str(selected))
    def select_caption(self,_=None):
        sel=self.subtitles.selection()
        if not sel or not self.data:return
        idx=int(sel[0]);self.caption_index=idx
        item=self.data["subtitles"][idx]
        self.start_var.set(f"{item['start']:.2f}")
        self.end_var.set(f"{item['end']:.2f}")
        self.caption_text.delete("1.0","end")
        self.caption_text.insert("1.0",item["text"])
        self.position.set(item["start"]);self.scrub()

    def apply_caption(self):
        if not self.data or self.caption_index is None:return
        try:
            start=float(self.start_var.get())
            end=float(self.end_var.get())
            text=self.caption_text.get("1.0","end").strip().replace("\n"," ")
            if start<0 or end>self.data["duration"]+0.05 or end<=start or not text:
                raise ValueError("Caption range/text invalid")
            if len(text)>200:raise ValueError("Caption too long")
            old=self.data["subtitles"][self.caption_index]
            old.update({"start":start,"end":end,"text":text})
            self.data["subtitles"].sort(key=lambda x:x["start"])
            idx=self.data["subtitles"].index(old)
            self.refresh_captions(idx);self.update_frame()
            self.status.set(f"Caption {idx+1} updated in editor (not yet exported).")
        except Exception as exc:messagebox.showerror("Caption error",str(exc))

    def add_caption(self):
        if not self.data:return
        at=float(self.position.get())
        dur=float(self.data["duration"])
        end=min(dur,at+1.2)
        if end<=at:return
        self.data["subtitles"].append({"start":at,"end":end,"text":"Edit this caption"})
        self.data["subtitles"].sort(key=lambda x:x["start"])
        idx=next(i for i,c in enumerate(self.data["subtitles"]) if c["text"]=="Edit this caption")
        self.refresh_captions(idx)
    def delete_caption(self):
        if not self.data or self.caption_index is None:return
        del self.data["subtitles"][self.caption_index]
        self.caption_index=None
        self.refresh_captions()
        self.caption_text.delete("1.0","end")
        self.draw_timeline()

    def click_timeline(self,event):
        if not self.data:return
        width=max(1,self.timeline.winfo_width()-24)
        t=max(0,min(self.data["duration"],(event.x-12)/width*self.data["duration"]))
        self.position.set(round(t,2));self.scrub()
    def draw_timeline(self):
        can=self.timeline
        can.delete("all")
        if not self.data:return
        w=max(60,can.winfo_width()-24)
        dur=self.data["duration"]
        can.create_line(12,36,12+w,36,fill=COLORS["line"],width=5)
        for t in self.data["cuts"]:
            if 0<=t<=dur:
                x=12+w*t/dur
                mode=self.data.get("transitions",{}).get(f"{float(t):.2f}","hard")
                can.create_line(x,9,x,61,fill="#ad70f1" if mode=="dip" else COLORS["blue"],width=2)
        for row in self.data["subtitles"]:
            t=row["start"]
            if 0<=t<=dur:
                x=12+w*t/dur
                can.create_line(x,29,x,44,fill=COLORS["red"],width=2)
        for key in self.data["keyframes"]:
            x=12+w*key["time"]/dur
            can.create_oval(x-4,15,x+4,23,fill=COLORS["yellow"],outline="")
        at=self.position.get()
        x=12+w*at/dur
        can.create_line(x,4,x,65,fill="white",width=2)
        can.create_text(16,8,text="0s",anchor="nw",fill=COLORS["sub"])
        can.create_text(12+w-6,8,text=f"{int(dur)}s",anchor="ne",fill=COLORS["sub"])

    def on_close(self):
        self.playing=False
        self.audio.close()
        if self.capture:self.capture.release()
        self.app.destroy()

    def arm_subject(self):
        if not self.data or self.busy:return
        self.selecting_subject=not self.selecting_subject
        self.subject_btn.configure(text="DRAG BOX NOW" if self.selecting_subject else "Track Any Object")
        self.status.set("Drag a box around ANY character, icon, vehicle, map or diagram; release to track.")

    def track_clicked(self,x,y,bbox=None):
        self.busy=True
        at=float(self.position.get())
        self.status.set("Analyzing subject motion near "+self.sec_label(at)+"...")
        data=copy.deepcopy(self.data)
        def worker():
            try:
                track=track_subject(data["source"],data["source_start"],at,
                    data["duration"],x,y,data.get("cuts",[]),seconds=8,bbox=bbox)
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
            VanitasCombo(row,textvariable=variable,state="readonly",
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
        self.label(dialog,"Hard = instant cut. Dip = brief brightness fade at cut.\n"
                         "Audio remains continuous. Preview rendered MP4 for timing.",
                   9,"sub",justify="left").pack(pady=(0,10))

    def open_style_gallery(self):
        dialog=tk.Toplevel(self.app)
        dialog.title("Subtitle Modes | ClipForge v0.6")
        dialog.geometry("810x610")
        dialog.configure(bg=COLORS["bg"])
        self.label(dialog,"CHOOSE A SUBTITLE MODE",18,bold=True).pack(anchor="w",padx=18,pady=(16,4))
        self.label(dialog,"Visual presets for 9:16 Shorts | click a card to apply",10,"sub").pack(anchor="w",padx=18,pady=(0,14))
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
            tk.Label(card,text=preset.name,font=("Archivo",11),
                     bg=COLORS["panel"],fg=COLORS["text"],
                     anchor="w").pack(fill="x",pady=(6,0))
            tk.Label(card,text=preset.sub,font=("Archivo",9),
                     bg=COLORS["panel"],fg=COLORS["sub"],
                     anchor="w").pack(fill="x")
            def choose_style(style=preset.id):
                self.style.set(style)
                self.update_frame()
                self.status.set("Subtitle preset: "+choose(style).name)
                dialog.destroy()
            button.configure(command=choose_style)
        dialog._photos=photos
        self.label(dialog,"Rendered captions use a safe bottom region (720x1280).",
                   10,"sub").pack(anchor="w",padx=20,pady=(4,14))

    def save(self):
        if not self.data:return
        self.data["caption_style"]=self.style.get()
        try:
            file=save_draft(self.data)
            self.status.set("Draft saved: "+file.name)
        except Exception as exc:messagebox.showerror("Save error",str(exc))

    def export(self):
        if not self.data or self.busy:return
        self.data["caption_style"]=self.style.get()
        snapshot=copy.deepcopy(self.data)
        self.busy=True
        self.export_btn.configure(state="disabled")
        self.status.set("Rendering from original footage...")
        def job():
            try:
                target=export_review(snapshot,log=lambda msg:self.messages.put(("log",msg)))
                self.messages.put(("done",str(target)))
            except Exception as exc:
                self.messages.put(("error",str(exc)))
        threading.Thread(target=job,daemon=True).start()
    def poll(self):
        try:
            while True:
                kind,val=self.messages.get_nowait()
                if kind=="log":self.status.set(val)
                elif kind=="subject":
                    self.busy=False
                    self.data.setdefault("subject_tracks",[]).append(val)
                    self.update_frame()
                    self.status.set(f"Subject tracked for {val['end']-val['start']:.1f}s. Save draft or export.")
                elif kind=="subject_error":
                    self.busy=False
                    self.status.set("Subject tracking failed: "+val[:110])
                    messagebox.showwarning("Subject tracking",val)
                else:
                    self.busy=False
                    self.export_btn.configure(state="normal")
                    if kind=="done":
                        self.last_render=Path(val)
                        self.status.set("Export successful: "+self.last_render.name)
                        if messagebox.askyesno("Export ready",
                                              "Edited MP4 saved as a new file. Open video preview?"):
                            os.startfile(str(self.last_render))
                    else:
                        self.status.set("Export failed: "+val[:130])
                        messagebox.showerror("Export failed",val)
        except queue.Empty:pass
        self.app.after(180,self.poll)
    def open_exports(self):
        if not self.data:return
        os.startfile(str(Path(self.data["clip"]).parent))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clip")
    args=parser.parse_args()
    editor=ReviewEditor(args.clip)
    editor.app.mainloop()

if __name__=="__main__":main()
