# VAW ClipForge

**Turn long-form video into focused vertical content.**

VAW ClipForge is a Windows desktop application for finding, shaping, and exporting short-form video from longer recordings. It combines local media analysis, AI-assisted editorial understanding, and a reviewable editing workflow to help creators turn source footage into standalone highlights or a connected story.

Instead of producing a folder of unrelated cuts, ClipForge gives you control over how moments are selected, arranged, captioned, and delivered.

[**Download for Windows**](https://github.com/VanitasStudio/VAW-ClipForge/releases/latest) · [Report a bug](https://github.com/VanitasStudio/VAW-ClipForge/issues) · [Security policy](SECURITY.md)

---

## What you can make

ClipForge supports three ways to shape source footage. You can use either Story Composer mode on its own or enable both alongside Standalone Highlights.

### Standalone Highlights

Find strong, self-contained moments and export them as individual vertical clips. Each highlight is treated as its own piece of content, rather than being forced into a larger sequence.

### Story Composer — Smart Compilation

Build a single vertical video from a selection of strong moments. The composer balances relevance and variety to create a compilation that feels intentional, without requiring every moment to follow a strict narrative order.

### Story Composer — Narrative Reconstruction

Reassemble moments into a coherent sequence. The composer considers context, prerequisites, and payoff so that the finished video is easier to follow as a story—not simply a ranking of the loudest or most visually striking moments.

Story Composer exports include an editable edit decision list (EDL) and supporting analysis data, so the composition can be reviewed and revised.

## From source footage to finished video

A typical ClipForge session follows this workflow:

1. **Add source media.** Open a local video or provide a supported public video URL.
2. **Choose the output.** Select Standalone Highlights, Smart Compilation, Narrative Reconstruction, or a combination.
3. **Set the format.** Configure vertical output, framing, captions, and the preferred Story Composer duration.
4. **Analyze the footage.** ClipForge examines speech, scene boundaries, and visual evidence to identify useful moments.
5. **Review the edit.** Inspect the proposed composition, adjust its sequence and timing, and refine captions and transitions.
6. **Export.** Render vertical MP4 video and the available supporting files.

The Story Composer duration is a target, not a reason to cut off an important moment. Compositions are kept within the supported 12–180 second range.

## Editing and review

The Review Studio is designed for editorial refinement after a composition has been generated. It is not intended to replace a full non-linear video editor.

Depending on the output, you can:

- Review the sequence on a multi-segment timeline.
- Reorder segments and adjust source in/out points.
- Change segment roles and refine the structure of a story.
- Correct transcript captions and configure caption presentation.
- Choose hard cuts or cross-dissolves, with smart audio continuity for supported compositions.
- Save an editable draft and render a new revision without overwriting the previous export.

ClipForge keeps the original source media intact. Review changes are applied to a new output.

## Local processing and AI assistance

ClipForge is built around a local-first workflow. Media handling and core analysis run on your Windows machine, with optional AI assistance for higher-level editorial interpretation.

- **Local speech transcription:** Whisper processes source audio locally.
- **Scene analysis:** Scene boundaries are detected locally to help identify meaningful visual changes.
- **Visual context:** Selected frames can be used to provide additional context during editorial analysis.
- **Optional Gemini assistance:** When enabled, Gemini can help interpret selected audio and visual evidence and support editorial suggestions.
- **Hardware-aware rendering:** ClipForge checks whether NVIDIA hardware encoding is usable and falls back to software encoding when it is not.
- **CPU fallback:** If the required CUDA runtime is unavailable, speech transcription can use CPU inference instead.

AI assistance is optional. The application retains a local processing path when cloud assistance is not enabled or available. Processing speed depends on source media, model selection, and the capabilities of the computer.

## Titles and hashtags

ClipForge can prepare a Markdown suggestion sheet alongside an export. It contains title options and relevant hashtags for the generated clips, giving you a starting point for publishing.

These are editorial suggestions—not automatic publishing. Review titles, hashtags, and any factual claims before using them.

## Privacy

Your source footage and full transcript are not sent to Gemini.

When Gemini assistance is enabled and you confirm the data-sharing prompt, ClipForge sends selected, compressed audio and sparse frame images for analysis. The full source video and full transcript remain on your device.

The optional Video Vision integration is used for bounded local frame extraction. It does not replace ClipForge's transcription pipeline or independently upload your source media.

ClipForge does not publish content to social platforms automatically. Only process media you own or have permission to use.

For vulnerability reporting and security expectations, see [SECURITY.md](SECURITY.md).

## Getting started

1. Open the [latest Windows release](https://github.com/VanitasStudio/VAW-ClipForge/releases/latest).
2. Download the available ClipForge executable from the release assets.
3. Run the application on Windows.
4. Select your source video and choose the output workflow that fits your edit.
5. Review the generated results before publishing.

The first use of a selected Whisper model may require an internet connection to download the model files. Gemini features require the user's own API configuration and explicit opt-in.

## System requirements

- **Operating system:** Windows 10 or Windows 11, 64-bit.
- **Processor:** A modern multi-core CPU.
- **Memory:** 8 GB RAM minimum; 16 GB or more recommended for longer or higher-resolution footage.
- **Graphics:** NVIDIA GPU is optional. Compatible NVIDIA hardware can accelerate supported encoding workloads.
- **Storage:** Free space for source media, model files, temporary processing data, and exported videos.
- **Network:** Required for downloading model files, accessing supported public video URLs, and using optional Gemini services.

Actual performance varies with video resolution, codec, duration, model choice, and available hardware.

## Project structure

- `clipforge/` — application and media-processing modules.
- `assets/` — application identity, fonts, and bundled resources.
- `docs/` — focused technical and product documentation.
- `.github/` — repository templates and automation.

The README describes the product and its user-facing workflows. Release-specific changes and build availability are maintained separately on the [Releases page](https://github.com/VanitasStudio/VAW-ClipForge/releases).

## About

VAW ClipForge is developed by **Vanitas Studio**.

The application uses a dark, restrained workspace with metallic silver typography and electric-blue accents—built to keep attention on the footage and the edit.

---

**Have feedback or found a problem?** Open an issue on the [GitHub repository](https://github.com/VanitasStudio/VAW-ClipForge/issues).
