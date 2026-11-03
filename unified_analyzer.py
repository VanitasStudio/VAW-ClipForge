"""Unified source analysis for VAW ClipForge v1.2.

Adapts the proven v1.1 analyzers into one stable AnalysisBundle. Original
media and full transcripts stay local; Gemini only receives the compressed
audio and sparse frames used by the existing analysis workflow.
"""
from __future__ import annotations

import hashlib
import math
from datetime import datetime
from pathlib import Path
from typing import Callable

from clip_engine import EXTS, FFMPEG, probe_duration
from clipforge_contracts import (
    AnalysisBundle, EditorialEvent, MediaSource, SceneSpan, SegmentRole,
    TranscriptSpan,
)
from silent_process import run as silent_run

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
    log: Callable[[str], None] = print,
) -> AnalysisBundle:
    """Run local analysis and Gemini, returning a single AnalysisBundle."""
    path = Path(source).resolve()
    cache = Path(cache_dir).resolve()
    cache.mkdir(parents=True, exist_ok=True)
    media = probe_source(path)
    warnings: list[str] = []
    transcript_rows: list[dict] = []
    scene_cuts: list[float] = []
    editorial_rows: list[dict] = []

    if context_aware:
        try:
            from smart_duration import analyze_boundaries
            transcript_rows = analyze_boundaries(
                path, cache, model_size=duration_model, log=log
            )
        except Exception as exc:
            warnings.append("Local transcript boundaries were unavailable.")
            log(f"Transcript analysis skipped: {type(exc).__name__}: {str(exc)[:180]}")

    if include_scenes:
        try:
            from smart_reframe import shot_boundaries
            scene_cuts = shot_boundaries(path, log=log)
        except Exception as exc:
            warnings.append("Visual scene detection was unavailable.")
            log(f"Scene detection skipped: {type(exc).__name__}: {str(exc)[:160]}")

    try:
        from gemini_highlights import process_ai
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
    log(
        f"Analysis ready: {len(bundle.transcript)} transcript spans, "
        f"{len(bundle.scenes)} scenes, {len(bundle.events)} editorial moments."
    )
    return bundle
