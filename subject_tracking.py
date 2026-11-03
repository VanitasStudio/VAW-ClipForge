"""VAW ClipForge v0.7 — generic region tracking for animated documentaries.

Manual rectangle or click selection tracks ANY visible object (vehicle, icon,
diagram, character, product, text panel) without identity recognition.

Hybrid: sparse optical flow + local normalized template matching.  It stops
at scene boundaries, refuses low-confidence jumps, and retains original input.
No external AI service, face classifier, or network calls.
"""
from __future__ import annotations
import math
from pathlib import Path
import cv2
import numpy as np

def _clip_bbox(rect, width, height):
    x0,y0,x1,y1 = map(float, rect)
    x0,x1=sorted((x0,x1))
    y0,y1=sorted((y0,y1))
    # tiny drag/click => create a default box around selected point
    if x1-x0<0.045:
        cx=(x0+x1)/2
        x0,x1=cx-.085,cx+.085
    if y1-y0<0.05:
        cy=(y0+y1)/2
        y0,y1=cy-.13,cy+.13
    x0=max(0,min(1,x0)); x1=max(0,min(1,x1))
    y0=max(0,min(1,y0)); y1=max(0,min(1,y1))
    if x1-x0<.02 or y1-y0<.02:
        raise ValueError("Selection too small; drag a rectangle around the object.")
    return (int(x0*width),int(y0*height),int(x1*width),int(y1*height))

def _features(gray, box, limit=110):
    x0,y0,x1,y1=box
    mask=np.zeros_like(gray)
    mask[y0:y1,x0:x1]=255
    return cv2.goodFeaturesToTrack(gray,maxCorners=limit,qualityLevel=.011,
                                   minDistance=4,mask=mask,blockSize=3)

def _template_position(gray,template,box,predicted_x,predicted_y):
    """Find a local match, rather than searching whole video and jumping to a duplicate."""
    height,width=gray.shape
    tw=template.shape[1];th=template.shape[0]
    if width<tw or height<th:return None
    radius_x=max(25,int(tw*1.30))
    radius_y=max(20,int(th*1.35))
    x0=max(0,round(predicted_x-radius_x))
    y0=max(0,round(predicted_y-radius_y))
    x1=min(width,round(predicted_x+radius_x+tw))
    y1=min(height,round(predicted_y+radius_y+th))
    scan=gray[y0:y1,x0:x1]
    if scan.shape[1]<tw or scan.shape[0]<th:return None
    template_variance=float(np.std(template))
    if template_variance<7.5:
        matching=cv2.matchTemplate(scan,template,cv2.TM_SQDIFF_NORMED)
        low,high,lowat,highat=cv2.minMaxLoc(matching)
        score=1-float(low)
        pos=lowat
    else:
        matching=cv2.matchTemplate(scan,template,cv2.TM_CCOEFF_NORMED)
        low,high,lowat,highat=cv2.minMaxLoc(matching)
        score=float(high)
        pos=highat
    if not math.isfinite(score) or score<.43:return None
    return x0+pos[0],y0+pos[1],score

