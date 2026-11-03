"""VAW ClipForge v0.7: scene-aware universal 9:16 reframing.

Detects cuts with PySceneDetect, detects faces with OpenCV Haar cascade, tracks
scene motion/visual saliency when no face is available, smoothly changes crop X
using FFmpeg sendcmd. Keeps audio synchronized and original video untouched.
"""
from __future__ import annotations
import json
import math
import os
import subprocess
from clipforge.silent_process import run as silent_run, popen as silent_popen
import tempfile
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from scenedetect import ContentDetector, SceneManager, open_video
from clipforge.clip_engine import FFMPEG, filter_graph, probe_duration, OUTPUT_SIZES
from clipforge.local_performance import video_encoder_args
from clipforge.stylish_captions import polish_clip

SIZE=(720,1280)
FACE_CASCADE=cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml")

def extract_local_segment(source,start,seconds,target,log=print):
    cmd=[FFMPEG,"-hide_banner","-loglevel","error","-y",
         "-ss",f"{start:.3f}","-i",str(source),"-t",f"{seconds:.3f}",
         *video_encoder_args(FFMPEG,20),
         "-c:a","aac","-b:a","128k","-movflags","+faststart",str(target)]
    p=silent_run(cmd,capture_output=True,text=True,timeout=420)
    if p.returncode:
        raise RuntimeError("Could not prepare source clip: "+p.stderr[-350:])

def shot_boundaries(segment,log=print):
    """Detect scene cuts efficiently while retaining useful cut precision."""
    video=None
    try:
        from time import perf_counter
        from clipforge.local_performance import detect_local_performance
        profile=detect_local_performance()
        cv2.setNumThreads(profile.opencv_threads)
        started=perf_counter()
        video=open_video(str(segment),backend="opencv")
        manager=SceneManager()
        manager.add_detector(ContentDetector(threshold=29,min_scene_len=12))
        # 15 fps sampling is sufficient for editorial cut boundaries and halves
        # decode work compared with scanning every frame of a 30 fps source.
        processed=manager.detect_scenes(video,frame_skip=1,show_progress=False)
        scenes=manager.get_scene_list()
        cuts=[float(scene[0].get_seconds()) for scene in scenes][1:]
        log(f"Scene analysis ready: {len(cuts)} cuts from {processed} sampled frames in {perf_counter()-started:.1f}s.")
        return cuts
    except Exception as exc:
        log(f"Scene detector unavailable ({type(exc).__name__}); tracking without cuts.")
        return []
    finally:
        if video is not None:
            try:
                video.close()
            except Exception:
                pass

