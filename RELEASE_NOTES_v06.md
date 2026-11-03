# VAW ClipForge v0.6 - Subtitle Modes + Audio/Scene/Subject Review

Updated November 3, 2026 on VAWRIEL-PC.
Project: D:\YouTubeAutomation\VAW-ClipForge

## Launch
- VAW ClipForge shortcut: generate clips using Gemini or offline audio scoring; Caption Style dropdown and Browse Subtitle Modes.
- VAW Review Studio shortcut: edit existing v0.4 ClipForge output with the original source.

## Six subtitle presets
- Karaoke: white captions, crimson active-word highlight.
- Bold Pop: big uppercase, black outline, yellow word.
- Minimal: restrained white, no per-word highlight.
- Gaming: bright white/cyan with lime highlight.
- Neon: white with pink glow.
- Creator: white with orange accents.
All six render in the automatic caption generator AND Review Studio. Preview gallery is available in both applications.

## Review Studio new functionality
- Play with Audio: audio from original local video via Windows WAV playback, frames driven by audio clock. This is approximate preview, not sample-accurate playback.
- Edit transitions: set Hard Cut or Soft Dip per scene boundary. Audio continuous.
- Lock Subject: choose a subject in source preview, OpenCV optical-flow follows the clicked region for up to 4 sec (stops at scene cut); can revert to manual framing pins.
- Caption Timeline: edit text/timing, choose subtitle preset.
- Save Draft and EXPORT EDITED MP4: new filenames, source untouched.

## Verified
- All 6 caption presets generated ASS.
- Local Whisper + Bold Pop successfully generated and burned subtitles into synthetic speech video.
- Audio preview PlaySound clock tested, with a brief test clip.
- Subject tracking produced seven points over 1.2sec in source demo.
- Scene soft dip + Gaming subtitle + track rendered successfully in local 6sec preview.
- MP4 decode successful.
- No new Gemini API request made for v0.6 testing.
- Main source videoplayback.mp4 unchanged.

## Limitations
- Audio sync is approximate and may lag under CPU load. Verify with Media Player before publish.
- Subject track is motion/optical-flow based, not semantic identity recognition; occlusion and rapid cuts can fail.
- Transitions currently Hard Cut / Soft Dip only.
- Automatic transcript may mishear technical/medical terms.
- Third-party videos still require relevant reuse rights and meaningful transformation for platform monetization.
