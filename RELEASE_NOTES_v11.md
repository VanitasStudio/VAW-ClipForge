# VAW ClipForge v1.1 — UI Refinement + All Capital Subtitle

Installed on VAWRIEL-PC — 2026-11-04.

## UI changes
- Rebuilt the primary GUI into a structured, dark desktop workspace.
- Added five sections with clear hierarchy and descriptions.
- Added a scrollable settings area; Generate Clips, Open Exports, Review / Timeline, Editorial Report and Activity remain visible.
- Improved typography, contrast, spacing, combobox styling, buttons and hover feedback.
- Increased default window size to 1080x920 and minimum size to 960x760.
- Preserved existing input, export, model, key, URL, processing and report controls.
- Removed the obsolete legacy UI implementation after replacing it.

## Subtitle mode
- Added preset ID all_caps, displayed as "All Capital Subtitle".
- Added it automatically to the main selector and subtitle preview gallery.
- All Capital applies uppercase to ASS rendering and SRT sidecar text.
- Preserves existing word-level timing and animated active-word emphasis.
- Existing six subtitle presets remain unchanged.

## QA
- Python compile passed for GUI, preset, caption and reframe modules.
- Preset registry and unique IDs passed.
- ASS output test confirms "THIS IS THE RESULT".
- Mocked local Whisper export confirms both ASS burn-in source and SRT sidecar contain uppercase text for All Capital.
- Other presets retain their original casing.
- Preview image generation passed for All Capital.
- Tkinter GUI smoke test passed.
- Main selector -> internal preset ID binding passed.
- Existing v1.0 AI editorial and context-duration code was not changed.
- No video source or existing export was modified.

## Files
- clipforge_gui.py
- subtitle_presets.py
- stylish_captions.py
- qa_v11_ui.py
- qa_v11_gui_smoke.py
- README.md
- RELEASE_NOTES_v11.md

## Rollback
Backups were created before edits with timestamp 20261104-002648:
- clipforge_gui.py.bak-20261104-002648
- subtitle_presets.py.bak-20261104-002648
