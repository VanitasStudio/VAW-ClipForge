from pathlib import Path
p=Path(__file__).with_name("review_editor.py")
s=p.read_text(encoding="utf-8")
old='''        self.subtitles.pack(fill="both",expand=True)
        self.subtitles.bind("<<TreeviewSelect>>",self.select_caption)'''
new='''        caption_scroll=ttk.Scrollbar(right,orient="vertical",command=self.subtitles.yview)
        self.subtitles.configure(yscrollcommand=caption_scroll.set)
        self.subtitles.pack(side="left",fill="both",expand=True)
        self.subtitles.pack_forget()
        caption_panel=tk.Frame(right,bg=COLORS["bg"])
        caption_panel.pack(fill="both",expand=True)
        self.subtitles.pack(in_=caption_panel,side="left",fill="both",expand=True)
        caption_scroll.pack(in_=caption_panel,side="right",fill="y")
        self.subtitles.bind("<<TreeviewSelect>>",self.select_caption)'''
if old not in s:raise ValueError("Caption table anchor missing")
s=s.replace(old,new)
s=s.replace('            self.paint_caption(cropped,msg)','            self.paint_caption(cropped,msg,t)')
start=s.index('    def paint_caption(self,image,text):')
end=s.index('    def scrub(self,_=None):',start)
replacement='''    def paint_caption(self,image,text,t):
        draw=ImageDraw.Draw(image)
        font_path="C:/Windows/Fonts/segoeuib.ttf"
        font=ImageFont.truetype(font_path,18) if Path(font_path).exists() else ImageFont.load_default()
        words=text.split()
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
                is_active=(index==active and self.style.get()=="modern")
                draw.text((x,y),word,font=font,
                          fill="#ff5e73" if is_active else "#ffffff",
                          stroke_width=2,stroke_fill="#06080b")
                x+=width

'''
s=s[:start]+replacement+s[end:]
p.write_text(s,encoding="utf-8")
print("Caption scroll and red active-word preview integrated.")
