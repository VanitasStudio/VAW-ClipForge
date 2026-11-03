"""Non-destructive multi-segment Review Studio for Story Composer EDLs."""
from __future__ import annotations

import argparse
import json
import tkinter as tk
import cv2
from PIL import Image, ImageTk
from dataclasses import replace
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from vanitas_widgets import VanitasCombo, VanitasEntry, VanitasButton, VanitasCheckbutton, load_brand_fonts

from clipforge_contracts import (
    AnalysisBundle, AudioContinuity, AudioPlan, CaptionPlan, CompositionSegment,
    EditorialEvent,
    CompositionStrategy, EditDecisionList, MediaSource, RenderSettings,
    SceneSpan, SegmentRole, TranscriptSpan, TransitionKind, TransitionSpec,
    validate_edl,
)
from composition_renderer import render_composition
from unified_analyzer import probe_source


def load_bundle(path: str | Path) -> AnalysisBundle:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    source = MediaSource(**data["source"])
    transcript = tuple(TranscriptSpan(**row) for row in data.get("transcript", []))
    scenes = tuple(SceneSpan(
        **{**row, "visual_tags": tuple(row.get("visual_tags", []))}
    ) for row in data.get("scenes", []))
    events = []
    for row in data.get("events", []):
        values = dict(row)
        values["role"] = SegmentRole(values.get("role", "support"))
        for field in (
            "tags", "requires_event_ids", "supports_event_ids",
            "contradicts_event_ids", "visual_evidence_seconds",
        ):
            values[field] = tuple(values.get(field, []))
        events.append(EditorialEvent(**values))
    return AnalysisBundle(
        bundle_id=data["bundle_id"],
        source=source,
        transcript=transcript,
        scenes=scenes,
        events=tuple(events),
        analysis_version=data.get("analysis_version", "1.2.0"),
        created_at=data.get("created_at", ""),
        warnings=tuple(data.get("warnings", [])),
        composition_orders={
            key: tuple(value) for key, value in data.get("composition_orders", {}).items()
        },
        event_roles=data.get("event_roles", {}),
        event_dependencies={
            key: tuple(value) for key, value in data.get("event_dependencies", {}).items()
        },
    )


def load_edl(path: str | Path) -> EditDecisionList:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    segments = tuple(
        CompositionSegment(
            **{**row, "role": SegmentRole(row.get("role", "support")),
               "event_ids": tuple(row.get("event_ids", []))}
        )
        for row in data.get("segments", [])
    )
    transitions = tuple(
        TransitionSpec(
            **{**row, "kind": TransitionKind(row.get("kind", "hard_cut"))}
        )
        for row in data.get("transitions", [])
    )
    return EditDecisionList(
        edl_id=data["edl_id"],
        source_id=data["source_id"],
        composition_id=data["composition_id"],
        strategy=CompositionStrategy(data["strategy"]),
        title=data["title"],
        segments=segments,
        transitions=transitions,
        audio=AudioPlan(**{
            **data.get("audio", {}),
            "continuity": AudioContinuity(data.get("audio", {}).get("continuity", "smart")),
        }),
        captions=CaptionPlan(**data.get("captions", {})),
        render=RenderSettings(**data.get("render", {})),
        schema_version=data.get("schema_version", "1.0"),
        created_at=data.get("created_at", ""),
        target_duration_seconds=float(data.get("target_duration_seconds", 60)),
    )


