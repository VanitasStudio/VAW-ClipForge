# UI/UX work for v1.2

This is part of the v1.2 build, not a polish pass to squeeze in at the end.

## What needs to improve

- Make the first screen explain the next step without asking users to understand the processing pipeline.
- Keep source selection, output destination and the main action easy to find.
- Put advanced controls behind clear sections; preserve settings that users have already chosen.
- Present Standalone Highlights and Story Composer as two production choices, with both Story Composer strategies available together.
- Show progress in plain language. Separate downloading, transcription, visual analysis, story planning and rendering so a slow stage is not mistaken for a frozen app.
- Give failures a useful explanation and a clear recovery action. Keep logs available without making the main screen look like a developer console.
- Make Review Studio feel like an editor: preview first, timeline second, clip details and captions close at hand.
- Keep destructive actions explicit. Never silently overwrite source files or previous exports.

## Planned screens

1. **Home / New Project** — choose a local file or public video URL, review source details, choose output folder.
2. **Production** — choose Standalone Highlights, Smart Compilation and Narrative Reconstruction; default all three on, with independent toggles.
3. **Processing** — stage-based progress, elapsed time, current task, cancellation and partial-result status.
4. **Review Studio** — video preview, multi-segment timeline, segment list, subtitle editor, transition controls and rerender action.
5. **Export Summary** — show each finished output, its strategy, duration, resolution and file location.

## UI behavior rules

- One obvious primary action per screen.
- Do not expose internal enum names, filenames or model jargon in normal user-facing copy.
- Use consistent spacing, alignment, typography, button hierarchy and focus states.
- Empty, loading, disabled, warning, error and success states must all be designed.
- Keyboard navigation and readable contrast are required.
- Keep the current v1.1 workflow available until the v1.2 path passes regression tests.

## Acceptance checks

- A first-time user can identify where to add a video and how to start without reading documentation.
- Users can tell which production outputs are enabled before starting.
- Progress text identifies the current stage and does not jump backward.
- Partial success is shown accurately when one engine fails but another finishes.
- Review Studio can inspect and edit a multi-segment EDL without losing the original source ranges.
- All UI copy reads naturally and describes what the app actually does.
