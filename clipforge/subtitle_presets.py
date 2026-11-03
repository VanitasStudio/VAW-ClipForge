"""ClipForge v0.6 selectable caption presets and live thumbnail samples.

ASS rendering uses explicit 720x1280 layout, safe word animation and original captions.
No external fonts; Segoe UI and Arial shipped with Windows.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

@dataclass(frozen=True)
class Preset:
    id:str
    name:str
    sub:str
    font:str
    fontsize:int
    white:str
    accent:str
    stroke:str
    outline:int
    shadow:int
    baseline:int
    animated:bool
    uppercase:bool=False

PRESETS=[
    Preset("karaoke","Karaoke","Word-by-word crimson","Segoe UI Semibold",49,"#FFFFFF","#FF5A6A","#07080E",4,2,1080,True),
    Preset("bold_pop","Bold Pop","Large punchy yellow","Arial",59,"#FFFFFF","#FFF357","#08090A",5,2,1060,True,True),
    Preset("minimal","Minimal","Small clean white","Segoe UI Semibold",39,"#FFFFFF","#FFFFFF","#121722",2,1,1090,False),
    Preset("gaming","Gaming","Cyan and electric lime","Arial",51,"#E8FCFF","#8DFF63","#041525",5,2,1065,True,True),
    Preset("neon","Neon","Hot pink accent","Segoe UI Semibold",47,"#FFFFFF","#FF70D8","#22102B",4,3,1070,True),
    Preset("creator","Creator","Bright orange accents","Segoe UI Semibold",51,"#FFFFFF","#FFB453","#0B0F17",4,1,1075,True),
    Preset("all_caps","All Capital Subtitle","Full uppercase with bold word highlight","Arial",57,"#FFFFFF","#FFF357","#08090A",5,2,1060,True,True),
]
ALIASES={"modern":"karaoke","clean":"minimal",
         "all capital":"all_caps","all capital subtitle":"all_caps"}
BY_ID={p.id:p for p in PRESETS}

def choose(name):
    return BY_ID.get(ALIASES.get(name,name),BY_ID["karaoke"])

def asscolor(hexa):
    h=hexa.strip("#")
    return "&H00"+h[4:6]+h[2:4]+h[0:2]+"&"

def ass_stamp(t):
    centis=max(0,round(float(t)*100))
    h,centis=divmod(centis,360000)
    m,centis=divmod(centis,6000)
    s,centis=divmod(centis,100)
    return f"{h}:{m:02}:{s:02}.{centis:02}"

def escape(text):
    return text.replace("\\","").replace("{","(").replace("}",")").replace("\n"," ")

def break_lines(words):
    """Stable word wrap across all highlighted events."""
    text=" ".join(words)
    if len(text)<=25:
        return list(words)
    split=min(range(1,len(words)),key=lambda i:abs(len(" ".join(words[:i]))-len(" ".join(words[i:]))))
    return words[:split]+[r"\N"]+words[split:]

def caption_ass(rows,mode="karaoke"):
    preset=choose(mode)
    style=(f"Style: Selected,{preset.font},{preset.fontsize},"
           f"{asscolor(preset.white)},{asscolor(preset.white)},"
           f"{asscolor(preset.stroke)},&H64000000,-1,0,0,0,100,100,0,0,"
           f"1,{preset.outline},{preset.shadow},2,36,36,160,1")
    out=["[Script Info]\nScriptType: v4.00+\nPlayResX: 720\nPlayResY: 1280\n"
         "ScaledBorderAndShadow: yes\nWrapStyle: 2\n\n[V4+ Styles]\n"
         "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
         "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
         "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
         "Alignment, MarginL, MarginR, MarginV, Encoding\n",
         style+"\n\n[Events]\n"
         "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"]
    old_end=0.0
    for row in sorted(rows,key=lambda x:float(x["start"])):
        start=float(row["start"]);end=float(row["end"])
        if start<old_end-0.02:raise ValueError("Caption segments overlap")
        text=str(row["text"]).strip()
        tokens=text.split()
        if not tokens or end<=start:continue
        if preset.uppercase:tokens=[word.upper() for word in tokens]
        wrapped=break_lines(tokens)
        indices=[i for i,token in enumerate(wrapped) if token!=r"\N"]
        baseprefix=rf"{{\an2\pos(360,{preset.baseline})}}"
        n=len(indices)
        word_spans=row.get("word_spans",[])
        for j in range(n if preset.animated else 1):
            if preset.animated and len(word_spans)==n:
                a=max(start,min(end,float(word_spans[j][0])))
                b=max(a+0.012,min(end,float(word_spans[j+1][0]) if j+1<n else end))
            else:
                a=start+(end-start)*j/n if preset.animated else start
                b=start+(end-start)*(j+1)/n if preset.animated else end
            if b<=a+0.005:continue
            focused=indices[j] if preset.animated else -1
            rendered=[]
            for i,token in enumerate(wrapped):
                if token==r"\N":
                    rendered.append(r"\N");continue
                if i==focused:
                    rendered.append(r"{\c"+asscolor(preset.accent)+r"}"+escape(token)
                                    +r"{\c"+asscolor(preset.white)+r"}")
                else:rendered.append(escape(token))
            caption=" ".join(rendered).replace(" "+r"\N"+" ",r"\N")
            out.append(f"Dialogue: 0,{ass_stamp(a)},{ass_stamp(b)},Selected,,0,0,0,,"
                       f"{baseprefix}{caption}\n")
        old_end=end
    return "".join(out)

def preview_image(mode,width=240,height=140,selected=False):
    preset=choose(mode)
    image=Image.new("RGB",(width,height),(18,22,34))
    draw=ImageDraw.Draw(image)
    draw.rounded_rectangle((9,8,width-10,height-9),radius=12,
                           fill=(31,38,55),outline=(221,64,82) if selected else (66,76,93),width=2)
    draw.rectangle((19,20,width-20,68),fill=(48,58,78))
    draw.rounded_rectangle((80,26,156,59),radius=12,fill=(93,109,127))
    draw.ellipse((111,18,133,40),fill=(201,147,117))
    paths=["C:/Windows/Fonts/segoeuib.ttf","C:/Windows/Fonts/arialbd.ttf"]
    font=next((ImageFont.truetype(path,19 if preset.fontsize<50 else 20) for path in paths if Path(path).exists()),ImageFont.load_default())
    phrase=["THIS","IS","AMAZING"] if preset.uppercase else ["This","is","amazing"]
    sizes=[draw.textlength(t,font=font) for t in phrase]
    spacing=5
    xpos=(width-(sum(sizes)+spacing*2))/2
    for idx,token in enumerate(phrase):
        draw.text((xpos,78),token,font=font,fill=preset.accent if idx==2 else preset.white,
                  stroke_width=2 if preset.outline>=4 else 1,stroke_fill=preset.stroke)
        xpos+=sizes[idx]+spacing
    font2=next((ImageFont.truetype(path,12) for path in ["C:/Windows/Fonts/segoeui.ttf"] if Path(path).exists()),ImageFont.load_default())
    return image
