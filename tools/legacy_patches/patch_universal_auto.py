"""Universal frame composition for auto-clipping; keep old fallback layout."""
from pathlib import Path
p=Path(__file__).with_name("smart_reframe.py")
s=p.read_text(encoding="utf-8")
s=s.replace('"""VAW ClipForge v0.4: scene-aware person/motion 9:16 reframing.','"""VAW ClipForge v0.7: scene-aware universal 9:16 reframing.')
s=s.replace('def frame_centers(segment,cut_times,log=print):','def frame_centers(segment,cut_times,log=print,subject_mode="universal"):')
a=s.index('        target=base_center;mode="center"')
b=s.index('        target=max(crop_w/2,min(width-crop_w/2,target))',a)
replace=r'''        target=base_center;mode="center"
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
            previous=small
'''
s=s[:a]+replace+s[b:]
s=s.replace('def smart_render(segment,output,auto=True,scenes=True,layout="blur",log=print):',
            'def smart_render(segment,output,auto=True,scenes=True,layout="blur",subject_mode="universal",log=print):')
s=s.replace('''        width,height,positions,counts,kind=frame_centers(segment,cuts,log)''',
            '''        width,height,positions,counts,kind=frame_centers(segment,cuts,log,subject_mode=subject_mode)''')
s=s.replace('''            meta["mode"]="scene-aware-face-motion"''',
            '''            meta["mode"]="scene-aware-"+subject_mode''')
s=s.replace('''    meta={"mode":"blur" if not auto else "auto","scene_cuts":[],"focus_samples":[]}''',
            '''    meta={"mode":"blur" if not auto else "auto","scene_cuts":[],
          "focus_samples":[],"subject_mode":subject_mode}''')
s=s.replace('''               captions=True,burn=True,style="modern",layout="blur",log=print):''',
            '''               captions=True,burn=True,style="modern",layout="blur",
               subject_mode="universal",log=print):''')
s=s.replace('''                        "auto_captions":captions,"burn":burn,"caption_style":style},''',
            '''                        "auto_captions":captions,"burn":burn,
                        "caption_style":style,"subject_mode":subject_mode},''')
s=s.replace('''                                            scenes=scenes,layout=layout,log=log)''',
            '''                                            scenes=scenes,layout=layout,
                                            subject_mode=subject_mode,log=log)''')
p.write_text(s,encoding="utf-8")
print("Automatic tracking modes added:",["universal","people","motion","center"])
