"""Enable native 720x1280 / 1080x1920 vertical rendering from the source.
Do NOT upscale the prior 720p exports for new-generation clips.
"""
from pathlib import Path

root=Path(__file__).resolve().parent

p=root/"clip_engine.py"
s=p.read_text(encoding="utf-8")
a=s.index("def filter_graph(style):")
b=s.index("\ndef process(",a)
func='''OUTPUT_SIZES={"720p":(720,1280),"1080p":(1080,1920)}

def filter_graph(style,resolution="720p"):
    if resolution not in OUTPUT_SIZES:
        raise ValueError("Choose 720p or 1080p vertical output")
    w,h=OUTPUT_SIZES[resolution]
    if style=="crop":
        return (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                f"crop={w}:{h},setsar=1,format=yuv420p")
    if style=="fit":
        return (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,format=yuv420p")
    if style!="blur":
        raise ValueError("Invalid layout")
    return (f"split=2[fg][bg];[bg]scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},boxblur=18:1[back];"
            f"[fg]scale={w}:{h}:force_original_aspect_ratio=decrease[front];"
            "[back][front]overlay=(W-w)/2:(H-h)/2,setsar=1,format=yuv420p")

'''
s=s[:a]+func+s[b:]
p.write_text(s,encoding="utf-8")

p=root/"smart_reframe.py"
s=p.read_text(encoding="utf-8")
s=s.replace("from clip_engine import FFMPEG, filter_graph, probe_duration",
            "from clip_engine import FFMPEG, filter_graph, probe_duration, OUTPUT_SIZES")
s=s.replace('''def smart_render(segment,output,auto=True,scenes=True,layout="blur",subject_mode="universal",log=print):''',
'''def smart_render(segment,output,auto=True,scenes=True,layout="blur",
                 subject_mode="universal",resolution="1080p",log=print):''')
s=s.replace('''    segment=Path(segment).resolve()
    output=Path(output).resolve()
    meta={''',
'''    segment=Path(segment).resolve()
    output=Path(output).resolve()
    if resolution not in OUTPUT_SIZES:
        raise ValueError("Invalid output resolution")
    out_w,out_h=OUTPUT_SIZES[resolution]
    meta={''',1)
s=s.replace('''          "focus_samples":[],"subject_mode":subject_mode}''',
'''          "focus_samples":[],"subject_mode":subject_mode,
          "output_resolution":f"{out_w}x{out_h}"}''',1)
s=s.replace('''        vf=filter_graph(layout)''','''        vf=filter_graph(layout,resolution=resolution)''',1)
s=s.replace('''            vf="scale=720:1280:force_original_aspect_ratio=decrease,"+(
                "pad=720:1280:(ow-iw)/2:(oh-ih)/2:black,setsar=1,format=yuv420p")''',
'''            vf=(f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,"
                f"pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2:black,"
                "setsar=1,format=yuv420p")''',1)
s=s.replace('''                "scale=720:1280,setsar=1,format=yuv420p")''',
'''                f"scale={out_w}:{out_h},setsar=1,format=yuv420p")''',1)
s=s.replace('''               subject_mode="universal",log=print):''',
'''               subject_mode="universal",resolution="1080p",log=print):''',1)
s=s.replace('''                        "caption_style":style,"subject_mode":subject_mode},''',
'''                        "caption_style":style,"subject_mode":subject_mode,
                        "resolution":resolution},''',1)
s=s.replace('''                                            subject_mode=subject_mode,log=log)''',
'''                                            subject_mode=subject_mode,
                                            resolution=resolution,log=log)''',1)
p.write_text(s,encoding="utf-8")

p=root/"review_core.py"
s=p.read_text(encoding="utf-8")
s=s.replace('''                      "scale=720:1280,setsar=1,format=yuv420p,")''',
'''                      "scale=1080:1920,setsar=1,format=yuv420p,")''')
s=s.replace('''        video_filter=("scale=720:1280:force_original_aspect_ratio=decrease,"
                      "pad=720:1280:(ow-iw)/2:(oh-ih)/2:black,format=yuv420p,")''',
'''        video_filter=("scale=1080:1920:force_original_aspect_ratio=decrease,"
                      "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,format=yuv420p,")''')
s=s.replace('''         "subtitle_mode":data.get("caption_style","karaoke"),''',
'''         "subtitle_mode":data.get("caption_style","karaoke"),
         "output_resolution":"1080x1920",''')
p.write_text(s,encoding="utf-8")
print("1080x1920 native render pipeline patched for main editor and generator.")
