from pathlib import Path
p=Path(__file__).with_name("gemini_highlights.py")
s=p.read_text(encoding="utf-8")
needle='''    rows=[]
    errors=[]
    active_model=model
    with tempfile.TemporaryDirectory(prefix="vawclip-ai-") as work:'''
replacement='''    rows=[]
    errors=[]
    active_model=model
    # Save each successful section to avoid reusing quota after a partial failure.
    if not dry_run:
        dest.mkdir(parents=True,exist_ok=True)
    cachefile=dest/"analysis-progress.json"
    fingerprint=str((str(src),src.stat().st_size,src.stat().st_mtime_ns,
                     model,seconds,visual))
    completed={}
    if cachefile.exists():
        try:
            old=json.loads(cachefile.read_text(encoding="utf-8"))
            if old.get("fingerprint")==fingerprint:
                completed=old.get("successful_sections",{})
                log(f"Recovered {len(completed)} previously analyzed section(s).")
        except (ValueError,OSError):
            pass
    with tempfile.TemporaryDirectory(prefix="vawclip-ai-") as work:'''
if needle not in s:raise ValueError("Cache setup anchor missing")
s=s.replace(needle,replacement)
needle='''        for i,(offset,length) in enumerate(windows,1):
            audio=Path(work)/f"audio{i}.mp3"'''
replacement='''        for i,(offset,length) in enumerate(windows,1):
            if str(i) in completed:
                cached=completed[str(i)]
                for x in cached:
                    rows.append({**x,"start":x["start"]+offset,"end":x["end"]+offset})
                log(f"Section {i}: reused {len(cached)} cached highlights.")
                continue
            audio=Path(work)/f"audio{i}.mp3"'''
if needle not in s:raise ValueError("Cache reuse anchor missing")
s=s.replace(needle,replacement)
needle='''            for x in candidates:
                rows.append({**x,"start":x["start"]+offset,"end":x["end"]+offset})'''
replacement='''            completed[str(i)]=candidates
            if not dry_run:
                cachefile.write_text(json.dumps({
                    "fingerprint":fingerprint,
                    "successful_sections":completed
                },indent=2),encoding="utf-8")
            for x in candidates:
                rows.append({**x,"start":x["start"]+offset,"end":x["end"]+offset})'''
if needle not in s:raise ValueError("Cache save anchor missing")
s=s.replace(needle,replacement)
p.write_text(s,encoding="utf-8")

gui=Path(__file__).with_name("clipforge_gui.py")
s=gui.read_text(encoding="utf-8")
old='''            "This will send compressed audio excerpts from this video to Google AI.\\n"
            "Maximum six requests. Costs or quotas depend on your Google project.\\n"'''
new='''            "This sends compressed audio and (if enabled) sampled frames to Google AI.\\n"
            "Up to 6 sections; failed calls may retry. API quota/cost may apply.\\n"'''
if old not in s:raise ValueError("Consent text anchor missing")
s=s.replace(old,new)
gui.write_text(s,encoding="utf-8")
print("v0.3: cache/recovery + accurate media consent applied")
