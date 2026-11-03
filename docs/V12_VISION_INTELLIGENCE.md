# VAW ClipForge v1.2 — Vision Intelligence Integration

## Decision

Integrate OAMaestro/video-vision-mcp as an optional local frame-extraction provider. Do not make it a mandatory runtime dependency and do not use its combined transcript/AI analysis path.

Pinned upstream revision: cb854278518c46943a5b9e89643f2e29c7aca839
License: MIT
Upstream package version: 0.1.0

## Why this integration is bounded

The upstream MCP exposes analyze_video, extract_frames, get_video_info, get_transcript, transcribe_audio, extract_frame_at, create_frame_grid and cleanup.

ClipForge already owns the local Whisper transcript pipeline and scene-boundary analysis. Calling the MCP analyze_video or transcribe_audio paths would duplicate work and could create inconsistent transcript boundaries. The upstream raw scene extraction path also does not enforce max_frames in its low-level extractor.

ClipForge therefore calls only extract_frames in targeted timestamp mode. The adapter generates an explicit evenly distributed timestamp list, caps the request at eight frames, and validates every returned path against its temporary output directory. The existing local PySceneDetect stage remains responsible for scene boundaries.

## Runtime architecture

~~~text
Local source file
      |
      +--> ClipForge local Whisper / sentence boundaries
      |
      +--> ClipForge PySceneDetect scene boundaries
      |
      +--> Optional Video Vision MCP
                |
                +--> extract_frames (targeted timestamp mode)
                +--> bounded temporary JPEG frames
                +--> local cache + quality filter
      |
      v
Gemini editorial analysis
  compressed audio + sparse selected frames only
      |
      v
AnalysisBundle
  transcript + scenes + events + visual evidence timestamps
      |
      +--> Standalone Highlights
      +--> Story Composer — Smart Compilation
      +--> Story Composer — Narrative Reconstruction
      |
      v
EDL -> segment renderer -> smart audio join -> captions -> Review Studio
~~~

## Privacy rules

- The MCP server receives a local filesystem path only.
- The adapter does not pass online URLs, cookies, credentials or API keys to the MCP server.
- The adapter calls extract_frames only. It does not call transcript, Whisper, analyze_video or any cloud model.
- Temporary frame files are removed after extraction.
- The cache is stored under LocalAppData, keyed by source path, size, modification time and frame budget, and capped at 1 GB.
- Gemini receives only the compressed audio and selected sparse frame images after the existing explicit user consent prompt.
- Full source video and full transcript remain local.
- If the provider is unavailable, invalid or returns unusable frames, the existing built-in frame sampler remains active.

## Installation and dependency audit

The README's @oamaestro/video-vision-mcp package name is not currently available from the npm registry. The setup script clones the pinned GitHub revision to:

%LOCALAPPDATA%\VanitasStudio\ClipForge\video-vision-mcp

The setup script:
1. Requires Git and Node.js 20.9+.
2. Checks out the pinned revision.
3. Applies compatible dependency updates for sharp, uuid and qs.
4. Runs npm install and npm audit fix without forcing major-version changes.
5. Requires the production dependency audit to pass.
6. Builds the TypeScript server.
7. Writes a local install manifest.

The current pinned build passed its production dependency audit with zero reported vulnerabilities. The upstream project emits deprecation warnings for dependencies that are not used by ClipForge's bounded local extraction path.

## User controls

- Desktop checkbox: Extra local frame sampling (Video Vision MCP).
- Default: disabled.
- Requires Gemini AI and the existing AI visual-analysis setting.
- Programmatic opt-in: CLIPFORGE_VIDEO_VISION_ENABLED=1.
- Failure behavior: log the reason and fall back to built-in local frame sampling.

## Tests

- MCP stdio initialize, tools/list and tools/call using a fake server.
- Real MCP handshake against the pinned local server.
- Real local extraction against samples/synthetic-demo.mp4.
- Timestamp parsing and image normalization.
- Frame-budget enforcement, quality filtering and duplicate removal.
- Local cache hit behavior.
- Unified analyzer fusion with event-level visual evidence.
- GUI regression and end-to-end composition rendering.
