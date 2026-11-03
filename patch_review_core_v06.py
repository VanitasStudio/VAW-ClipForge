"""Upgrade review_core to v0.6 styles, subject tracks, per-scene dip transitions."""
from pathlib import Path
p=Path(__file__).with_name("review_core.py")
s=p.read_text(encoding="utf-8")
s=s.replace("from stylish_captions import ASS_HEADER, safe_text, emphasized_text, timestamp_ass",
            "from subtitle_presets import caption_ass, choose\nfrom subject_tracking import tracked_center")
a=s.index("def make_ass(rows,mode=\"modern\"):")
b=s.index("\ndef load_clip(mp4):",a)
s=s[:a]+'''def make_ass(rows,mode="karaoke"):
    return caption_ass(rows,mode)

'''+s[b:]
s=s.replace('''    mode="modern"
    if draft.exists():''',
'''    mode="karaoke"
    subject_tracks=[]
    transitions={}
    if draft.exists():''')
s=s.replace('''            mode=saved.get("caption_style",mode)
    cap=cv2.VideoCapture''',
'''            mode=saved.get("caption_style",mode)
            subject_tracks=saved.get("subject_tracks",[])
            transitions=saved.get("transitions",{})
    cap=cv2.VideoCapture''')
s=s.replace('''            "caption_style":mode}''',
'''            "caption_style":mode,"subject_tracks":subject_tracks,
            "transitions":transitions}''')
s=s.replace('''    manual=[(float(k["time"]),float(k["center"])) for k in data.get("keyframes",[])]''',
'''    subject=tracked_center(data,t)
    if subject is not None:
        center=subject
    manual=[(float(k["time"]),float(k["center"])) for k in data.get("keyframes",[])]''')
s=s.replace('''    for k in data.get("keyframes",[]):
        if not 0<=float(k["time"])<=dur or not 0<=float(k["center"])<=1:
            raise ValueError("Keyframe is out of bounds")''',
'''    for k in data.get("keyframes",[]):
        if not 0<=float(k["time"])<=dur or not 0<=float(k["center"])<=1:
            raise ValueError("Keyframe is out of bounds")
    if choose(data.get("caption_style","karaoke")).id not in ("karaoke","bold_pop",
            "minimal","gaming","neon","creator"):
        raise ValueError("Unknown subtitle preset")
    for track in data.get("subject_tracks",[]):
        if not 0<=float(track["start"])<=float(track["end"])<=dur+.1:
            raise ValueError("Subject tracking time invalid")
        if len(track.get("points",[]))>1000:
            raise ValueError("Too many track points")
    cuts={f"{float(cut):.2f}" for cut in data.get("cuts",[])}
    for cut,mode in data.get("transitions",{}).items():
        if cut not in cuts or mode not in ("hard","dip"):
            raise ValueError("Unknown cut transition setting")''')
s=s.replace('''    to_save={k:data[k] for k in ("clip","source","subtitles","keyframes","caption_style")}''',
'''    to_save={k:data[k] for k in ("clip","source","subtitles","keyframes",
                                  "caption_style","subject_tracks","transitions")}''')
s=s.replace('''    video_filter+=f"ass={ass.name}"''',
'''    dip_times=[float(c) for c,kind in data.get("transitions",{}).items()
               if kind=="dip" and .16<float(c)<float(data["duration"])-.16]
    if dip_times:
        terms=["exp(-(((t-"+f"{c:.3f}"+")/0.12)*((t-"+f"{c:.3f}"+")/0.12)))"
               for c in dip_times]
        video_filter+="eq=brightness='-0.65*("+"+".join(terms)+")':eval=frame,"
        log(f"Applying soft dip transitions to {len(dip_times)} scene cut(s).")
    video_filter+=f"ass={ass.name}"''')
s=s.replace('''         "keyframes":data["keyframes"],"captions":len(data["subtitles"]),''',
'''         "keyframes":data["keyframes"],"subjects":len(data.get("subject_tracks",[])),
         "transitions":data.get("transitions",{}),
         "subtitle_mode":data.get("caption_style","karaoke"),
         "captions":len(data["subtitles"]),''')
p.write_text(s,encoding="utf-8")
print("Core v0.6 patched.")
