"""Story composition planning for VAW ClipForge v1.2."""
from __future__ import annotations

from datetime import datetime
from math import isfinite

from clipforge_contracts import (
    AnalysisBundle, AudioPlan, CaptionPlan, CompositionSegment,
    CompositionStrategy, EditDecisionList, RenderSettings, SegmentRole,
    TransitionKind, TransitionSpec, validate_edl,
)

MIN_SEGMENTS = 2
MAX_SEGMENTS = 8
MAX_DURATION = 180.0


def _role(value: str | SegmentRole | None, fallback: SegmentRole) -> SegmentRole:
    if isinstance(value, SegmentRole):
        return value
    try:
        return SegmentRole(str(value))
    except (ValueError, TypeError):
        return fallback


def _ordered_events(bundle: AnalysisBundle, strategy: CompositionStrategy):
    by_id = {event.event_id: event for event in bundle.events}
    if len(by_id) != len(bundle.events):
        raise ValueError("Analysis contains duplicate editorial event IDs.")
    requested = tuple(bundle.composition_orders.get(strategy.value, ()))
    unknown = set(requested) - set(by_id)
    if unknown:
        raise ValueError(
            f"Composition order references unknown event IDs: {', '.join(sorted(unknown))}."
        )
    if len(set(requested)) != len(requested):
        raise ValueError("Composition order contains duplicate event IDs.")
    ordered = [by_id[event_id] for event_id in requested]
    if not ordered:
        if strategy == CompositionStrategy.SMART_COMPILATION:
            ordered = sorted(bundle.events, key=lambda event: (-event.confidence, event.start_seconds))
        else:
            ordered = sorted(bundle.events, key=lambda event: event.start_seconds)
    return ordered


def _dependency_order(events, dependencies: dict[str, tuple[str, ...]]):
    """Topologically order events; missing prerequisites and cycles are errors."""
    by_id = {event.event_id: event for event in events}
    for event_id in by_id:
        missing = set(dependencies.get(event_id, ())) - set(by_id)
        if missing:
            raise ValueError(
                f"Event {event_id} requires unavailable prerequisite(s): {', '.join(sorted(missing))}."
            )
    remaining = list(events)
    ordered = []
    placed: set[str] = set()
    while remaining:
        ready = next((
            event for event in remaining
            if set(dependencies.get(event.event_id, ())).issubset(placed)
        ), None)
        if ready is None:
            raise ValueError("Narrative dependencies contain a cycle.")
        ordered.append(ready)
        placed.add(ready.event_id)
        remaining.remove(ready)
    return ordered


def build_composition(
    bundle: AnalysisBundle,
    strategy: CompositionStrategy,
    *,
    target_duration_seconds: float = 60.0,
    roles: dict[str, str] | None = None,
    dependencies: dict[str, tuple[str, ...]] | None = None,
) -> EditDecisionList:
    """Build one EDL from complete source moments; never trim to fit."""
    target = float(target_duration_seconds)
    if not isfinite(target) or not 12.0 <= target <= MAX_DURATION:
        raise ValueError("Target duration must be between 12 and 180 seconds.")
    if not isinstance(strategy, CompositionStrategy):
        strategy = CompositionStrategy(strategy)

    roles = roles if roles is not None else bundle.event_roles
    dependencies = dependencies if dependencies is not None else bundle.event_dependencies
    ordered = _ordered_events(bundle, strategy)
    if strategy == CompositionStrategy.NARRATIVE_RECONSTRUCTION:
        ordered = _dependency_order(ordered, dependencies)

    selected = []
    total = 0.0
    for event in ordered:
        values = (event.start_seconds, event.end_seconds, event.confidence)
        if not all(isfinite(float(value)) for value in values):
            continue
        duration = event.end_seconds - event.start_seconds
        if duration < 1.0 or duration > MAX_DURATION:
            continue
        if event.start_seconds < 0 or event.end_seconds > bundle.source.duration_seconds:
            continue
        if any(_source_overlap(event, existing) > 0.35 for existing in selected):
            continue
        if total + duration > MAX_DURATION:
            continue
        selected.append(event)
        total += duration
        if len(selected) >= MAX_SEGMENTS or (total >= target and len(selected) >= MIN_SEGMENTS):
            break

    if len(selected) < MIN_SEGMENTS:
        raise ValueError(
            f"{strategy.value} needs at least {MIN_SEGMENTS} complete, non-overlapping moments "
            "that fit within 180 seconds."
        )
    if not 12.0 <= total <= MAX_DURATION:
        raise ValueError("The selected moments do not fit the 12–180 second composition limit.")

    segments = []
    timeline = 0.0
    for index, event in enumerate(selected, 1):
        segment_id = f"{strategy.value}_{index:02d}"
        segment = CompositionSegment(
            segment_id=segment_id,
            source_id=bundle.source.source_id,
            source_in=event.start_seconds,
            source_out=event.end_seconds,
            timeline_in=timeline,
            role=_role(roles.get(event.event_id), event.role),
            reason=(event.summary + ((" | Visual: " + event.visual_summary) if event.visual_summary else ""))[:600],
            event_ids=(event.event_id,),
        )
        segments.append(segment)
        timeline = segment.timeline_out

    transitions = tuple(
        TransitionSpec(
            from_segment_id=left.segment_id,
            to_segment_id=right.segment_id,
            kind=TransitionKind.HARD_CUT,
            reason="Clean dialogue continuity; transitions remain editable in Review Studio.",
        )
        for left, right in zip(segments, segments[1:])
    )
    title = (
        "Smart Compilation"
        if strategy == CompositionStrategy.SMART_COMPILATION
        else "Narrative Reconstruction"
    )
    edl = EditDecisionList(
        edl_id=f"edl_{strategy.value}",
        source_id=bundle.source.source_id,
        composition_id=f"composition_{strategy.value}",
        strategy=strategy,
        title=title,
        segments=tuple(segments),
        transitions=transitions,
        audio=AudioPlan(),
        captions=CaptionPlan(),
        render=RenderSettings(),
        created_at=datetime.now().astimezone().isoformat(),
        target_duration_seconds=target,
    )
    report = validate_edl(edl, bundle.source)
    if not report.valid:
        details = "; ".join(issue.message for issue in report.issues)
        raise ValueError("Composition failed validation: " + details)
    return edl


def _source_overlap(a, b) -> float:
    overlap = max(0.0, min(a.end_seconds, b.end_seconds) - max(a.start_seconds, b.start_seconds))
    return overlap / max(1.0, min(a.end_seconds - a.start_seconds, b.end_seconds - b.start_seconds))


def build_compositions(
    bundle: AnalysisBundle,
    *,
    target_duration_seconds: float = 60.0,
) -> dict[str, EditDecisionList]:
    """Build both approved Story Composer outputs independently."""
    results = {}
    failures = []
    for strategy in (CompositionStrategy.SMART_COMPILATION, CompositionStrategy.NARRATIVE_RECONSTRUCTION):
        try:
            results[strategy.value] = build_composition(
                bundle, strategy, target_duration_seconds=target_duration_seconds
            )
        except ValueError as exc:
            failures.append(f"{strategy.value}: {exc}")
    if not results:
        raise ValueError("No Story Composer output could be planned. " + " | ".join(failures))
    return results
