from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any
import json

CONTRACT_VERSION = "1.0"
MIN_CLIP_SECONDS = 12.0
MAX_CLIP_SECONDS = 180.0
MIN_COMPOSITION_SEGMENTS = 2
MAX_COMPOSITION_SEGMENTS = 8


class CompositionStrategy(str, Enum):
    SMART_COMPILATION = "smart_compilation"
    NARRATIVE_RECONSTRUCTION = "narrative_reconstruction"


class SegmentRole(str, Enum):
    HOOK = "hook"
    CONTEXT = "context"
    DEVELOPMENT = "development"
    EVIDENCE = "evidence"
    PAYOFF = "payoff"
    BRIDGE = "bridge"
    SUPPORT = "support"


class TransitionKind(str, Enum):
    HARD_CUT = "hard_cut"
    CROSS_DISSOLVE = "cross_dissolve"
    J_CUT = "j_cut"
    L_CUT = "l_cut"
    DIP = "dip"
    FADE_IN = "fade_in"
    FADE_OUT = "fade_out"


class AudioContinuity(str, Enum):
    SMART = "smart"
    SOURCE_CONTINUOUS = "source_continuous"
    SEGMENT_LOCAL = "segment_local"


class JobStatus(str, Enum):
    CREATED = "created"
    INGESTING = "ingesting"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    VALIDATING = "validating"
    READY_TO_RENDER = "ready_to_render"
    RENDERING = "rendering"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EngineStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class MediaSource:
    source_id: str
    path: str
    duration_seconds: float
    width: int
    height: int
    fps: float
    has_audio: bool = True

    def __post_init__(self) -> None:
        if not self.source_id or not self.path:
            raise ValueError("source_id and path are required")
        if self.duration_seconds <= 0 or self.width <= 0 or self.height <= 0 or self.fps <= 0:
            raise ValueError("Media metadata must contain positive duration, dimensions and fps")


@dataclass(frozen=True)
class TranscriptSpan:
    span_id: str
    start_seconds: float
    end_seconds: float
    text: str
    speaker: str | None = None

    def __post_init__(self) -> None:
        if self.start_seconds < 0 or self.end_seconds <= self.start_seconds:
            raise ValueError("Transcript span has an invalid time range")


@dataclass(frozen=True)
class SceneSpan:
    scene_id: str
    start_seconds: float
    end_seconds: float
    visual_summary: str = ""
    visual_tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.start_seconds < 0 or self.end_seconds <= self.start_seconds:
            raise ValueError("Scene span has an invalid time range")


