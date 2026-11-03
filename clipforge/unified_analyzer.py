"""Unified source analysis for VAW ClipForge v1.2.

Adapts the proven v1.1 analyzers into one stable AnalysisBundle. Original
media and full transcripts stay local; Gemini only receives the compressed
audio and sparse frames used by the existing analysis workflow.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Callable

from clipforge.clip_engine import EXTS, FFMPEG, probe_duration
from clipforge.clipforge_contracts import (
    AnalysisBundle, EditorialEvent, MediaSource, SceneSpan, SegmentRole,
    TranscriptSpan,
)
from clipforge.silent_process import run as silent_run

ANALYZER_VERSION = "1.2.0"


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def probe_source(source: str | Path) -> MediaSource:
    """Read basic media metadata locally without uploading the source."""
    path = Path(source).resolve()
    if not path.is_file() or path.suffix.lower() not in EXTS:
        raise ValueError("Choose an existing supported video file.")

    duration = float(probe_duration(path))
    if not math.isfinite(duration) or duration <= 0:
        raise RuntimeError("Video duration is invalid.")
    try:
        import cv2
        capture = cv2.VideoCapture(str(path))
        if not capture.isOpened():
            raise RuntimeError("Video decoder could not open this file.")
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 30.0)
        capture.release()
    except ImportError as exc:
        raise RuntimeError("OpenCV is required to read video dimensions.") from exc

    if width <= 0 or height <= 0 or not math.isfinite(fps) or fps <= 0:
        raise RuntimeError("Video metadata is incomplete or unreadable.")

    # ffmpeg returns a non-zero code for an input-only probe; stream metadata
    # is still present in stderr, so inspect it rather than the exit code.
    probe = silent_run(
        [FFMPEG, "-hide_banner", "-i", str(path)],
        capture_output=True, text=True, timeout=30,
    )
    has_audio = "Audio:" in (probe.stderr or "")
    stat = path.stat()
    fingerprint = f"{path}|{stat.st_size}|{stat.st_mtime_ns}"
    return MediaSource(
        source_id=_stable_id("src", fingerprint),
        path=str(path),
        duration_seconds=duration,
        width=width,
        height=height,
        fps=fps,
        has_audio=has_audio,
    )


def _transcript_spans(rows: list[dict]) -> tuple[TranscriptSpan, ...]:
    spans = []
    for row in rows:
        try:
            start, end = float(row["start"]), float(row["end"])
            text = str(row.get("text", "")).strip()
            if text and math.isfinite(start) and math.isfinite(end) and end > start:
                spans.append((start, end, text))
        except (KeyError, TypeError, ValueError):
            continue
    return tuple(
        TranscriptSpan(
            span_id=f"utt_{index:05d}",
            start_seconds=start,
            end_seconds=end,
            text=text,
        )
        for index, (start, end, text) in enumerate(spans, 1)
    )


def _scene_spans(cuts: list[float], duration: float) -> tuple[SceneSpan, ...]:
    valid_cuts = set()
    for value in cuts:
        try:
            cut = float(value)
            if math.isfinite(cut) and 0.0 < cut < duration:
                valid_cuts.add(cut)
        except (TypeError, ValueError):
            continue
    boundaries = [0.0, *sorted(valid_cuts), float(duration)]
    return tuple(
        SceneSpan(
            scene_id=f"scene_{index:04d}",
            start_seconds=round(start, 3),
            end_seconds=round(end, 3),
        )
        for index, (start, end) in enumerate(zip(boundaries, boundaries[1:]), 1)
        if end > start
    )


def _editorial_events(rows: list[dict]) -> tuple[EditorialEvent, ...]:
    events = []
    for row in rows:
        try:
            start = float(row["start"])
            end = float(row.get("end", start + float(row.get("duration", 0))))
            if not math.isfinite(start) or not math.isfinite(end) or end <= start:
                continue
            title = str(row.get("title") or f"Story moment {len(events) + 1}")[:120]
            summary = str(row.get("reason") or row.get("payoff") or "")[:420]
            score = float(row.get("editorial_score", row.get("score", 0)))
            if not math.isfinite(score):
                score = 0.0
            tags = tuple(
                str(row.get(key, "")).strip()
                for key in ("visual_type", "retention_risk")
                if str(row.get(key, "")).strip()
            )
            events.append(EditorialEvent(
                event_id=f"event_{len(events) + 1:04d}",
                start_seconds=start,
                end_seconds=end,
                topic=title,
                summary=summary,
                role=SegmentRole.SUPPORT,
                confidence=max(0.0, min(1.0, score / 100.0)),
                tags=tags,
                visual_summary=str(row.get("visual_notes", ""))[:600],
            ))
        except (TypeError, ValueError, KeyError):
            continue
    return tuple(events)


def build_analysis_bundle(
    source: MediaSource,
    *,
    transcript_rows: list[dict] | None = None,
    scene_cuts: list[float] | None = None,
    editorial_rows: list[dict] | None = None,
    warnings: list[str] | None = None,
) -> AnalysisBundle:
    """Build a stable bundle from the individual analyzer outputs."""
    stat = Path(source.path).stat()
    fingerprint = f"{source.source_id}|{stat.st_size}|{stat.st_mtime_ns}|{ANALYZER_VERSION}"
    return AnalysisBundle(
        bundle_id=_stable_id("analysis", fingerprint),
        source=source,
        transcript=_transcript_spans(transcript_rows or []),
        scenes=_scene_spans(scene_cuts or [], source.duration_seconds),
        events=_editorial_events(editorial_rows or []),
        analysis_version=ANALYZER_VERSION,
        created_at=datetime.now().astimezone().isoformat(),
        warnings=tuple(warnings or []),
    )


def analyze_source(
    source: str | Path,
    cache_dir: str | Path,
    *,
    clips: int = 6,
    target_seconds: int = 45,
    model: str = "gemini-3.6-flash",
    visual: bool = True,
    context_aware: bool = True,
    duration_model: str = "base",
    include_scenes: bool = True,
    provider=None,
    story_provider=None,
    vision_provider=None,
    vision_enabled: bool | None = None,
    log: Callable[[str], None] = print,
) -> AnalysisBundle:
    """Run local analysis and Gemini, returning a single AnalysisBundle."""
    path = Path(source).resolve()
    cache = Path(cache_dir).resolve()
    cache.mkdir(parents=True, exist_ok=True)
    from time import perf_counter
    probe_started = perf_counter()
    log("Reading local source metadata and validating media streams...")
    media = probe_source(path)
    log(f"Source ready: {media.width}x{media.height}, {media.duration_seconds/60:.1f} min in {perf_counter()-probe_started:.1f}s.")
    warnings: list[str] = []
    vision_result = None
    if vision_enabled is None:
        try:
            from clipforge.video_vision_adapter import is_enabled
            vision_enabled = is_enabled() or vision_provider is not None
        except Exception:
            vision_enabled = False
    if vision_enabled:
        try:
            if vision_provider is None:
                from clipforge.video_vision_adapter import VideoVisionMCPProvider
                vision_provider = VideoVisionMCPProvider()
            from clipforge.vision_cache import CachedVisionProvider, default_vision_cache_dir
            from clipforge.vision_quality import filter_vision_frames
            vision_provider = CachedVisionProvider(vision_provider, default_vision_cache_dir())
            vision_result = vision_provider.analyze(
                path, duration_seconds=media.duration_seconds, max_frames=8
            )
            quality = filter_vision_frames(
                vision_result.frames,
                duration_seconds=media.duration_seconds,
                max_frames=8,
            )
            vision_result = replace(
                vision_result,
                frames=quality.frames,
                warnings=tuple(dict.fromkeys((*vision_result.warnings, *quality.warnings))),
            )
            warnings.extend(vision_result.warnings)
            log(
                f"Visual intelligence ready: {len(vision_result.frames)} key frames "
                f"from {vision_result.provider}."
            )
        except Exception as exc:
            warnings.append("Video Vision MCP was unavailable; built-in visual analysis will be used.")
            log(f"Video Vision MCP skipped: {type(exc).__name__}: {str(exc)[:180]}")
    transcript_rows: list[dict] = []
    scene_cuts: list[float] = []
    editorial_rows: list[dict] = []

    if context_aware:
        try:
            log("Stage 1/3: analyzing speech boundaries locally...")
            from clipforge.smart_duration import analyze_boundaries
            transcript_rows = analyze_boundaries(
                path, cache, model_size=duration_model, log=log
            )
        except Exception as exc:
            warnings.append("Local transcript boundaries were unavailable.")
            log(f"Transcript analysis skipped: {type(exc).__name__}: {str(exc)[:180]}")

    if include_scenes:
        try:
            log("Stage 2/3: scanning visual scene transitions...")
            from clipforge.smart_reframe import shot_boundaries
            scene_cuts = shot_boundaries(path, log=log)
        except Exception as exc:
            warnings.append("Visual scene detection was unavailable.")
            log(f"Scene detection skipped: {type(exc).__name__}: {str(exc)[:160]}")

    try:
        log("Stage 3/3: ranking editorial moments and building story candidates...")
        from clipforge.gemini_highlights import process_ai
        result = process_ai(
            path,
            cache / "gemini-analysis",
            clips=clips,
            seconds=target_seconds,
            model=model,
            log=log,
            provider=provider,
            visual=visual,
            render=False,
            context_aware=False,
            boundary_spans=transcript_rows,
            vision_frames=vision_result.frames if vision_result else None,
        )
        editorial_rows = result.get("ranked_candidates", [])
        if not editorial_rows:
            editorial_rows = result.get("clips", [])
    except Exception as exc:
        warnings.append("Gemini editorial analysis did not complete.")
        log(f"Editorial analysis unavailable: {type(exc).__name__}: {str(exc)[:200]}")
        if not transcript_rows and not scene_cuts:
            raise RuntimeError(
                "No analysis stage completed. Check the source, local models and Gemini settings."
            ) from exc

    bundle = build_analysis_bundle(
        media,
        transcript_rows=transcript_rows,
        scene_cuts=scene_cuts,
        editorial_rows=editorial_rows,
        warnings=warnings,
    )
    if vision_result is not None:
        try:
            from clipforge.multimodal_fusion import fuse_visual_evidence
            bundle = fuse_visual_evidence(bundle, vision_result)
        except Exception as exc:
            warnings.append("Visual evidence could not be attached to the analysis timeline.")
            bundle = replace(bundle, warnings=tuple(dict.fromkeys((*bundle.warnings, *warnings))))
            log(f"Visual evidence fusion skipped: {type(exc).__name__}: {str(exc)[:160]}")
    if bundle.events:
        try:
            from clipforge.gemini_highlights import request_story_compositions
            story = request_story_compositions(bundle.events, provider=story_provider)
            bundle = replace(
                bundle,
                composition_orders=story["composition_orders"],
                event_roles=story["event_roles"],
                event_dependencies=story["event_dependencies"],
            )
        except Exception as exc:
            warnings.append("AI story structure was unavailable; deterministic composition ordering will be used.")
            bundle = replace(bundle, warnings=tuple(warnings))
            log(f"Story structure unavailable: {type(exc).__name__}: {str(exc)[:180]}")
    log(
        f"Analysis ready: {len(bundle.transcript)} transcript spans, "
        f"{len(bundle.scenes)} scenes, {len(bundle.events)} editorial moments."
    )
    return bundle
