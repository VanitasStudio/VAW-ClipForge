"""Provider contracts for optional visual analysis backends."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class VisionFrame:
    timestamp_seconds: float
    image_bytes: bytes
    mime_type: str = "image/jpeg"
    source: str = "unknown"


@dataclass(frozen=True)
class VisionResult:
    provider: str
    frames: tuple[VisionFrame, ...] = ()
    transcript_text: str = ""
    metadata: dict = field(default_factory=dict)
    warnings: tuple[str, ...] = ()


class VisionProvider(Protocol):
    def analyze(self, source: str | Path, *, duration_seconds: float,
                max_frames: int = 12) -> VisionResult: ...
