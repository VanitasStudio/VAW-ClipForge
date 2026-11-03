# VAW ClipForge v0.9 — Context-Aware Intelligent Clipping

Installed on VAWRIEL-PC — 2026-11-03.

## Features
- Reworked Gemini prompt around complete mini-stories: Hook → Context → Payoff.
- Added structured story metadata: hook, context, payoff, complete flag, reason and title.
- Replaced fixed-duration centering with variable-duration selection.
- Target seconds now acts as a soft preference in Gemini mode.
- Added local Whisper full-source transcription for natural sentence boundaries.
- Added a local boundary cache keyed to source path, file size, modified timestamp and model.
- Added 12-second overlap between Gemini analysis windows to preserve story context across section seams.
- Start/end timestamps are aligned to sentence boundaries where possible.
- 12–180 seconds is the supported short-form range.
- Clips exceeding 180 seconds are skipped rather than forcibly truncated; the model must propose independent story beats.
- GUI includes a default-enabled Context-aware duration checkbox and labels the seconds field TARGET SEC (SOFT).
- Offline Audio Activity mode remains fixed-duration and logs this distinction.

## QA
- Python compile passed for smart_duration.py, gemini_highlights.py, clipforge_gui.py and smart_reframe.py.
- Synthetic sentence alignment test passed: 30-second target produced a natural 14.58-second clip.
- Variable-duration selection without Whisper preserved a 45-second candidate rather than forcing 30 seconds.
- Over-180-second story candidate is rejected instead of truncated.
- Real local Whisper test on samples/spoken-test.mp4 found 40 words and 5 utterance boundaries.
- End-to-end mocked Gemini pipeline selected 2.2–14.42 seconds (12.22 seconds) for a 30-second soft target, aligned at both sentence boundaries.
- No live Gemini API request was made during QA.
- Existing export folders and source files were preserved.

## Current app behavior
- Existing ClipForge GUI process must be restarted to load v0.9.
- Existing exports remain unchanged.
- Next Gemini run uses a new semantic-story-v09 analysis fingerprint and will re-analyze rather than reuse v0.8 candidate cache.
