"""Render Story Composer EDLs using ClipForge's proven v0.4 segment renderer."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from clipforge.clip_engine import FFMPEG
from clipforge.local_performance import video_encoder_args, video_encoder_label
from clipforge.clipforge_contracts import AnalysisBundle, EditDecisionList, dumps_contract, validate_edl
from clipforge.silent_process import run as silent_run
from clipforge.smart_reframe import export_v04
from clipforge.subtitle_presets import caption_ass


def _unique_output(path: Path) -> Path:
    if not path.exists():
        return path
    for revision in range(2, 1000):
        candidate = path.with_name(f"{path.stem}_rev{revision}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError("Too many existing revisions for this composition.")


def _time_srt(seconds: float) -> str:
    ms = max(0, round(float(seconds) * 1000))
    hours, ms = divmod(ms, 3_600_000)
    minutes, ms = divmod(ms, 60_000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"


def _caption_rows(bundle: AnalysisBundle, edl: EditDecisionList) -> list[dict]:
    rows = []
    for segment in edl.segments:
        previous_end = segment.timeline_in
        for span in sorted(bundle.transcript, key=lambda item: item.start_seconds):
            start = max(float(span.start_seconds), float(segment.source_in))
            end = min(float(span.end_seconds), float(segment.source_out))
            if end <= start:
                continue
            timeline_start = segment.timeline_in + (start - segment.source_in)
            timeline_end = segment.timeline_in + (end - segment.source_in)
            timeline_start = max(timeline_start, previous_end + (0.001 if rows else 0.0))
            if timeline_end <= timeline_start:
                continue
            text = str(span.text).strip()
            if not text:
                continue
            rows.append({
                "start": round(timeline_start, 3),
                "end": round(timeline_end, 3),
                "text": text,
            })
            previous_end = timeline_end
    rows.sort(key=lambda item: item["start"])
    normalized = []
    previous_end = 0.0
    for row in rows:
        row["start"] = max(float(row["start"]), previous_end)
        if row["end"] <= row["start"]:
            continue
        normalized.append(row)
        previous_end = float(row["end"])
    return normalized


def _write_subtitles(
    output: Path,
    rows: list[dict],
    style: str,
    *,
    export_srt: bool,
    burn_in: bool,
    uppercase: bool,
) -> tuple[Path | None, Path | None]:
    if not rows:
        return None, None
    prepared = [
        {**row, "text": str(row["text"]).upper() if uppercase else str(row["text"])}
        for row in rows
    ]
    srt_path = None
    if export_srt:
        srt_path = output.with_suffix(".srt")
        srt_text = "\n\n".join(
            f"{index}\n{_time_srt(row['start'])} --> {_time_srt(row['end'])}\n{row['text']}"
            for index, row in enumerate(prepared, 1)
        ) + "\n"
        srt_path.write_text(srt_text, encoding="utf-8")
    ass_path = None
    if burn_in:
        ass_path = output.with_suffix(".ass")
        ass_path.write_text(caption_ass(prepared, style), encoding="utf-8")
    return srt_path, ass_path


def _burn_ass(video: Path, ass_path: Path, output: Path, log) -> None:
    filter_path = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
    filter_path = filter_path.replace("'", "\\'")
    command = [
        FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(video), "-vf", f"ass='{filter_path}'",
        *video_encoder_args(FFMPEG,19), "-c:a", "copy",
        "-movflags", "+faststart", str(output),
    ]
    result = silent_run(command, capture_output=True, text=True, timeout=900)
    if result.returncode:
        raise RuntimeError("Caption burn-in failed: " + (result.stderr or "")[-600:])
    log("Story Composer captions burned into the final output.")



def _concat_segments(
    segments: list[Path],
    output: Path,
    *,
    duration_seconds: float,
    has_audio: bool,
    audio_plan,
    edl_segments,
    transitions,
    log,
) -> bool:
    """Join vertical video streams and smooth hard-cut dialogue boundaries."""
    inputs = []
    filters = []
    video_labels = []
    audio_labels = []
    for index, segment in enumerate(segments):
        inputs.extend(["-i", str(segment)])
        video_label = f"v{index}"
        filters.append(
            f"[{index}:v]setpts=PTS-STARTPTS,fps=30,format=yuv420p[{video_label}]"
        )
        video_labels.append(f"[{video_label}]")
        if has_audio:
            audio_label = f"a{index}"
            volume = float(getattr(audio_plan, "source_gain_db", 0.0))
            filters.append(
                f"[{index}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                f"volume={volume}dB,asetpts=PTS-STARTPTS[{audio_label}]"
            )
            audio_labels.append(f"[{audio_label}]")
    transition_map = {
        (item.from_segment_id, item.to_segment_id): item
        for item in transitions
    }
    if len(video_labels) == 1:
        current_video = video_labels[0]
        current_video_duration = edl_segments[0].duration_seconds
    else:
        current_video = video_labels[0]
        current_video_duration = edl_segments[0].duration_seconds
        for index in range(1, len(video_labels)):
            left, right = edl_segments[index - 1], edl_segments[index]
            transition = transition_map.get((left.segment_id, right.segment_id))
            kind = getattr(getattr(transition, "kind", "hard_cut"), "value", getattr(transition, "kind", "hard_cut"))
            if kind == "cross_dissolve":
                requested = float(getattr(transition, "duration_seconds", 0.25) or 0.25)
                dissolve = min(max(0.05, requested), min(current_video_duration, right.duration_seconds) * 0.25)
                offset = max(0.0, current_video_duration - dissolve)
                output_label = f"vx{index}"
                filters.append(
                    f"{current_video}{video_labels[index]}xfade=transition=fade:"
                    f"duration={dissolve:.3f}:offset={offset:.3f}[{output_label}]"
                )
                current_video = f"[{output_label}]"
                current_video_duration += right.duration_seconds - dissolve
            else:
                output_label = f"vx{index}"
                filters.append(
                    f"{current_video}{video_labels[index]}concat=n=2:v=1:a=0[{output_label}]"
                )
                current_video = f"[{output_label}]"
                current_video_duration += right.duration_seconds
    video_padding = max(0.0, duration_seconds - current_video_duration)
    if video_padding > 0.001:
        filters.append(
            f"{current_video}tpad=stop_mode=clone:stop_duration={video_padding:.3f},"
            f"trim=duration={duration_seconds:.3f}[vout]"
        )
    else:
        filters.append(f"{current_video}trim=duration={duration_seconds:.3f}[vout]")
    use_crossfade = (
        getattr(audio_plan, "allow_crossfade", True)
        and getattr(getattr(audio_plan, "continuity", "smart"), "value", getattr(audio_plan, "continuity", "smart")) == "smart"
    )
    if has_audio:
        if len(audio_labels) == 1:
            filters.append(f"{audio_labels[0]}anull[a_joined]")
        elif use_crossfade:
            current = audio_labels[0]
            for index, next_label in enumerate(audio_labels[1:], 1):
                output_label = f"ac{index}"
                left, right = edl_segments[index - 1], edl_segments[index]
                transition = transition_map.get((left.segment_id, right.segment_id))
                kind = getattr(getattr(transition, "kind", "hard_cut"), "value", getattr(transition, "kind", "hard_cut"))
                requested = (
                    float(getattr(transition, "duration_seconds", 0.25) or 0.25)
                    if kind == "cross_dissolve" else 0.06
                )
                fade_duration = min(max(0.04, requested), min(left.duration_seconds, right.duration_seconds) * 0.25)
                filters.append(
                    f"{current}{next_label}acrossfade=d={fade_duration:.3f}:c1=tri:c2=tri[{output_label}]"
                )
                current = f"[{output_label}]"
            filters.append(
                f"{current}apad=whole_dur={duration_seconds:.3f},"
                f"atrim=duration={duration_seconds:.3f}[aout]"
            )
        else:
            filters.append(
                "".join(audio_labels) + f"concat=n={len(segments)}:v=0:a=1[a_joined]"
            )
            filters.append(
                f"[a_joined]apad=whole_dur={duration_seconds:.3f},"
                f"atrim=duration={duration_seconds:.3f}[aout]"
            )
    command = [
        FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
        *inputs, "-filter_complex", ";".join(filters),
        "-map", "[vout]",
    ]
    if has_audio:
        command.extend(["-map", "[aout]" if len(audio_labels) > 1 else "[a_joined]"])
    command.extend(video_encoder_args(FFMPEG,19))
    if has_audio:
        command.extend(["-c:a", "aac", "-b:a", "160k"])
    command.extend(["-movflags", "+faststart", str(output)])
    result = silent_run(command, capture_output=True, text=True, timeout=1200)
    if result.returncode or not output.is_file() or output.stat().st_size <= 0:
        has_dissolve = any(
            getattr(getattr(item.kind, "value", item.kind), "lower", lambda: str(item.kind))() == "cross_dissolve"
            for item in transitions
        )
        if has_dissolve:
            raise RuntimeError(
                "The requested cross-dissolve could not be rendered by this FFmpeg build: "
                + (result.stderr or "")[-500:]
            )
        log("Filtered join failed; using a hard-cut stream-copy fallback. Audio crossfades are unavailable for this export.")
        with tempfile.TemporaryDirectory(prefix="vaw-concat-fallback-") as fallback_dir:
            listing = Path(fallback_dir) / "concat.txt"
            lines = [
                "file '" + str(path).replace("\\", "/").replace("'", "'\\''") + "'"
                for path in segments
            ]
            listing.write_text("\n".join(lines) + "\n", encoding="utf-8")
            fallback = silent_run([
                FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
                "-f", "concat", "-safe", "0", "-i", str(listing),
                "-c", "copy", "-movflags", "+faststart", str(output),
            ], capture_output=True, text=True, timeout=900)
            if fallback.returncode or not output.is_file() or output.stat().st_size <= 0:
                raise RuntimeError(
                    "Could not join Story Composer segments: "
                    + ((result.stderr or "") + " " + (fallback.stderr or ""))[-800:]
                )

def render_composition(
    bundle: AnalysisBundle,
    edl: EditDecisionList,
    output_path: str | Path,
    *,
    layout: str = "blur",
    auto_reframe: bool = True,
    scene_detection: bool = True,
    subject_mode: str = "universal",
    resolution: str | None = None,
    log=print,
) -> dict:
    """Render a validated multi-segment EDL as one vertical MP4 with sidecars."""
    report = validate_edl(edl, bundle.source)
    if not report.valid:
        raise ValueError("Cannot render invalid EDL: " + "; ".join(x.message for x in report.issues))
    output = _unique_output(Path(output_path).resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    if layout not in {"blur", "fit", "crop"}:
        raise ValueError("Unknown vertical layout.")
    if resolution is None:
        resolution = "1080p" if edl.render.width >= 1080 else "720p"

    picks = []
    for index, segment in enumerate(edl.segments, 1):
        event = next((item for item in bundle.events if item.event_id in segment.event_ids), None)
        picks.append({
            "start": segment.source_in,
            "duration": segment.duration_seconds,
            "title": event.topic if event else f"Story segment {index}",
            "reason": segment.reason,
            "score": round((event.confidence if event else 0.0) * 100),
            "editorial_rank": index,
        })

    log(f"Video encoder: {video_encoder_label(FFMPEG)}.")
    log(f"Rendering {edl.title}: {len(picks)} complete segments, {edl.duration_seconds:.1f}s total.")
    with tempfile.TemporaryDirectory(prefix="vaw-story-render-", dir=str(output.parent)) as temporary:
        work = Path(temporary)
        segments_dir = work / "segments"
        segments_dir.mkdir()
        rendered = export_v04(
            bundle.source.path,
            segments_dir,
            picks,
            auto=auto_reframe,
            scenes=scene_detection,
            captions=False,
            burn=False,
            style=edl.captions.preset_id,
            layout=layout,
            subject_mode=subject_mode,
            resolution=resolution,
            log=log,
        )
        good = [
            Path(item["output"]).resolve()
            for item in rendered.get("clips", [])
            if item.get("ok") and Path(item.get("output", "")).is_file()
        ]
        if len(good) != len(picks):
            errors = [
                item.get("error", "segment render failed")
                for item in rendered.get("clips", []) if not item.get("ok")
            ]
            raise RuntimeError(
                f"Story Composer rendered {len(good)}/{len(picks)} segments. "
                + " | ".join(errors[:3])
            )

        intermediate = work / "composition.mp4"
        concat_fallback = _concat_segments(
            good,
            intermediate,
            duration_seconds=edl.duration_seconds,
            has_audio=bundle.source.has_audio,
            audio_plan=edl.audio,
            edl_segments=edl.segments,
            transitions=edl.transitions,
            log=log,
        )

        caption_rows = _caption_rows(bundle, edl) if edl.captions.enabled else []
        srt_path, ass_path = _write_subtitles(
            output,
            caption_rows,
            edl.captions.preset_id,
            export_srt=edl.captions.export_srt,
            burn_in=edl.captions.burn_in,
            uppercase=edl.captions.uppercase,
        )
        if edl.captions.enabled and edl.captions.burn_in and ass_path:
            burn_temp = work / "captioned.mp4"
            _burn_ass(intermediate, ass_path, burn_temp, log)
            os.replace(burn_temp, output)
        else:
            os.replace(intermediate, output)

    edl_path = output.with_suffix(".edl.json")
    analysis_path = output.with_suffix(".analysis.json")
    edl_path.write_text(dumps_contract(edl), encoding="utf-8")
    analysis_path.write_text(dumps_contract(bundle), encoding="utf-8")
    manifest = {
        "version": "1.2",
        "created_at": datetime.now().astimezone().isoformat(),
        "source": bundle.source.path,
        "output": str(output),
        "strategy": edl.strategy.value,
        "title": edl.title,
        "duration_seconds": edl.duration_seconds,
        "segments": len(edl.segments),
        "resolution": resolution,
        "edl": str(edl_path),
        "analysis": str(analysis_path),
        "srt": str(srt_path) if srt_path else None,
        "ass": str(ass_path) if ass_path else None,
        "warnings": (
            ["Audio crossfades were unavailable; hard-cut audio fallback was used."]
            if concat_fallback else []
        ),
    }
    output.with_suffix(".composition.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log(f"{edl.title} exported: {output.name} ({edl.duration_seconds:.1f}s).")
    return manifest
