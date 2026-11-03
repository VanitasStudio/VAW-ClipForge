"""Quality gates for visual frames before multimodal analysis."""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

from vision_provider import VisionFrame


@dataclass(frozen=True)
class VisionQualityReport:
    frames: tuple[VisionFrame, ...]
    duplicate_count: int = 0
    rejected_count: int = 0
    warnings: tuple[str, ...] = ()


def filter_vision_frames(
    frames: tuple[VisionFrame, ...] | list[VisionFrame],
    *,
    duration_seconds: float,
    max_frames: int = 12,
) -> VisionQualityReport:
    if not math.isfinite(float(duration_seconds)) or duration_seconds <= 0:
        raise ValueError("Video duration must be positive and finite.")
    if not 1 <= int(max_frames) <= 24:
        raise ValueError("max_frames must be between 1 and 24.")

    accepted = []
    hashes = set()
    timestamps = set()
    duplicates = rejected = 0
    for frame in frames:
        try:
            timestamp = float(frame.timestamp_seconds)
            data = bytes(frame.image_bytes)
        except (AttributeError, TypeError, ValueError):
            rejected += 1
            continue
        if not math.isfinite(timestamp) or not data or timestamp < 0 or timestamp > duration_seconds:
            rejected += 1
            continue
        digest = hashlib.sha256(data).hexdigest()
        if digest in hashes or round(timestamp, 3) in timestamps:
            duplicates += 1
            continue
        hashes.add(digest)
        timestamps.add(round(timestamp, 3))
        accepted.append(frame)

    accepted.sort(key=lambda item: item.timestamp_seconds)
    if len(accepted) > max_frames:
        if max_frames == 1:
            accepted = [accepted[len(accepted) // 2]]
        else:
            indices = [
                round(i * (len(accepted) - 1) / (max_frames - 1))
                for i in range(max_frames)
            ]
            accepted = [accepted[index] for index in indices]

    warnings = []
    if rejected:
        warnings.append(f"{rejected} invalid visual frame(s) were discarded.")
    if duplicates:
        warnings.append(f"{duplicates} duplicate visual frame(s) were discarded.")
    if not accepted:
        warnings.append("No usable visual frames were returned.")
    elif len(accepted) == 1:
        warnings.append("Only one visual frame was available; visual coverage is limited.")

    return VisionQualityReport(
        frames=tuple(accepted),
        duplicate_count=duplicates,
        rejected_count=rejected,
        warnings=tuple(warnings),
    )
