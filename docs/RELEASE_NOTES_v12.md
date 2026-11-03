# VAW ClipForge v1.2 — Vision-Aware Story Editing

## Production
- Unified local-first source analysis feeds standalone highlights and two Story Composer strategies.
- Smart Compilation and Narrative Reconstruction generate separate editable EDLs.
- Composition renderer creates one vertical MP4 per story strategy, with caption sidecars and Review Studio round-tripping.
- Optional Video Vision MCP frame extraction is isolated behind a provider adapter, bounded to a small local frame budget and disabled by default.
- Visual evidence is fused into editorial events without duplicating the local Whisper pipeline.

## Publishing assistance
- Each export run creates one Title and Hashtag Suggestion.md file.
- Every successfully rendered standalone clip and every Story Composer segment receives three short title options, one recommended title and relevant hashtags.
- Gemini suggestions are generated only when the user has enabled AI for that job. Offline or failed AI requests fall back to local suggestions.
- Suggestions use only clip-specific metadata and the transcript excerpt overlapping that clip.

## Review Studio
- Multi-segment timeline, source-frame preview, reorder and trim, role editing, caption settings and transition controls.
- Audio continuity settings and non-destructive revision exports.

## Repository
- QA suite moved into tests/.
- Product, UX and release documentation moved into docs/.
- Setup and QA scripts moved into scripts/.
- Historical one-off migration scripts archived in tools/legacy_patches/.
- Runtime modules and launchers remain at the root to preserve import and Windows launcher compatibility.
