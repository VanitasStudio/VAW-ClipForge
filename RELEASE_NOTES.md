# VAW ClipForge v1.2.1 — Vanitas UI, Controls & Reliability

This release builds on the v1.2 Vision-Aware Story Editing foundation.

## Editorial production
- Unified local-first source analysis feeds standalone highlights and two Story Composer strategies.
- Smart Compilation and Narrative Reconstruction generate separate editable EDLs.
- Composition rendering creates one vertical MP4 per story strategy, with caption sidecars and Review Studio round-tripping.
- Optional Video Vision MCP frame extraction is isolated behind a provider adapter, bounded to a small local frame budget and disabled by default.
- Visual evidence is fused into editorial events without duplicating the local Whisper pipeline.

## Publishing assistance
- Each export run creates one Title and Hashtag Suggestion.md file.
- Each successfully rendered clip receives three title options, one recommendation and relevant hashtags.
- Gemini suggestions are generated only when AI is enabled for that job. Offline or failed requests use local suggestions.
- Suggestions use clip-specific metadata and the transcript excerpt overlapping that clip.

## Vanitas Studio interface
- Added a fully custom dropdown popup with pointer and keyboard selection.
- Replaced Windows-native scrollbar rendering with a Canvas-drawn chamfered Vanitas scrollbar.
- Added chamfered action buttons, custom numeric steppers, geometric checkboxes and Canvas-rendered sliders.
- Applied the shared Archivo / Quantico typography and Vanitas palette across the main workspace and Review Studio windows.
- Fixed dropdown selection event ordering and popup focus handling.
- Added runtime interaction tests for dropdowns, scrollbars, steppers, checkboxes and buttons.
- Corrected malformed punctuation in Composition Review UI.

## Repository
- Current release notes are consolidated here; historical v0.6–v1.1 notes are archived under docs/archive/releases/.
- QA, product documentation, setup scripts, diagnostics and legacy patches are grouped by purpose.
- Local media, model caches, generated exports, backups and build artifacts are excluded from Git.
- Added contributor guidance, security reporting guidance and GitHub issue / pull-request templates.

## Windows application
- Launch dist/VAW-ClipForge.exe.
- Build from source with scripts/build_windows.ps1.
- Run the supported regression suite with scripts/run_qa.ps1.

See docs/VANITAS_BRAND_UI.md and docs/REPOSITORY_STRUCTURE.md for the design and repository conventions.