def track_subject(source,start_abs,start_rel,duration,x_fraction,y_fraction,
                  cut_times=(),seconds=5,log=print,bbox=None):
    """Follow user-selected visual REGION, not a person's identity.

    x/y are click coordinates (0..1). bbox is normalized (left,top,right,bottom).
    Runs at ~5fps; returns keyframes with confidence and the requested ROI.
    """
    source=Path(source)
    cap=cv2.VideoCapture(str(source))
    if not cap.isOpened():raise RuntimeError("Cannot open source video for object tracking.")
    try:
        fps=float(cap.get(cv2.CAP_PROP_FPS) or 30)
        fps=max(5.0,fps)
        width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if width<32 or height<32:raise ValueError("Invalid input dimensions.")
        begin=max(0.0,float(start_rel))
        end=min(float(duration),begin+min(15.0,max(1.0,float(seconds))))
        cut=min((float(c) for c in cut_times if begin+.06<float(c)<=end),
                default=end+.01)
        end=min(end,cut-.035)
        if end-begin<.17:raise RuntimeError("Too close to a scene cut to start tracking.")
        if bbox is None:
            x,y=float(x_fraction),float(y_fraction)
            bbox=(x-.09,y-.14,x+.09,y+.14)
        rect=_clip_bbox(bbox,width,height)
        x0,y0,x1,y1=rect
        if x1-x0<10 or y1-y0<10:
            raise ValueError("Selected object region is too small.")
        cap.set(cv2.CAP_PROP_POS_MSEC,(float(start_abs)+begin)*1000)
        ok,frame=cap.read()
        if not ok:raise RuntimeError("Unable to decode the selected source frame.")
        previous=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        # The template includes background/object edges; a clicked empty flat
        # area will report low confidence rather than 'recognize' a subject.
        template=previous[y0:y1,x0:x1].copy()
        if template.size==0:raise ValueError("Empty object selection.")
        track_box=(float(x0),float(y0),float(x1),float(y1))
        center_x=(x0+x1)/2
        points=[{"time":round(begin,3),"center":round(center_x/width,5),
                 "confidence":1.0}]
        prev_points=_features(previous,rect)
        stride=max(1,int(round(fps/5)))
        frames=int(math.ceil((end-begin)*fps/stride))
        low_confidence_streak=0
        for k in range(1,frames+1):
            rel=min(end,begin+k*stride/fps)
            cap.set(cv2.CAP_PROP_POS_MSEC,(float(start_abs)+rel)*1000)
            ok,frame=cap.read()
            if not ok:break
            gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
            ox,oy,ex,ey=track_box
            bw=ex-ox;bh=ey-oy
            dx=dy=0.0;flow_conf=0.0
            if prev_points is not None and len(prev_points)>=4:
                nxt,status,_=cv2.calcOpticalFlowPyrLK(
                    previous,gray,prev_points,None,
                    winSize=(21,21),maxLevel=3,
                    criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,25,.012))
                if nxt is not None and status is not None:
                    matched=status.reshape(-1)==1
                    old=prev_points.reshape(-1,2)[matched]
                    new=nxt.reshape(-1,2)[matched]
                    if len(new)>=4:
                        diff=new-old
                        median=np.median(diff,axis=0)
                        residual=np.linalg.norm(diff-median,axis=1)
                        inliers=(residual<max(3.5,bw*.055))
                        if inliers.sum()>=4:
                            dx=float(np.median(diff[inliers,0]))
                            dy=float(np.median(diff[inliers,1]))
                            flow_conf=min(1.,float(inliers.mean())*
                                          min(1.,len(new)/18))
            pred_x=max(0,min(width-bw,ox+dx))
            pred_y=max(0,min(height-bh,oy+dy))
            match=_template_position(gray,template,track_box,pred_x,pred_y)
            if match:
                tx,ty,match_score=match
                motion_diff=math.hypot(tx-pred_x,ty-pred_y)
                # Reject wildly different positions unless optical flow corroborates.
                agrees=motion_diff<max(14.,bw*.7) or flow_conf<.18
                if agrees:
                    blend=.62 if match_score>.72 else .35
                    new_x=pred_x*(1-blend)+tx*blend
                    new_y=pred_y*(1-blend)+ty*blend
                    confidence=max(flow_conf*.8,match_score)
                else:
                    new_x,new_y,confidence=pred_x,pred_y,flow_conf*.75
            elif flow_conf>.17:
                new_x,new_y,confidence=pred_x,pred_y,flow_conf
            else:
                low_confidence_streak+=1
                if low_confidence_streak>=5:
                    log("Tracking stopped: object lost / insufficient visual evidence.")
                    break
                # Temporary hold is preferable to jumping to an unrelated object.
                new_x,new_y,confidence=ox,oy,.08
            if confidence>.27:low_confidence_streak=0
            if abs(new_x-ox)>width*.16 or abs(new_y-oy)>height*.24:
                log("Tracking stopped: implausible object jump.")
                break
            new_x=max(0,min(width-bw,new_x))
            new_y=max(0,min(height-bh,new_y))
            track_box=(new_x,new_y,new_x+bw,new_y+bh)
            center_x=new_x+bw/2
            points.append({"time":round(rel,3),
                           "center":round(center_x/width,5),
                           "confidence":round(float(confidence),3)})
            previous=gray
            rect=(round(new_x),round(new_y),round(new_x+bw),round(new_y+bh))
            prev_points=_features(gray,rect)
            if match is not None and confidence>.64:
                # Adaptive template prevents drift when a flat animation changes pose.
                roi=gray[rect[1]:rect[3],rect[0]:rect[2]]
                if roi.shape==template.shape:
                    template=cv2.addWeighted(template,.9,roi,.1,0)
        if len(points)<2:raise RuntimeError("Could not reliably track selected region.")
        log(f"Universal object tracking: {len(points)} samples / "
            f"{points[-1]['time']-begin:.1f}s, stopped at scene boundary if present.")
        return {
            "start":begin,"end":points[-1]["time"],
            "seed":(round(float(x_fraction),4),round(float(y_fraction),4)),
            "bbox":[round(float(x),5) for x in bbox],
            "points":points,"method":"optical-flow+template-match",
            "source_width":width,"object_type":"visual-region",
            "original_center":round(((x0+x1)/2)/width,4)
        }
    finally:
        cap.release()

def tracked_center(data,t):
    """Interpolate saved generic-object focus positions for the 9:16 crop."""
    for track in reversed(data.get("subject_tracks",[])):
        pts=track.get("points",[])
        if not pts or not float(track["start"])<=t<=float(track["end"]):
            continue
        left=pts[0];right=pts[-1]
        for i,p in enumerate(pts):
            if float(p["time"])>=t:
                right=p
                left=pts[max(0,i-1)]
                break
        span=max(.001,float(right["time"])-float(left["time"]))
        weight=max(0,min(1,(t-float(left["time"]))/span))
        return (float(left["center"])+(float(right["center"])-float(left["center"]))*weight)*float(data["width"])
    return None
