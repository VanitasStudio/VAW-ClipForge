# VAW ClipForge v1.2.1 — Vision-Aware Story Editing

VAW ClipForge v1.2 builds on the v1.1 local-first desktop editor. It keeps Standalone Highlights and adds two complete Story Composer outputs: Smart Compilation and Narrative Reconstruction. Both story strategies can be enabled together.

## Vanitas Studio identity

The desktop interface follows the Vanitas Studio product language: dark, premium, minimal and editorial.
Archivo is used for functional UI typography; Quantico is reserved for the product wordmark.
The palette is built around Vanitas Blue, platinum and restrained orange accents.
See docs/VANITAS_BRAND_UI.md for the full tokens and UI rules.

## Windows desktop application

End users should launch dist/VAW-ClipForge.exe. The application is packaged as a single-file,
windowed Windows executable with the Vanitas app icon and bundled fonts. No Python installation
or CMD launcher is required to start the packaged app.

Build or rebuild on Windows with:

~~~powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1 -Clean
~~~

The resulting executable is written to dist/VAW-ClipForge.exe. First-time speech-model use may
download the selected Whisper model into the user's Hugging Face cache. The Gemini key remains
protected with Windows DPAPI under the current Windows account.

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

Requires Git and Node.js 20.9 or newer. From the ClipForge project folder, run once:

~~~powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_video_vision_mcp.ps1
~~~

The installer checks out a pinned MIT-licensed upstream revision, applies semver-safe dependency updates, audits the production dependency tree and builds the MCP server locally. The README's npm package name is not currently available from the npm registry, so ClipForge installs from the pinned GitHub source instead.

The desktop checkbox is off by default. The programmatic analyzer can opt in with:

~~~powershell
$env:CLIPFORGE_VIDEO_VISION_ENABLED = "1"
~~~

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

Runtime modules and Windows launchers remain at the project root for compatibility. QA tests are grouped in tests/, product and release documentation in docs/, setup and maintainer scripts in scripts/, and historical one-off patches in tools/legacy_patches/.

Run the supported regression suite:

~~~powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_qa.ps1
~~~

See docs/REPOSITORY_STRUCTURE.md for the full layout and RELEASE_NOTES.md for the latest changes. Historical release notes are archived under docs/archive/releases/.

## Privacy and safety

- Original media, Whisper transcription and boundary alignment stay local.
- Video Vision MCP receives only a local file path and writes bounded frame images to a temporary local directory. It does not receive an online URL, cookies or API key from ClipForge.
- The MCP integration uses frame extraction only; it does not upload media or run its own transcript/AI pipeline.
- Gemini receives compressed audio and selected sparse frames only after the user confirms. Full video and full transcript are not sent.
- If the optional provider is missing or fails, ClipForge falls back to its built-in local frame sampler.
- No automatic publishing. Use only content you own or have permission to repurpose.

## QA

The v1.2 QA suite covers EDL contracts, unified analysis, Story Composer ordering and dependency validation, MCP transport and frame extraction, visual cache/quality/fusion, composition rendering and Review Studio round-tripping. v1.1 UI and GUI smoke tests remain part of the regression gate.
