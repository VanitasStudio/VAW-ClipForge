from pathlib import Path
p=Path(__file__).with_name("stylish_captions.py")
s=p.read_text(encoding="utf-8")
s=s.replace('end-current[0][0]>1.65 or total>25',
            'end-current[0][0]>1.85 or total>32')
s=s.replace('len(fused[-1])<=2 and p[-1][1]-fused[-1][0][0]<1.9',
            'len(fused[-1])<=3 and p[-1][1]-fused[-1][0][0]<2.4')
s=s.replace('''    for n,group in enumerate(groups,1):
        start=max(0,group[0][0]-0.03)
        end=group[-1][1]+0.07''',
'''    previous_end=0.0
    for n,group in enumerate(groups,1):
        start=max(previous_end,group[0][0]-0.01)
        end=group[-1][1]+0.04
        if n<len(groups):
            next_start=groups[n][0][0]
            end=min(end,max(start+0.09,next_start-0.025))
        end=max(end,start+0.09)
        previous_end=end''')
p.write_text(s,encoding="utf-8")

r=Path(__file__).with_name("smart_reframe.py")
s=r.read_text(encoding="utf-8")
s=s.replace('''        outfile=dest/f"{source.stem}_v04_{i:02d}_{round(start):05d}s.mp4"
        item={**pick,"output":str(outfile)}''',
'''        stem=f"{source.stem}_v04_{i:02d}_{round(start):05d}s"
        outfile=dest/f"{stem}.mp4"
        revision=2
        while outfile.exists():
            outfile=dest/f"{stem}_rev{revision}.mp4"
            revision+=1
        item={**pick,"output":str(outfile)}''')
r.write_text(s,encoding="utf-8")
print("Caption timing and version-safe exports patched")
