"""Synthetic animation documentary QA: colored icon follows a path, no human face."""
from pathlib import Path
import cv2
import numpy as np
from subject_tracking import track_subject
root=Path(__file__).parent
out=root/"samples"/"animated-object-qa.mp4"
out.parent.mkdir(exist_ok=True)
fps=20
writer=cv2.VideoWriter(str(out),cv2.VideoWriter_fourcc(*"mp4v"),fps,(640,360))
for k in range(120):
    frame=np.full((360,640,3),(33,40,49),np.uint8)
    cv2.rectangle(frame,(30,45),(604,315),(56,69,82),-1)
    cv2.putText(frame,"ANIMATED HISTORY - 1945",(66,85),cv2.FONT_HERSHEY_SIMPLEX,
                .8,(230,230,230),2)
    for j in range(6):
        cv2.line(frame,(40+j*100,125),(40+j*100,290),(76,80,95),1)
    # target: moving satellite-like object, no faces, alternating details
    x=110+round(290*k/119)
    cv2.rectangle(frame,(x-27,165),(x+27,225),(222,150,35),-1)
    cv2.rectangle(frame,(x-22,170),(x+22,220),(110,80,13),2)
    cv2.line(frame,(x-36,194),(x+36,194),(240,245,190),2)
    cv2.circle(frame,(x,195),10,(45,235,255),-1)
    cv2.putText(frame,"ROCKET",(x-38,248),cv2.FONT_HERSHEY_SIMPLEX,.45,(220,220,235),1)
    writer.write(frame)
writer.release()
result=track_subject(out,0,0,6.0,(110/640),(190/360),
                     bbox=(75/640,158/360,145/640,253/360),seconds=5.8)
points=result["points"]
print("QA_FILE",out)
print("METHOD",result["method"],"POINTS",len(points))
print("START_END",points[0],points[-1])
print("CENTER_MOVEMENT",round(points[-1]["center"]-points[0]["center"],3))
assert len(points)>=15,"Tracker lost animated object too early"
assert (points[-1]["center"]-points[0]["center"])>.28,"Tracker not following moving illustration"
print("UNIVERSAL_ANIMATION_QA=PASS")