@dataclass(frozen=True)
class EditorialEvent:
    event_id: str
    start_seconds: float
    end_seconds: float
    topic: str
    summary: str
    role: SegmentRole = SegmentRole.SUPPORT
    confidence: float = 0.0
    tags: tuple[str, ...] = ()
    requires_event_ids: tuple[str, ...] = ()
    supports_event_ids: tuple[str, ...] = ()
    contradicts_event_ids: tuple[str, ...] = ()
    visual_summary: str = ""
    visual_evidence_seconds: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        if self.start_seconds < 0 or self.end_seconds <= self.start_seconds:
            raise ValueError("Editorial event has an invalid time range")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class AnalysisBundle:
    bundle_id: str
    source: MediaSource
    transcript: tuple[TranscriptSpan, ...] = ()
    scenes: tuple[SceneSpan, ...] = ()
    events: tuple[EditorialEvent, ...] = ()
    analysis_version: str = "1.0"
    created_at: str = ""
    warnings: tuple[str, ...] = ()
    composition_orders: dict[str, tuple[str, ...]] = field(default_factory=dict)
    event_roles: dict[str, str] = field(default_factory=dict)
    event_dependencies: dict[str, tuple[str, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class CompositionSegment:
    segment_id: str
    source_id: str
    source_in: float
    source_out: float
    timeline_in: float
    role: SegmentRole = SegmentRole.SUPPORT
    reason: str = ""
    event_ids: tuple[str, ...] = ()

    @property
    def duration_seconds(self) -> float:
        return self.source_out - self.source_in

    @property
    def timeline_out(self) -> float:
        return self.timeline_in + self.duration_seconds

    def __post_init__(self) -> None:
        if not self.segment_id or not self.source_id:
            raise ValueError("segment_id and source_id are required")
        if self.source_in < 0 or self.source_out <= self.source_in or self.timeline_in < 0:
            raise ValueError("Composition segment has an invalid time range")


@dataclass(frozen=True)
class TransitionSpec:
    from_segment_id: str
    to_segment_id: str
    kind: TransitionKind = TransitionKind.HARD_CUT
    duration_seconds: float = 0.0
    reason: str = ""

    def __post_init__(self) -> None:
        if self.duration_seconds < 0:
            raise ValueError("Transition duration cannot be negative")
        if self.kind == TransitionKind.HARD_CUT and self.duration_seconds != 0:
            raise ValueError("Hard cuts must have a zero duration")


@dataclass(frozen=True)
class AudioPlan:
    continuity: AudioContinuity = AudioContinuity.SMART
    source_gain_db: float = 0.0
    preserve_dialogue: bool = True
    allow_crossfade: bool = True


@dataclass(frozen=True)
class CaptionPlan:
    enabled: bool = True
    preset_id: str = "karaoke"
    uppercase: bool = False
    burn_in: bool = True
    export_srt: bool = True


@dataclass(frozen=True)
class RenderSettings:
    width: int = 1080
    height: int = 1920
    fps: float = 30.0
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    crf: int = 18
    pixel_format: str = "yuv420p"

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0 or self.fps <= 0:
            raise ValueError("Render dimensions and fps must be positive")
        if not 0 <= self.crf <= 51:
            raise ValueError("CRF must be between 0 and 51")


@dataclass(frozen=True)
class EditDecisionList:
    edl_id: str
    source_id: str
    composition_id: str
    strategy: CompositionStrategy
    title: str
    segments: tuple[CompositionSegment, ...]
    transitions: tuple[TransitionSpec, ...] = ()
    audio: AudioPlan = field(default_factory=AudioPlan)
    captions: CaptionPlan = field(default_factory=CaptionPlan)
    render: RenderSettings = field(default_factory=RenderSettings)
    schema_version: str = CONTRACT_VERSION
    created_at: str = ""
    target_duration_seconds: float = 0.0

    @property
    def duration_seconds(self) -> float:
        return max((segment.timeline_out for segment in self.segments), default=0.0)


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    severity: str = "error"
    segment_id: str | None = None


@dataclass(frozen=True)
class ValidationReport:
    valid: bool
    issues: tuple[ValidationIssue, ...] = ()


@dataclass(frozen=True)
class EngineResult:
    status: EngineStatus
    output_ids: tuple[str, ...] = ()
    message: str = ""
    error_code: str | None = None


@dataclass(frozen=True)
class JobResult:
    job_id: str
    status: JobStatus
    standalone: EngineResult = field(default_factory=lambda: EngineResult(EngineStatus.PENDING))
    smart_compilation: EngineResult = field(default_factory=lambda: EngineResult(EngineStatus.PENDING))
    narrative_reconstruction: EngineResult = field(default_factory=lambda: EngineResult(EngineStatus.PENDING))
    output_paths: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    error_message: str | None = None


def validate_edl(edl: EditDecisionList, source: MediaSource) -> ValidationReport:
    issues: list[ValidationIssue] = []
    if edl.source_id != source.source_id:
        issues.append(ValidationIssue("source_mismatch", "EDL source does not match the loaded media"))
    if not MIN_CLIP_SECONDS <= edl.duration_seconds <= MAX_CLIP_SECONDS:
        issues.append(ValidationIssue("duration_out_of_range", f"Composition duration must be between {MIN_CLIP_SECONDS:g} and {MAX_CLIP_SECONDS:g} seconds"))
    if not MIN_COMPOSITION_SEGMENTS <= len(edl.segments) <= MAX_COMPOSITION_SEGMENTS:
        issues.append(ValidationIssue("segment_count_out_of_range", f"Composition must contain {MIN_COMPOSITION_SEGMENTS} to {MAX_COMPOSITION_SEGMENTS} segments"))

    seen_ids: set[str] = set()
    previous_timeline_out = 0.0
    for segment in edl.segments:
        if segment.segment_id in seen_ids:
            issues.append(ValidationIssue("duplicate_segment_id", "Segment IDs must be unique", segment_id=segment.segment_id))
        seen_ids.add(segment.segment_id)
        if segment.source_id != source.source_id:
            issues.append(ValidationIssue("segment_source_mismatch", "Segment points to a different source", segment_id=segment.segment_id))
        if segment.source_out > source.duration_seconds:
            issues.append(ValidationIssue("source_range_exceeded", "Segment ends beyond the source duration", segment_id=segment.segment_id))
        if segment.timeline_in < previous_timeline_out - 0.001:
            issues.append(ValidationIssue("timeline_overlap", "Segments overlap on the timeline; overlap must be represented by a transition", segment_id=segment.segment_id))
        previous_timeline_out = max(previous_timeline_out, segment.timeline_out)

    valid_transition_pairs = {(a.segment_id, b.segment_id) for a, b in zip(edl.segments, edl.segments[1:])}
    for transition in edl.transitions:
        pair = (transition.from_segment_id, transition.to_segment_id)
        if pair not in valid_transition_pairs:
            issues.append(ValidationIssue("invalid_transition_pair", "Transition must connect adjacent segments"))
        if transition.from_segment_id not in seen_ids or transition.to_segment_id not in seen_ids:
            issues.append(ValidationIssue("unknown_transition_segment", "Transition references a segment that is not in this EDL"))
        if transition.kind not in {TransitionKind.HARD_CUT, TransitionKind.CROSS_DISSOLVE}:
            issues.append(ValidationIssue(
                "unsupported_transition",
                "This ClipForge version supports hard cuts and cross-dissolves only",
            ))
        if transition.kind == TransitionKind.CROSS_DISSOLVE:
            left = next((item for item in edl.segments if item.segment_id == transition.from_segment_id), None)
            right = next((item for item in edl.segments if item.segment_id == transition.to_segment_id), None)
            if transition.duration_seconds <= 0:
                issues.append(ValidationIssue("invalid_transition_duration", "Cross-dissolves must have a positive duration"))
            elif left and right and transition.duration_seconds > min(left.duration_seconds, right.duration_seconds) * 0.25:
                issues.append(ValidationIssue("transition_too_long", "Cross-dissolve duration cannot exceed 25% of either adjacent segment"))

    return ValidationReport(valid=not any(issue.severity == "error" for issue in issues), issues=tuple(issues))


def to_dict(value: Any) -> Any:
    """Convert contract objects into JSON-safe dictionaries."""
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: to_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): to_dict(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [to_dict(item) for item in value]
    return value


def dumps_contract(value: Any, *, indent: int = 2) -> str:
    return json.dumps(to_dict(value), ensure_ascii=False, indent=indent)
