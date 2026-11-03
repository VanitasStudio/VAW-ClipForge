"""Fuse timestamped visual evidence with local transcript and editorial events."""
from __future__ import annotations

from dataclasses import replace

from clipforge_contracts import AnalysisBundle, SceneSpan
from vision_provider import VisionResult
from vision_quality import filter_vision_frames


def fuse_visual_evidence(
    bundle: AnalysisBundle,
    result: VisionResult,
    *,
    max_frames: int = 12,
) -> AnalysisBundle:
    quality = filter_vision_frames(
        result.frames,
        duration_seconds=bundle.source.duration_seconds,
        max_frames=max_frames,
    )
    frames = quality.frames
    enriched_events = []
    for event in bundle.events:
        evidence = tuple(
            round(frame.timestamp_seconds, 3)
            for frame in frames
            if event.start_seconds <= frame.timestamp_seconds <= event.end_seconds
        )
        enriched_events.append(replace(
            event,
            visual_evidence_seconds=evidence,
        ))

    enriched_scenes = []
    for scene in bundle.scenes:
        related = [
            event for event in enriched_events
            if event.start_seconds < scene.end_seconds
            and event.end_seconds > scene.start_seconds
        ]
        summaries = []
        tags = list(scene.visual_tags)
        for event in related:
            summary = event.visual_summary.strip()
            if summary and summary not in summaries:
                summaries.append(summary)
            for tag in event.tags:
                if tag not in tags:
                    tags.append(tag)
        visual_summary = scene.visual_summary
        if summaries:
            visual_summary = " ".join(summaries)[:800]
        enriched_scenes.append(replace(
            scene,
            visual_summary=visual_summary,
            visual_tags=tuple(tags[:12]),
        ))

    warnings = list(bundle.warnings)
    warnings.extend(quality.warnings)
    return replace(
        bundle,
        events=tuple(enriched_events),
        scenes=tuple(enriched_scenes),
        warnings=tuple(dict.fromkeys(warnings)),
    )
