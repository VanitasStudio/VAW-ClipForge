# VAW ClipForge v0.7 — Universal Object Tracking

Release date: 2026-11-03
PC: VAWRIEL-PC
Installation: D:\YouTubeAutomation\VAW-ClipForge

## What changed
Object tracking is NOT restricted to faces or human identity. ClipForge does NOT attempt to identify people.
Designed to handle animated documentaries: cartoon characters, machines, vehicles, rockets, icons, diagrams, labels, maps, and moving visual assets.

### Main ClipForge: Automatic Focus
Under AUTO FOCUS, select:
- universal (default): prioritizes localized object motion, contrast, color, and steady visual framing.
- people: face cues first, generic content fallback.
- motion: follows localized changes, without face priority.
- center: holds the central crop.

Universal mode runs locally with OpenCV heuristics. This is not a semantic object recognizer.
The existing Gemini audio/keyframe scoring controls highlight SELECTION, not object identification.
No new upload or Gemini API request is required by subject tracking.

### Review Studio: Track Any Object
1. Open Review / Timeline.
2. Seek to the time where the target first appears.
3. Click **Track Any Object**.
4. On the Source Frame, drag a rectangle around the wanted character, object, chart element, vehicle, or title. Releasing triggers tracking.
5. The offline optical-flow + local template-matching tracker records center positions. One selection follows up to 8 seconds, stopping before a scene cut or when confidence drops.
6. Add another selection after a cut or lost track; use Pin Keyframe for corrections.
7. Save Draft and EXPORT EDITED MP4. Tracking information is saved in .review.json alongside caption changes.

Source media and previous exports are never modified. Rendered output always uses new filenames.

## QA performed
- Synthetic 640x360 animation with moving spacecraft icon, no human faces: 30 tracking samples across 5.8 seconds; position moved from ~0.172 to ~0.609 frame width.
- Automatic Universal mode detected object-motion in 29/30 animation samples and produced a 720x1280 test MP4.
- Review Studio drag selection on an animated documentary clip: 1 generic track, 10 samples, ending at scene cut.
- Three-second non-destructive edit with object tracking + captions rendered and decoded successfully locally.
- All existing subtitle presets and Gemini highlight selection remain available.

## Known limitations
- The tool tracks **pixel regions**, not the semantic identity of a tank, aircraft, person, symbol or narrator topic.
- Repeated identical graphics, low-contrast slides, occlusion, fast transitions, or motion blur can confuse tracking.
- Long clips need more than one Track Any Object selection when scenes change.
- Automatic Universal focus infers the most active area but cannot know which diagram matters to the story. Manual selection remains the precise option.
- Wide diagrams or full-slide text may be better with 9:16 Fit (no cropping) than Universal crop.
- Verify subtitle timing and safe framing before publishing.
