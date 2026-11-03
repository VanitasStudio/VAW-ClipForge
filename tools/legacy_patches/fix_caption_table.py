from pathlib import Path
p=Path(__file__).with_name("review_editor.py")
s=p.read_text(encoding="utf-8")
start=s.index('        self.subtitles=ttk.Treeview(right,')
end=s.index('        self.subtitles.bind("<<TreeviewSelect>>",self.select_caption)',start)
replacement='''        caption_panel=tk.Frame(right,bg=COLORS["bg"])
        caption_panel.pack(fill="both",expand=True)
        self.subtitles=ttk.Treeview(caption_panel,columns=("start","end","text"),
                                   show="headings",height=13)
        for name,width in (("start",68),("end",68),("text",312)):
            self.subtitles.heading(name,text=name.upper())
            self.subtitles.column(name,width=width,anchor="w")
        caption_scroll=ttk.Scrollbar(caption_panel,orient="vertical",command=self.subtitles.yview)
        self.subtitles.configure(yscrollcommand=caption_scroll.set)
        self.subtitles.pack(side="left",fill="both",expand=True)
        caption_scroll.pack(side="right",fill="y")
'''
s=s[:start]+replacement+s[end:]
p.write_text(s,encoding="utf-8")
print("Caption table layout fixed")
