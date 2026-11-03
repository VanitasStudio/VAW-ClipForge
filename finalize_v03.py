from pathlib import Path
p=Path(__file__).with_name("clipforge_gui.py")
s=p.read_text(encoding="utf-8")
s=s.replace('        self.src=tk.StringVar()',
'''        default_source=Path.home()/"Downloads"/"videoplayback.mp4"
        self.src=tk.StringVar(value=str(default_source) if default_source.exists() else "")''')
s=s.replace(
'''                self.messages.put(("done",f"Export complete: {len(outcome['clips'])} clips\n{dest}"))''',
'''                failures=len(outcome.get("sections_failed",[])) if ai else 0
                note=f" ({failures} analysis sections skipped)" if failures else ""
                self.messages.put(("done",f"Export complete: {len(outcome['clips'])} clips"+note+f"\n{dest}"))''')
p.write_text(s,encoding="utf-8")
doc=Path(__file__).with_name("README.md")
doc.write_text("""# VAW ClipForge v0.3 — AI Clipping + Local Auto-Captions

## Use now
Run the Desktop shortcut **VAW ClipForge**.
The previously tested local source video may be pre-filled; change it if desired.

1. Choose a video you own or have rights to repurpose.
2. Highlight Detection: **Gemini AI (audio)**.
3. Recommended: 3 clips, 30 seconds, blurred background.
4. AI analyzes sample frames too: ON (better visual context, but uploads four small stills per analyzed section).
5. Local auto-caption: ON. Burn captions into Shorts: ON.
6. Click GENERATE CLIPS, review the privacy/cost notice, and allow processing.
7. Open Exports -> video-name subfolder. Review MP4, SRT and ai-highlights.json.

## Reliability fixes
- Structured JSON output schema and extra response token budget to prevent truncated responses.
- Gemini 3.6 Flash defaults; Gemini 3.5 Flash-Lite fallback for temporary 503, 502, 504 and malformed output.
- If one of six sections fails, valid previous section results remain usable and will export.
- Successful section analysis is saved in analysis-progress.json to avoid repeat API charges on rerun.
- AI scoring uses spoken hook, context independence, payoff and speech clarity. Four sparse video frames provide visual context (not full video comprehension).
- Caption transcription uses local faster-whisper base model on Windows CPU; subtitles rendered via FFmpeg.
- No automatic YouTube upload, no delete of original, no API key in logs.
- User's Gemini key is encrypted using Windows account DPAPI.

## Limits
- Long video analysis samples up to six four-minute audio sections; for videos longer than 24 minutes some sections are skipped.
- Even multimodal sparse frame sampling can miss brief or purely visual gaming highlights.
- Whisper can mishear words or fail on background music; proofread subtitles before publishing.
- A section may take two requests on failure. Gemini costs or quota may apply depending on API account tier.
- Generated clips are 720x1280 MP4, not yet full OpusClip face tracking.
- Reusing third-party videos needs permission and must meet YouTube originality requirements.
""",encoding="utf-8")
print("GUI/documentation finalized")
