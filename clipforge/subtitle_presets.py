"""ClipForge caption presets with resolution-aware, measured safe-area layout."""
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
ALIASES={"modern":"karaoke","clean":"minimal","all capital":"all_caps","all capital subtitle":"all_caps"}
BY_ID={p.id:p for p in PRESETS}
LAYOUT_WIDTH=720
LAYOUT_HEIGHT=1280
SAFE_TEXT_WIDTH=610
MIN_FONT_SIZE=14
MAX_LINES=2

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

def _font_path(name):
    candidates=(
        ["C:/Windows/Fonts/arialbd.ttf"] if "Arial" in name else
        ["C:/Windows/Fonts/segoeuib.ttf","C:/Windows/Fonts/arialbd.ttf"]
    )
    return next((Path(item) for item in candidates if Path(item).is_file()),None)

def _measure(text,font_size,preset):
    path=_font_path(preset.font)
    try:
        font=ImageFont.truetype(str(path),font_size) if path else ImageFont.load_default()
        return float(font.getlength(text))
    except (OSError,AttributeError):
        return len(text)*font_size*0.58

def _wrap_at_size(tokens,font_size,preset):
    lines=[]
    current=""
    for token in tokens:
        candidate=(current+" "+token).strip()
        if current and _measure(candidate,font_size,preset)>SAFE_TEXT_WIDTH:
            lines.append(current)
            current=token
        else:
            current=candidate
    if current:
        lines.append(current)
    return lines

def layout_caption(tokens,preset):
    """Greedy font-metric wrapping; shrink long copy before allowing overflow."""
    size=int(preset.fontsize)
    lines=_wrap_at_size(tokens,size,preset)
    while (len(lines)>MAX_LINES or any(_measure(token,size,preset)>SAFE_TEXT_WIDTH for token in tokens)) and size>MIN_FONT_SIZE:
        size=max(MIN_FONT_SIZE,size-2)
        lines=_wrap_at_size(tokens,size,preset)
    # Preserve every word even for unusually long transcripts. Three compact
    # lines are preferable to text extending beyond the portrait safe area.
    return lines,size

def break_lines(words):
    """Compatibility helper returning measured line breaks as ASS tokens."""
    lines,_=layout_caption(list(words),BY_ID["karaoke"])
    result=[]
    for index,line in enumerate(lines):
        if index:
            result.append(r"\N")
        result.extend(line.split())
    return result

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
        lines,font_size=layout_caption(tokens,preset)
        wrapped=[]
        for line_index,line in enumerate(lines):
            if line_index:
                wrapped.append(r"\N")
            wrapped.extend(line.split())
        indices=[i for i,token in enumerate(wrapped) if token!=r"\N"]
        baseprefix=rf"{{\an2\pos(360,{preset.baseline})}}"
        if font_size!=preset.fontsize:
            baseprefix+=rf"{{\fs{font_size}}}"
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
    return image
