from pathlib import Path

root=Path(__file__).resolve().parent
p=root/"gemini_highlights.py"
s=p.read_text(encoding="utf-8")
s=s.replace('MODEL = "gemini-flash-latest"','MODEL = "gemini-3.6-flash"')
s=s.replace('    rows=[]\n    with tempfile.TemporaryDirectory', '    rows=[]\n    active_model=model\n    with tempfile.TemporaryDirectory')
s=s.replace('            candidates=fn(chunk,length,seconds,key,model)\n',
'''            try:
                candidates=fn(chunk,length,seconds,key,active_model)
            except RuntimeError as exc:
                # Fail over only when provider is temporarily unavailable.
                # Do not hide quota (429), auth (401/403) or invalid request errors.
                if provider is not None or active_model=="gemini-3.5-flash-lite" or not any(
                    marker in str(exc) for marker in ("HTTP 503", "HTTP 502", "HTTP 504")):
                    raise
                log(f"Primary model unavailable ({type(exc).__name__}); trying Gemini 3.5 Flash-Lite.")
                active_model="gemini-3.5-flash-lite"
                candidates=fn(chunk,length,seconds,key,active_model)
''')
s=s.replace('"source":str(src),"model":model,"created":datetime.now().isoformat(),',
            '"source":str(src),"model":active_model,"created":datetime.now().isoformat(),')
p.write_text(s,encoding="utf-8")

g=root/"clipforge_gui.py"
s=g.read_text(encoding="utf-8")
old='        self.entry(modelrow,self.model).pack(side="left",fill="x",expand=True,ipady=6)'
new='''        ttk.Combobox(modelrow,textvariable=self.model,state="normal",
                     values=["gemini-3.6-flash","gemini-3.5-flash-lite",
                             "gemini-3.8-flash","gemini-3.7-flash",
                             "gemini-3.1-flash-lite","gemini-2.5-flash"],
                     width=28).pack(side="left",fill="x",expand=True,ipady=6)'''
if old not in s:
    raise RuntimeError("GUI model entry not found")
s=s.replace(old,new)
g.write_text(s,encoding="utf-8")
print("PATCH_APPLIED: default 3.6 Flash, fallback 3.5 Flash-Lite on 502/503/504, selectable GUI models.")
