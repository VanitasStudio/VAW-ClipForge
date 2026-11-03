# VAW ClipForge v1.2.1 — Vision-Aware Story Editing

VAW ClipForge v1.2 builds on the v1.1 local-first desktop editor. It keeps Standalone Highlights and adds two complete Story Composer outputs: Smart Compilation and Narrative Reconstruction. Both story strategies can be enabled together.

## Vanitas Studio identity

The desktop interface follows the Vanitas Studio product language: dark, premium, minimal and editorial.
Archivo is used for functional UI typography; Quantico is reserved for the product wordmark.
The palette is built around Vanitas Blue, platinum and restrained orange accents.
See docs/VANITAS_BRAND_UI.md for the full tokens and UI rules.

## Windows desktop application

The Windows app is packaged as a single-file, windowed executable with the Vanitas app icon and bundled fonts. Build binaries are kept out of the source tree to keep the repository lightweight; attach the executable to a GitHub Release when publishing a desktop version. First-time speech-model use may download the selected Whisper model into the user's Hugging Face cache. The Gemini key remains protected with Windows DPAPI under the current Windows account.

## v1.2 production outputs

- **Standalone Highlights** — separate vertical clips selected from the strongest complete moments.
- **Story Composer — Smart Compilation** — a ranked, varied sequence of complete moments.
- **Story Composer — Narrative Reconstruction** — a coherent sequence that preserves context, prerequisites and payoff.
- Each Story Composer output is a single rendered vertical MP4 with an editable EDL, analysis bundle and caption sidecars.
- The target duration is a soft preference. Complete moments are never shortened to force a target; each composition must remain within 12–180 seconds.
- Smart audio continuity applies short audio crossfades at cuts. Review Studio supports hard cuts and cross-dissolves.

## Vision Intelligence

Video Vision MCP (OAMaestro/video-vision-mcp) is an optional local frame-extraction provider.

- Uses the MCP extract_frames tool with bounded targeted timestamp sampling. The upstream raw scene mode does not enforce its max_frames parameter, so ClipForge deliberately avoids that mode.
- Requests at most 8 additional local frames. The existing ClipForge sampler fills sparse coverage, with a maximum of 12 frames per Gemini analysis window.
- Does not invoke the MCP transcript or Whisper tools. ClipForge's existing local Whisper pipeline remains the only transcript source.
- Frames are compressed and quality-filtered before they are passed into the existing Gemini visual analysis.
- A LocalAppData cache is keyed by source path, size, modification time and frame budget, with a 1 GB size cap.
- The integration is disabled by default. Enable **Extra local frame sampling (Video Vision MCP)** in Smart Processing after installing the optional provider.

### Install the optional provider

The optional provider is maintained separately from the desktop source package. It is disabled by default; the programmatic analyzer can opt in with:

~~~powershell
$env:CLIPFORGE_VIDEO_VISION_ENABLED = "1"
~~~

## Local Performance Engine

ClipForge profiles the local machine before processing. Whisper uses CUDA only when the full CUDA 12 / cuDNN 9 runtime is available, then falls back automatically to bounded CPU `int8` inference if GPU execution is unavailable. Scene detection uses a reduced sampling rate to avoid decoding every frame, and Story Composer rendering, segment preparation and subtitle burn-in use NVIDIA NVENC when the installed FFmpeg passes a real encoder probe. Otherwise, ClipForge uses the software `libx264` encoder. Processing remains local-first; see [Local Performance](docs/LOCAL_PERFORMANCE.md) for runtime behavior and diagnostics.

## Review Studio

- Open **Review / Timeline** after a Story Composer export to open the multi-segment Composition Review Studio.
- Inspect the horizontal composition timeline and source-frame preview.
- Change segment order, source in/out points and segment roles.
- Edit transcript captions, choose caption presets, uppercase/burn-in/SRT settings, hard cuts or cross-dissolves, and smart audio crossfades.
- Save the EDL and analysis bundle without changing the original source.
- Render a new revision; existing exports are never overwritten.

## Quick workflow

1. Choose a local video or a supported public URL.
2. Set Standalone Highlights and/or the two Story Composer outputs.
3. Choose the Story Composer target duration (12–180 seconds).
4. Configure Gemini and confirm the data-sharing prompt.
5. Optionally enable Video Vision MCP after installing it.
6. Choose vertical layout, resolution, reframing and caption settings.
7. Generate, then inspect the outputs in Review / Timeline.

## Title & Hashtag Suggestions

Every export run creates one **Title and Hashtag Suggestion.md** file in the export folder, covering each successfully rendered standalone clip and each Story Composer segment.

- Three short title options are generated per clip, with one recommended title.
- Five to eight relevant hashtags are suggested per clip.
- Suggestions use only that clip's topic, editorial notes and matching transcript excerpt.
- Gemini is used when available in the already-enabled AI workflow. If title generation fails or the run is offline, a local fallback still writes the Markdown report.
- The report is a suggestion, not an automatic publish action. Review titles and claims before posting.

## Repository layout

- `clipforge/` — application modules and processing engines.
- `assets/` — bundled product identity, fonts and runtime assets.
- `docs/` — product, architecture, security and performance documentation.
- `.github/` — issue templates, pull-request template and static validation workflow.

Generated binaries, local model caches, development utilities and historical patch scripts are intentionally excluded from the public source tree. See `docs/REPOSITORY_STRUCTURE.md` and `RELEASE_NOTES.md` for project documentation.

## Privacy and safety

- Original media, Whisper transcription and boundary alignment stay local.
- Video Vision MCP receives only a local file path and writes bounded frame images to a temporary local directory. It does not receive an online URL, cookies or API key from ClipForge.
- The MCP integration uses frame extraction only; it does not upload media or run its own transcript/AI pipeline.
- Gemini receives compressed audio and selected sparse frames only after the user confirms. Full video and full transcript are not sent.
- If the optional provider is missing or fails, ClipForge falls back to its built-in local frame sampler.
- No automatic publishing. Use only content you own or have permission to repurpose.

## Validation

GitHub Actions runs Python bytecode compilation against the application package on pushes and pull requests. Maintainer-only runtime and rendering checks are performed on Windows before publishing a desktop build.
