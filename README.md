# VAW ClipForge v1.1 — AI Editorial Studio

A local-first desktop tool for finding complete, story-led moments and exporting vertical 9:16 clips.

## v1.1 interface refresh
- Reorganized controls into five clear sections: Source Video, Clip Settings, AI Highlight Engine, Smart Processing and Subtitle Style.
- Added a scrollable settings area while keeping Generate Clips, export/review actions and activity log visible.
- Increased spacing and control sizes, improved dark theme contrast, and added consistent hover states.
- Renamed technical labels into clearer user-facing language without changing the processing pipeline.
- Subtitle picker now shows readable preset names rather than internal IDs.

## New subtitle mode: All Capital Subtitle
- Adds an explicit All Capital Subtitle preset to the subtitle gallery and main selector.
- Forces every spoken word to uppercase while retaining word-by-word highlight timing.
- Applies to both burned-in ASS captions and the exported SRT sidecar.
- Uses bold white text with a yellow highlighted word and a dark outline.
- Existing Karaoke, Bold Pop, Minimal, Gaming, Neon and Creator modes remain available.

## AI editorial intelligence
- Gemini evaluates Hook, Context and Payoff plus eight editorial dimensions.
- Visual categories include animation, illustration, infographic, diagram, screen recording, live action, mixed media and unknown.
- Visual notes describe generic visible subjects and objects; no identity recognition is performed.
- Deterministic weighted scoring compares valid candidates and avoids overlapping selections.
- Retention potential is an editorial estimate, not a prediction of views or watch time.
- Local HTML Editorial Report shows ranking, scores, story structure, visual notes, retention risks and edit suggestions.

## Smart processing
- Context-aware duration uses local Whisper sentence boundaries; the duration target is soft.
- Auto-reframe supports universal objects, people, motion and center modes.
- Intelligent scene detection can reset focus at visual transitions.
- Output quality supports 720p and 1080p vertical export.
- URL input downloads one authorized public video to a reusable local cache.
- No automatic publishing.

## Quick workflow
1. Choose Local File or Video URL.
2. Set clip count, soft target duration, output quality and vertical layout.
3. Choose Gemini AI (audio) and a model; configure and test the API key if needed.
4. Enable visual analysis, auto-captions, context-aware duration, auto-reframe and scene detection as required.
5. Select a subtitle mode, including All Capital Subtitle.
6. Click Generate Clips.
7. Inspect the exports in Review / Timeline and compare candidates in Editorial Report.

## Privacy and limitations
- Gemini receives compressed audio and optional sparse timestamped frames only after confirmation.
- Whisper transcription and sentence-boundary alignment stay local.
- The local HTML report has no external scripts, CDN, analytics or network calls.
- Sparse frame sampling is not continuous video understanding; visual events between sampled frames may be missed.
- Always review the final clip and captions before publishing.
- Only use videos you own or have permission to repurpose.
