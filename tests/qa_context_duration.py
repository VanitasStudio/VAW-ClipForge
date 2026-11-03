from smart_duration import _build_sentences,align_interval
from gemini_highlights import select_best,request_gemini,sample_windows
from clip_engine import probe_duration
from pathlib import Path
import json

words=[]
def add(sentence,start,step=.38):
    tokens=sentence.split()
    t=start
    for token in tokens:
        words.append({"start":t,"end":t+.28,"text":token})
        t+=step
add("The brain stores memories through changing connections.",0.0)
add("Every time you remember something, the network changes.",3.4)
add("That is why a memory is never a perfect recording.",6.8)
add("It is rebuilt by your brain each time you recall it.",10.5)
spans=_build_sentences(words)
assert len(spans)==4,spans
aligned=align_interval(1.1,13.2,spans,20)
assert aligned and aligned[0]==0.0 and aligned[1]==14.58,aligned
rows=[
 {"start":1.1,"end":13.2,"score":91,"title":"Memory reconstruction","reason":"A complete explanation","complete":True},
 {"start":2.0,"end":8.0,"score":99,"title":"Incomplete duplicate","reason":"Too short","complete":False},
]
picked=select_best(rows,3,20,30,sentences=spans)
assert len(picked)==1,picked
assert picked[0]["duration"]!=30 and picked[0]["duration"]>=12,picked
assert picked[0]["boundary_alignment"]["start"]=="sentence"
# Variable-duration candidates are preserved when local alignment is disabled.
variable=select_best([{"start":2,"end":47,"score":90,"title":"Long idea","reason":"Full idea"}],1,60,30)
assert variable and variable[0]["duration"]==45.0,variable
# Stories over the 180s Shorts ceiling are rejected rather than truncated.
long=[]
for i in range(26):
    s=i*7.0
    long.append({"start":s,"end":s+6.0,"text":f"Sentence {i} ends.", "word_count":3})
limited=align_interval(0,190,long,200)
assert limited is None,limited
windows=sample_windows(894)
assert len(windows)==4 and windows[1][0]==228.0,windows
assert windows[0][0]+windows[0][1]-windows[1][0]==12.0,windows
assert windows[-1][0]+windows[-1][1]>=894,windows

print("SENTENCE_SPANS",len(spans))
print("ALIGNED_SAMPLE",aligned)
print("VARIABLE_PICK",picked[0]["duration"],picked[0]["boundary_alignment"])
print("VARIABLE_WITHOUT_WHISPER",variable[0]["duration"])
print("180S_LIMIT",limited)
print("SOURCE_TEST_SECONDS",round(probe_duration(Path(__file__).resolve().parents[1]/"samples"/"spoken-test.mp4"),2))
print("CONTEXT_DURATION_UNIT_TESTS_PASS")