def frame_centers(segment,cut_times,log=print,subject_mode="universal"):
    cap=cv2.VideoCapture(str(segment))
    if not cap.isOpened():raise RuntimeError("Cannot decode clip for tracking.")
    width=round(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height=round(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps=cap.get(cv2.CAP_PROP_FPS) or 30
    if width<=0 or height<=0:
        cap.release();raise RuntimeError("Invalid source dimensions")
    portrait=width/height<=9/16+0.03
    crop_w=min(width,int(height*9/16))
    if crop_w%2:crop_w-=1
    if portrait or crop_w<4:
        cap.release()
        log("Portrait source detected: preserving full frame, no forced zoom.")
        return width,height,[],[], "preserve"
    stride=max(1,round(fps/5))
    pos=0;previous=None;smoothed=width/2
    cut_index=0;track=[];modes=[]
    base_center=width/2
    max_left=width-crop_w
    while True:
        ok,frame=cap.read()
        if not ok:break
        if pos%stride:
            pos+=1;continue
        t=pos/fps
        gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        # Work on small frame for speed; face cascade on full-ish greyscale.
        resize=cv2.resize(gray,(320,max(24,round(height*320/width))))
        scaled=320/width
        faces=(FACE_CASCADE.detectMultiScale(resize,scaleFactor=1.15,
                  minNeighbors=5,minSize=(max(18,int(35*scaled)),max(18,int(35*scaled))))
               if subject_mode=="people" else [])
        reset=False
        while cut_index<len(cut_times) and t>=cut_times[cut_index]:
            reset=True;cut_index+=1
        target=base_center;mode="center"
        if subject_mode=="center":
            previous=cv2.resize(gray,(160,max(20,int(height*160/width))))
        elif subject_mode=="people" and len(faces):
            # Explicit people mode is the only mode that prioritizes faces.
            ranked=sorted(faces,key=lambda box:
                (float(box[2]*box[3])-0.35*abs((box[0]+box[2]/2)/scaled-smoothed)),
                reverse=True)
            fx,fy,fw,fh=ranked[0]
            target=(fx+fw/2)/scaled
            mode="face"
            previous=cv2.resize(gray,(160,max(20,int(height*160/width))))
        else:
            # Generic content scoring for cartoons, illustrated objects,
            # infographic highlights, maps and moving diagrams; NO identity.
            small=cv2.resize(gray,(160,max(20,int(height*160/width))))
            rgb=cv2.resize(frame,(160,small.shape[0]))
            hsv=cv2.cvtColor(rgb,cv2.COLOR_BGR2HSV)
            visible=small[int(small.shape[0]*.1):int(small.shape[0]*.89)]
            color=hsv[int(small.shape[0]*.1):int(small.shape[0]*.89),:,1]
            motion_col=np.zeros(160,np.float32)
            moving=False
            if previous is not None and previous.shape==small.shape and not reset:
                prior=previous[int(small.shape[0]*.1):int(small.shape[0]*.89)]
                diff=cv2.absdiff(visible,prior)
                moving_mask=(diff>22).astype(np.float32)
                motion_col=moving_mask.mean(axis=0).astype(np.float32)
                moving=float(np.mean(moving_mask))>.005
            edge_col=(cv2.Canny(visible,50,130)>0).astype(np.float32).mean(axis=0)
            saturation=(color.astype(np.float32)/255.0).mean(axis=0)
            # Ignore over-bright white slide background unless contrast/motion.
            if subject_mode=="motion":
                signal=motion_col.copy()
            else:
                signal=(motion_col*.65 if moving else np.zeros(160,np.float32))
                signal+=edge_col*.32+saturation*.13
            signal=cv2.GaussianBlur(signal.reshape(1,-1),(1,1),0).reshape(-1)
            window=max(2,int(crop_w*160/width))
            sums=np.convolve(signal,np.ones(window,dtype=np.float32)/window,mode="valid")
            if len(sums) and float(sums.max())>.001:
                mids=np.arange(len(sums),dtype=np.float32)+window/2
                previous_mid=smoothed*160/width
                # Penalize unmotivated jump to another icon/character.
                score=sums-.10*np.abs(mids-previous_mid)/80*max(.01,float(sums.max()))
                score-=.035*np.abs(mids-80)/80*max(.01,float(sums.max()))
                at=int(np.argmax(score))
                target=(at+window/2)*width/160
                mode=("motion" if moving else "graphic")
                # Static slides should not drift just because there is small text.
                if not moving and abs(target-smoothed)>crop_w*.48:
                    target=smoothed
                    mode="hold"
            else:
                target=smoothed if not reset else base_center
                mode="center"
            # A compact moving region is a better subject cue than a face
            # detector or the static center of the slide.
            if moving and subject_mode in ("universal","motion"):
                strong=motion_col>max(.012,float(motion_col.max())*.23)
                if np.any(strong) and np.count_nonzero(strong)<80:
                    weights=motion_col**2
                    if float(weights.sum())>.001:
                        moving_center=float(np.dot(np.arange(160),weights)/weights.sum())
                        target=moving_center*width/160
                        mode="object-motion"
            previous=small
        target=max(crop_w/2,min(width-crop_w/2,target))
        if reset:
            smoothed=target
        else:
            # limit movement and low-pass jitter to protect watchability
            delta=np.clip(target-smoothed,-40,40)
            smoothed+=0.37*delta
        x=max(0,min(max_left,round(smoothed-crop_w/2)))
        if x%2:x-=1
        track.append((t,x))
        modes.append(mode)
        pos+=1
    cap.release()
    if not track:track=[(0,round((width-crop_w)/2))]
    counts={name:modes.count(name) for name in set(modes)}
    log(f"Tracking: {len(track)} samples; {counts}; horizontal crop {crop_w}/{width}.")
    return width,height,track,counts,"tracking"

def smart_render(segment,output,auto=True,scenes=True,layout="blur",
                 subject_mode="universal",resolution="1080p",log=print):
    segment=Path(segment).resolve()
    output=Path(output).resolve()
    if resolution not in OUTPUT_SIZES:
        raise ValueError("Invalid output resolution")
    out_w,out_h=OUTPUT_SIZES[resolution]
    meta={"mode":"blur" if not auto else "auto","scene_cuts":[],
          "focus_samples":[],"subject_mode":subject_mode,
          "output_resolution":f"{out_w}x{out_h}"}
    if not auto:
        vf=filter_graph(layout,resolution=resolution)
        meta["mode"]=layout
        cmds=None
    else:
        cuts=shot_boundaries(segment,log) if scenes else []
        width,height,positions,counts,kind=frame_centers(segment,cuts,log,subject_mode=subject_mode)
        meta["scene_cuts"]=cuts
        meta["tracking_sources"]=counts
        meta["focus_samples"]=positions[::max(1,len(positions)//90)]
        if kind=="preserve":
            vf=(f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,"
                f"pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2:black,"
                "setsar=1,format=yuv420p")
            meta["mode"]="portrait-preserve"
            cmds=None
        else:
            crop_width=min(width,int(height*9/16))
            crop_width-=crop_width%2
            # Dynamic crop commands are applied on the trim's own timebase.
            cmdfile=output.with_suffix(".tracking.txt")
            cmdfile.write_text("".join(
                f"{max(0,t):.3f} crop@track x {int(x)};\n" for t,x in positions),
                encoding="ascii")
            first_x=positions[0][1]
            vf=(f"sendcmd=f={cmdfile.name},"
                f"crop@track=w={crop_width}:h={height}:x={first_x}:y=0,"
                f"scale={out_w}:{out_h},setsar=1,format=yuv420p")
            cmds=cmdfile
            meta["mode"]="scene-aware-"+subject_mode
    output.parent.mkdir(parents=True,exist_ok=True)
    cmd=[FFMPEG,"-hide_banner","-loglevel","error","-y","-i",str(segment),
         "-vf",vf,"-r","30",*video_encoder_args(FFMPEG,22),
         "-c:a","aac","-b:a","128k","-movflags","+faststart",str(output)]
    p=silent_run(cmd,cwd=str(output.parent),capture_output=True,text=True,timeout=600)
    if p.returncode:
        raise RuntimeError("Smart-reframe render failed: "+p.stderr[-650:])
    if cmds and cmds.exists():cmds.unlink(missing_ok=True)
    log("Rendered tracking mode: "+meta["mode"])
    return meta

def export_v04(source,export_dir,picks,auto=True,scenes=True,
               captions=True,burn=True,style="modern",layout="blur",
               subject_mode="universal",resolution="1080p",log=print):
    source=Path(source).resolve()
    dest=Path(export_dir).resolve()
    dest.mkdir(parents=True,exist_ok=True)
    result={"version":"0.4","source":str(source),"created":datetime.now().isoformat(),
            "settings":{"auto_reframe":auto,"scene_detection":scenes,
                        "auto_captions":captions,"burn":burn,
                        "caption_style":style,"subject_mode":subject_mode,
                        "resolution":resolution},
            "clips":[]}
    for i,pick in enumerate(picks,1):
        start=float(pick["start"])
        seconds=float(pick["duration"])
        stem=f"{source.stem}_v04_{i:02d}_{round(start):05d}s"
        outfile=dest/f"{stem}.mp4"
        revision=2
        while outfile.exists():
            outfile=dest/f"{stem}_rev{revision}.mp4"
            revision+=1
        item={**pick,"output":str(outfile)}
        log(f"V04 clip {i}/{len(picks)} at {start:.1f}-{start+seconds:.1f}s")
        try:
            with tempfile.TemporaryDirectory(prefix="vaw-v04-") as temporary:
                segment=Path(temporary)/"segment.mp4"
                extract_local_segment(source,start,seconds,segment,log)
                item["visual"]=smart_render(segment,outfile,auto=auto,
                                            scenes=scenes,layout=layout,
                                            subject_mode=subject_mode,
                                            resolution=resolution,log=log)
            if captions:
                try:
                    item["caption"]=polish_clip(outfile,style,burn=burn,log=log)
                except Exception as exc:
                    item["caption_error"]=str(exc)[:220]
                    log("Caption failed; MP4 retained without captions.")
            item["ok"]=outfile.is_file() and outfile.stat().st_size>0
        except Exception as exc:
            item["ok"]=False
            item["error"]=str(exc)[:250]
            log(f"Clip {i} failed, other clips continue: {str(exc)[:170]}")
        result["clips"].append(item)
        (dest/"v04-manifest.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    return result