class CompositionReview:
    def __init__(self, edl_path: str | Path):
        load_brand_fonts()
        self.edl_path = Path(edl_path).resolve()
        self.manifest_path = self.edl_path.with_name(
            self.edl_path.name.replace(".edl.json", ".composition.json")
        )
        self.analysis_path = self.edl_path.with_name(
            self.edl_path.name.replace(".edl.json", ".analysis.json")
        )
        self.bundle = load_bundle(self.analysis_path)
        self.edl = load_edl(self.edl_path)
        fresh = probe_source(self.bundle.source.path)
        if fresh.source_id != self.bundle.source.source_id:
            raise RuntimeError(
                "The original source file has changed since this composition was created. "
                "Re-analyze the source before editing or rendering."
            )

        self.root = tk.Tk()
        self.root.title("VAW ClipForge — Composition Review Studio")
        self.root.geometry("1180x850")
        self.root.minsize(1020, 760)
        self.root.configure(bg="#05070B")
        self.selected = 0
        self.caption_span_id = None
        self.visible_caption_ids = []
        self.preview_photo = None
        self.start_var = tk.StringVar()
        self.end_var = tk.StringVar()
        self.role_var = tk.StringVar()
        self.transition_var = tk.StringVar(value="hard_cut")
        self.caption_var = tk.StringVar()
        self.caption_enabled_var = tk.BooleanVar(value=self.edl.captions.enabled)
        self.caption_burn_var = tk.BooleanVar(value=self.edl.captions.burn_in)
        self.caption_srt_var = tk.BooleanVar(value=self.edl.captions.export_srt)
        self.caption_upper_var = tk.BooleanVar(value=self.edl.captions.uppercase)
        self.caption_style_var = tk.StringVar(value=self.edl.captions.preset_id)
        self.audio_crossfade_var = tk.BooleanVar(value=self.edl.audio.allow_crossfade)
        self.title_var = tk.StringVar(value=self.edl.title)
        self.target_var = tk.StringVar(value=str(round(self.edl.target_duration_seconds)))
        self.status_var = tk.StringVar(value="Review the segment order and source ranges. The original video is never modified.")
        self._build_ui()
        self._refresh_list()
        self._select(0)

    def _build_ui(self):
        bg, card, white, muted = "#05070B", "#101827", "#DCE6F5", "#8793A3"
        header = tk.Frame(self.root, bg=bg)
        header.pack(fill="x", padx=20, pady=(16, 8))
        tk.Label(
            header, text=self.edl.title, bg=bg, fg=white,
            font=("Archivo", 20),
        ).pack(side="left")
        tk.Label(
            header, text=f"{self.edl.strategy.value.replace('_', ' ').title()}",
            bg="#172235", fg="#DCE6F5", padx=10, pady=5,
            font=("Archivo", 9),
        ).pack(side="right")

        body = tk.Frame(self.root, bg=bg)
        body.pack(fill="both", expand=True, padx=20, pady=8)
        left = tk.Frame(body, bg=card, highlightbackground="#29364B", highlightthickness=1)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))
        right = tk.Frame(body, bg=card, highlightbackground="#29364B", highlightthickness=1)
        right.pack(side="right", fill="y", padx=(10, 0))

        tk.Label(left, text="COMPOSITION TIMELINE", bg=card, fg=muted,
                 font=("Archivo", 9)).pack(anchor="w", padx=14, pady=(12, 6))
        self.timeline_canvas=tk.Canvas(left,height=96,bg="#0B111C",highlightthickness=0)
        self.timeline_canvas.pack(fill="x",padx=12,pady=(0,8))
        self.timeline_canvas.bind("<Button-1>",self._timeline_click)
        self.timeline_canvas.bind("<Configure>",lambda _event:self._draw_timeline())
        self.listbox = tk.Listbox(
            left, bg="#0B111C", fg=white, selectbackground="#075BFF",
            selectforeground=white, relief="flat", bd=0,
            font=("Consolas", 10), activestyle="none",
        )
        self.listbox.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        buttons = tk.Frame(left, bg=card)
        buttons.pack(fill="x", padx=12, pady=(0, 12))
        self._button(buttons, "Move Up", lambda: self._move(-1)).pack(side="left")
        self._button(buttons, "Move Down", lambda: self._move(1)).pack(side="left", padx=7)
        self._button(buttons, "Apply Segment", self._apply_segment).pack(side="right")

        tk.Label(right, text="SOURCE PREVIEW", bg=card, fg=muted,
                 font=("Archivo", 9)).pack(anchor="w", padx=16, pady=(12, 5))
        self.preview_label=tk.Label(right,bg="#0B111C",fg=muted,text="Select a segment")
        self.preview_label.pack(fill="x",padx=16,pady=(0,10))
        tk.Label(right, text="SEGMENT DETAILS", bg=card, fg=white,
                 font=("Archivo", 11)).pack(anchor="w", padx=16, pady=(4, 8))
        self._field(right, "Source In (seconds)", self.start_var)
        self._field(right, "Source Out (seconds)", self.end_var)
        tk.Label(right, text="Segment Role", bg=card, fg=muted,
                 font=("Archivo", 9)).pack(anchor="w", padx=16, pady=(8, 3))
        VanitasCombo(
            right, textvariable=self.role_var, state="readonly", width=25,
            values=[role.value for role in SegmentRole],
        ).pack(fill="x", padx=16)
        tk.Label(right,text="Transition to next segment",bg=card,fg=muted,
                 font=("Archivo",9)).pack(anchor="w",padx=16,pady=(8,3))
        self.transition_combo=VanitasCombo(
            right,textvariable=self.transition_var,state="readonly",width=25,
            values=["hard_cut","cross_dissolve"],
        )
        self.transition_combo.pack(fill="x",padx=16)
        tk.Label(right,text="CAPTIONS IN THIS SEGMENT",bg=card,fg=muted,
                 font=("Archivo",9)).pack(anchor="w",padx=16,pady=(15,4))
        self.caption_list=tk.Listbox(
            right,height=3,bg="#0B111C",fg=white,selectbackground="#075BFF",
            relief="flat",bd=0,font=("Archivo",8),activestyle="none",
        )
        self.caption_list.pack(fill="x",padx=16)
        self.caption_list.bind("<<ListboxSelect>>",self._on_caption_select)
        VanitasEntry(
            right,textvariable=self.caption_var,bg="#0B111C",fg=white,
            insertbackground="white",font=("Archivo",9),
        ).pack(fill="x",padx=16,pady=(5,4),ipady=6)
        self._button(right,"Apply Caption Text",self._apply_caption).pack(anchor="e",padx=16,pady=(0,8))

        tk.Label(right, text="COMPOSITION SETTINGS", bg=card, fg=white,
                 font=("Archivo", 10)).pack(anchor="w", padx=16, pady=(20, 8))
        self._field(right, "Title", self.title_var)
        self._field(right, "Target Duration (12–180s)", self.target_var)
        tk.Label(right,text="CAPTION EXPORT",bg=card,fg=muted,
                 font=("Archivo",9)).pack(anchor="w",padx=16,pady=(12,3))
        for variable,text in (
            (self.caption_enabled_var,"Enable captions"),
            (self.caption_burn_var,"Burn captions into video"),
            (self.caption_srt_var,"Export editable SRT"),
            (self.caption_upper_var,"Uppercase caption text"),
            (self.audio_crossfade_var,"Smooth audio at segment cuts"),
        ):
            VanitasCheckbutton(
                right,text=text,variable=variable,bg=card,
                fg=white,font=("Archivo",8),
            ).pack(anchor="w",padx=16,pady=2)
        from subtitle_presets import PRESETS
        VanitasCombo(
            right,textvariable=self.caption_style_var,state="readonly",
            values=[preset.id for preset in PRESETS],width=24,
        ).pack(fill="x",padx=16,pady=(4,8))
        tk.Label(
            right,
            text=f"Original source: {Path(self.bundle.source.path).name}\n"
                 f"Current timeline: {self.edl.duration_seconds:.1f}s\n"
                 f"Segments: {len(self.edl.segments)}",
            bg=card, fg=muted, justify="left", font=("Archivo", 9),
        ).pack(anchor="w", padx=16, pady=(12, 14))

        footer = tk.Frame(self.root, bg=bg)
        footer.pack(fill="x", padx=20, pady=(4, 16))
        tk.Label(footer, textvariable=self.status_var, bg=bg, fg=muted,
                 font=("Archivo", 9), anchor="w").pack(side="left", fill="x", expand=True)
        self._button(footer, "Render Revised Composition", self._render, primary=True).pack(side="right")
        self._button(footer, "Save EDL", self._save).pack(side="right", padx=8)

    def _button(self, parent, text, command, primary=False):
        return VanitasButton(parent,text=text,command=command,primary=primary,
                             font=("Archivo",9,"bold"),padx=12,pady=8)

    def _field(self, parent, label, variable):
        tk.Label(parent, text=label, bg="#101827", fg="#8E9DB4",
                 font=("Archivo", 9)).pack(anchor="w", padx=16, pady=(8, 3))
        VanitasEntry(
            parent,textvariable=variable,bg="#0B111C",fg="#DCE6F5",
            insertbackground="white",font=("Archivo",10),
        ).pack(fill="x",padx=16,ipady=7)

    def _refresh_list(self):
        self.listbox.delete(0, "end")
        for index, segment in enumerate(self.edl.segments, 1):
            self.listbox.insert(
                "end",
                f"{index:02d}  {segment.timeline_in:6.1f}s  "
                f"{segment.duration_seconds:5.1f}s  "
                f"{segment.role.value.upper():12s}  {segment.reason[:64]}",
            )
        if self.edl.segments:
            self.listbox.selection_set(min(self.selected, len(self.edl.segments) - 1))
        self._draw_timeline()

    def _draw_timeline(self):
        canvas=self.timeline_canvas
        canvas.delete("all")
        width=max(520,canvas.winfo_width())
        total=max(1.0,self.edl.duration_seconds)
        palette={
            "hook":"#b9475a","context":"#4f78a8","development":"#6573a5",
            "evidence":"#438f8c","payoff":"#8e6db0","bridge":"#8a8051",
            "support":"#536273",
        }
        x=10
        for index,segment in enumerate(self.edl.segments):
            bar_width=max(38,(width-20)*segment.duration_seconds/total)
            color=palette.get(segment.role.value,"#536273")
            outline="#ffffff" if index==self.selected else "#303b4e"
            canvas.create_rectangle(x,27,x+bar_width,72,fill=color,outline=outline,width=2 if index==self.selected else 1)
            canvas.create_text(x+bar_width/2,49,text=f"{index+1} · {segment.role.value}",fill="#ffffff",font=("Archivo",8))
            canvas.create_text(x,15,text=f"{segment.timeline_in:.0f}s",anchor="w",fill="#8793A3",font=("Archivo",7))
            x+=bar_width
        canvas.configure(scrollregion=(0,0,max(width,x+10),96))

    def _timeline_click(self,event):
        total=max(0.001,self.edl.duration_seconds)
        width=max(1,self.timeline_canvas.winfo_width()-20)
        position=max(0.0,min(total,(event.x-10)/width*total))
        for index,segment in enumerate(self.edl.segments):
            if segment.timeline_in <= position <= segment.timeline_out:
                self._select(index)
                break

    def _refresh_captions(self):
        self.caption_list.delete(0,"end")
        self.visible_caption_ids=[]
        if not self.edl.segments:
            return
        segment=self.edl.segments[self.selected]
        for span in self.bundle.transcript:
            if span.start_seconds < segment.source_out and span.end_seconds > segment.source_in:
                self.visible_caption_ids.append(span.span_id)
                self.caption_list.insert(
                    "end",f"{span.start_seconds:.1f}–{span.end_seconds:.1f}s  {span.text[:58]}"
                )
        self.caption_span_id=None
        self.caption_var.set("")
        if self.visible_caption_ids:
            self.caption_list.selection_set(0)
            self._on_caption_select()

    def _select(self, index: int):
        if not 0 <= index < len(self.edl.segments):
            return
        self.selected = index
        segment = self.edl.segments[index]
        self.start_var.set(f"{segment.source_in:.3f}")
        self.end_var.set(f"{segment.source_out:.3f}")
        self.role_var.set(segment.role.value)
        outgoing=next((t for t in self.edl.transitions if t.from_segment_id==segment.segment_id),None)
        self.transition_var.set(outgoing.kind.value if outgoing else "hard_cut")
        self._refresh_list()
        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(index)
        self.listbox.activate(index)
        self._refresh_captions()
        self._update_preview(segment.source_in)

    def _on_select(self, _event=None):
        selection = self.listbox.curselection()
        if selection:
            self._select(int(selection[0]))

    def _reflow(self):
        prior={(item.from_segment_id,item.to_segment_id):item for item in self.edl.transitions}
        timeline = 0.0
        rebuilt = []
        for segment in self.edl.segments:
            rebuilt.append(replace(segment, timeline_in=timeline))
            timeline += segment.duration_seconds
        transitions=[]
        for left,right in zip(rebuilt,rebuilt[1:]):
            old=prior.get((left.segment_id,right.segment_id))
            transitions.append(old or TransitionSpec(
                left.segment_id,right.segment_id,TransitionKind.HARD_CUT
            ))
        self.edl = replace(self.edl,segments=tuple(rebuilt),transitions=tuple(transitions))

    def _apply_transition_value(self):
        segment=self.edl.segments[self.selected]
        next_segment=self.edl.segments[self.selected+1]
        kind=TransitionKind(self.transition_var.get())
        duration=(
            min(0.25,min(segment.duration_seconds,next_segment.duration_seconds)*0.25)
            if kind==TransitionKind.CROSS_DISSOLVE else 0.0
        )
        transitions=list(self.edl.transitions)
        transitions=[t for t in transitions if not (
            t.from_segment_id==segment.segment_id and t.to_segment_id==next_segment.segment_id
        )]
        transitions.append(TransitionSpec(
            segment.segment_id,next_segment.segment_id,kind,duration,
            "Edited in Composition Review Studio",
        ))
        self.edl=replace(self.edl,transitions=tuple(transitions))

    def _apply_segment(self):
        try:
            start, end = float(self.start_var.get()), float(self.end_var.get())
            role = SegmentRole(self.role_var.get())
            if start < 0 or end <= start or end > self.bundle.source.duration_seconds:
                raise ValueError("Source range must be valid and stay inside the original video.")
            segment = replace(
                self.edl.segments[self.selected],
                source_in=start, source_out=end, role=role,
            )
            items = list(self.edl.segments)
            items[self.selected] = segment
            self.edl = replace(self.edl, segments=tuple(items))
            self._reflow()
            if self.selected < len(self.edl.segments)-1:
                self._apply_transition_value()
            self._refresh_list()
            self._refresh_captions()
            self._update_preview(start)
            self.status_var.set("Segment updated. Save the EDL to keep these edits.")
        except (ValueError, tk.TclError) as exc:
            messagebox.showerror("Invalid segment", str(exc))

    def _move(self, delta: int):
        target = self.selected + delta
        if not 0 <= target < len(self.edl.segments):
            return
        items = list(self.edl.segments)
        items[self.selected], items[target] = items[target], items[self.selected]
        self.edl = replace(self.edl, segments=tuple(items))
        self.selected = target
        self._reflow()
        self._refresh_list()
        self._select(target)
        self.status_var.set("Segment order changed. Check narrative dependencies before rendering.")

    def _on_caption_select(self,_event=None):
        selection=self.caption_list.curselection()
        if not selection:
            return
        index=int(selection[0])
        if index>=len(self.visible_caption_ids):
            return
        span_id=self.visible_caption_ids[index]
        span=next((item for item in self.bundle.transcript if item.span_id==span_id),None)
        if span:
            self.caption_span_id=span_id
            self.caption_var.set(span.text)

    def _apply_caption(self):
        if not self.caption_span_id:
            return
        text=self.caption_var.get().strip()
        if not text:
            messagebox.showwarning("Caption text","Caption text cannot be empty.")
            return
        updated=tuple(
            replace(span,text=text) if span.span_id==self.caption_span_id else span
            for span in self.bundle.transcript
        )
        self.bundle=replace(self.bundle,transcript=updated)
        self._refresh_captions()
        self.status_var.set("Caption updated. Save the composition to keep this text.")

    def _update_preview(self,source_time):
        capture=cv2.VideoCapture(self.bundle.source.path)
        if not capture.isOpened():
            self.preview_label.configure(text="Source preview unavailable",image="")
            return
        capture.set(cv2.CAP_PROP_POS_MSEC,max(0.0,float(source_time))*1000)
        ok,frame=capture.read()
        capture.release()
        if not ok:
            self.preview_label.configure(text="Frame unavailable at this timestamp",image="")
            return
        rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
        image=Image.fromarray(rgb)
        image.thumbnail((300,150))
        self.preview_photo=ImageTk.PhotoImage(image)
        self.preview_label.configure(image=self.preview_photo,text="")

    def _validated(self):
        try:
            target = float(self.target_var.get())
            if not 12 <= target <= 180:
                raise ValueError("Target duration must be between 12 and 180 seconds.")
            self.edl = replace(
                self.edl,
                title=self.title_var.get().strip() or self.edl.title,
                target_duration_seconds=target,
                captions=replace(
                    self.edl.captions,
                    enabled=self.caption_enabled_var.get(),
                    burn_in=self.caption_burn_var.get(),
                    export_srt=self.caption_srt_var.get(),
                    uppercase=self.caption_upper_var.get(),
                    preset_id=self.caption_style_var.get(),
                ),
                audio=replace(
                    self.edl.audio,
                    allow_crossfade=self.audio_crossfade_var.get(),
                ),
            )
            report = validate_edl(self.edl, self.bundle.source)
            issues = [item.message for item in report.issues if item.severity == "error"]
            if self.edl.strategy == CompositionStrategy.NARRATIVE_RECONSTRUCTION:
                positions = {
                    event_id: index
                    for index, segment in enumerate(self.edl.segments)
                    for event_id in segment.event_ids
                }
                for event_id, required in self.bundle.event_dependencies.items():
                    if event_id not in positions:
                        continue
                    for dependency in required:
                        if dependency not in positions or positions[dependency] > positions[event_id]:
                            issues.append(f"Narrative dependency missing or out of order: {dependency} → {event_id}.")
            if issues:
                raise ValueError("\n".join(issues))
            return True
        except (ValueError, tk.TclError) as exc:
            messagebox.showerror("Composition validation", str(exc))
            return False

    def _save(self):
        if not self._validated():
            return
        from clipforge_contracts import to_dict
        self.edl_path.write_text(
            json.dumps(to_dict(self.edl), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.analysis_path.write_text(
            json.dumps(to_dict(self.bundle), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.status_var.set("Timeline and captions saved. Original source footage remains unchanged.")

    def _render(self):
        if not self._validated():
            return
        self._save()
        try:
            manifest = render_composition(
                self.bundle, self.edl,
                self.edl_path.parent / (
                    Path(self.bundle.source.path).stem + "_" + self.edl.strategy.value + ".mp4"
                ),
                layout="blur",
                log=lambda message: self.status_var.set(message),
            )
            self.status_var.set("Revised composition rendered: " + manifest["output"])
            messagebox.showinfo("Composition rendered", manifest["output"])
        except Exception as exc:
            messagebox.showerror("Render failed", str(exc)[:800])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--edl", help="Path to a Story Composer .edl.json file")
    args = parser.parse_args()
    path = args.edl or filedialog.askopenfilename(
        title="Open Story Composer EDL",
        filetypes=[("ClipForge EDL", "*.edl.json"), ("JSON", "*.json")],
    )
    if not path:
        return
    try:
        app = CompositionReview(path)
        app.root.mainloop()
    except Exception as exc:
        messagebox.showerror("Review Studio", str(exc)[:900])


if __name__ == "__main__":
    main()
