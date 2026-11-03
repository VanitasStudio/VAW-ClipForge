# UI/UX work for v1.2

This is part of the v1.2 build, not a polish pass to squeeze in at the end.

## Implemented production workflow

- Source selection, destination and the primary action remain visible in the desktop shell.
- Production outputs are independently selectable: Standalone Highlights, Story Composer — Smart Compilation and Story Composer — Narrative Reconstruction. All three default to enabled.
- Story Composer has a soft target duration from 12 to 180 seconds. Complete source moments are never shortened just to meet the target.
- Smart Processing includes an optional Video Vision MCP toggle, off by default.
- The existing v1.1 Standalone Highlights path remains available and is still covered by regression tests.
- Processing logs identify source import, local frame extraction, story planning, segment rendering and export. A failure in one requested output does not discard other successful outputs.
- Review / Timeline opens the multi-segment Composition Review Studio when a Story Composer EDL exists.

## Composition Review Studio

- Horizontal multi-segment timeline with role labels and segment selection.
- Source-frame preview at the selected segment's source-in timestamp.
- Editable source in/out points and editorial roles.
- Editable transcript caption text, saved back to the local analysis bundle.
- Caption preset, uppercase, burn-in and SRT export controls.
- Hard-cut and cross-dissolve transitions, plus smart audio crossfade control.
- EDL validation before saving or rendering.
- Non-destructive revision rendering; original source and prior exports are preserved.

## Vision Intelligence controls

- Optional Video Vision MCP installation through setup_video_vision_mcp.ps1.
- The MCP checkbox is independent of the built-in visual-analysis setting and is disabled by default.
- The adapter uses bounded local targeted-timestamp frame extraction, not the upstream unbounded scene-extraction mode.
- Local Whisper remains the only transcript source; the MCP transcript tools are not invoked.
- Missing provider, malformed response, extraction failure or invalid frames fall back to ClipForge's built-in sampler.

## UI behavior rules

- One obvious primary action per screen.
- Do not expose internal enum names, filenames or model jargon in normal user-facing copy.
- Use consistent spacing, alignment, typography, button hierarchy and focus states.
- Empty, loading, disabled, warning, error and success states must all be designed.
- Keyboard navigation and readable contrast are required.
- Never silently overwrite source files or previous exports.

## Acceptance checks

- A first-time user can identify where to add a video and how to start without reading documentation.
- Users can tell which production outputs are enabled before starting.
- Progress text identifies the current stage and does not jump backward.
- Partial success is shown accurately when one output fails but another finishes.
- Review Studio can inspect and edit a multi-segment EDL, source ranges, captions and transitions.
- All UI copy reads naturally and describes what the app actually does.
