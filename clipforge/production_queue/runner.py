"""Reusable production pipeline adapter shared by single and batch workflows."""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable
from .models import JobRecord

LogCallback = Callable[[str], None]
ProgressCallback = Callable[[str, float | None], None]


def run_production(source_path: str | Path, output_directory: str | Path,
                   config: dict[str, Any], log: LogCallback = print,
                   progress: ProgressCallback | None = None) -> dict[str, Any]:
    """Run one complete ClipForge production using a frozen effective config."""
    source = Path(source_path).expanduser().resolve()
    destination = Path(output_directory).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Source video is unavailable: {source}")
    destination.mkdir(parents=True, exist_ok=True)
    def stage(name: str):
        if progress:
            progress(name, None)
    ai = bool(config.get("ai", True))
    visual = bool(config.get("visual", True))
    use_vision = bool(config.get("video_vision", False))
    standalone = bool(config.get("standalone", True))
    smart_compilation = bool(config.get("smart_compilation", False))
    narrative_reconstruction = bool(config.get("narrative_reconstruction", False))
    if not (standalone or smart_compilation or narrative_reconstruction):
        raise ValueError("At least one output mode must be enabled in the production preset.")
    if (smart_compilation or narrative_reconstruction) and not ai:
        raise ValueError("Story Composer requires Gemini AI editorial analysis.")
    if ai and not __import__("clipforge.secure_config", fromlist=["has_key"]).has_key():
        raise RuntimeError("Gemini API key is unavailable. Configure it before starting the batch.")

    count = int(config.get("count", 3))
    seconds = int(config.get("seconds", 30))
    story_seconds = int(config.get("story_seconds", 60))
    resolution = str(config.get("resolution", "1080p"))
    style = str(config.get("layout", "blur"))
    model = str(config.get("model", "gemini-3.5-flash-lite"))
    if not 1 <= count <= 20 or not 5 <= seconds <= 180:
        raise ValueError("Highlight count must be 1-20 and target duration 5-180 seconds.")
    if not 12 <= story_seconds <= 180:
        raise ValueError("Story Composer duration must be between 12 and 180 seconds.")
    if resolution not in {"720p", "1080p"}:
        raise ValueError("Output resolution must be 720p or 1080p.")
    if style not in {"blur", "fit", "crop"}:
        raise ValueError("Unknown vertical layout preset.")
    captions = bool(config.get("captions", True))
    burn = bool(config.get("burn", True))
    context_aware = bool(config.get("context_duration", True))
    subject_mode = str(config.get("subject_mode", "universal"))
    auto = bool(config.get("autoframe", True))
    scene = bool(config.get("scenedetect", True))
    cap_style = str(config.get("caption_style", "karaoke"))

    stage("Source validation")
    vision_result = None
    if ai:
        vision_frames = None
        if use_vision:
            log("Video Vision MCP: extracting a bounded set of local frames...")
            try:
                from clipforge.video_vision_adapter import VideoVisionMCPProvider
                from clipforge.vision_cache import CachedVisionProvider
                from clipforge.vision_quality import filter_vision_frames
                from clipforge.clip_engine import probe_duration
                provider = CachedVisionProvider(VideoVisionMCPProvider())
                vision_result = provider.analyze(source, duration_seconds=float(probe_duration(source)), max_frames=8)
                quality = filter_vision_frames(vision_result.frames, duration_seconds=float(probe_duration(source)), max_frames=8)
                vision_frames = quality.frames
                log(f"Video Vision MCP supplied {len(vision_frames)} additional frames (cache: {vision_result.metadata.get('cache','miss')}).")
                for warning in quality.warnings:
                    log("Vision quality: " + warning)
                for warning in vision_result.warnings:
                    log("Vision note: " + warning)
            except Exception as exc:
                log(f"Video Vision MCP unavailable; using built-in frame sampling instead. {type(exc).__name__}: {str(exc)[:160]}")
        stage("Editorial analysis")
        from clipforge.gemini_highlights import process_ai
        selection = process_ai(source, destination, count, seconds, style, model,
            log=log, visual=visual, render=False, context_aware=context_aware,
            duration_model="base", vision_frames=vision_frames)
    else:
        if context_aware:
            log("Context-aware sentence alignment requires Gemini AI; offline audio mode keeps the requested fixed duration.")
        stage("Local audio analysis")
        from clipforge.clip_engine import process as process_local
        selection = process_local(source, destination, count, seconds, style, log=log, dry_run=True)

    successes: list[str] = []
    failures: list[str] = []
    suggestion_items: list[dict[str, Any]] = []
    if standalone:
        stage("Standalone rendering")
        log("Rendering Standalone Highlights...")
        from clipforge.smart_reframe import export_v04
        outcome = export_v04(source, destination, selection["clips"], auto=auto, scenes=scene,
            captions=captions, burn=burn, style=cap_style, layout=style,
            subject_mode=subject_mode, resolution=resolution, log=log)
        completed = sum(bool(item.get("ok")) for item in outcome["clips"])
        suggestion_items.extend({"output": item.get("output"), "start": item.get("start", 0),
            "duration": item.get("duration", 0), "title": item.get("title", "Standalone Highlight"),
            "reason": item.get("reason", ""), "summary": item.get("payoff", "")}
            for item in outcome["clips"] if item.get("ok"))
        if completed:
            successes.append(f"Standalone Highlights: {completed}/{len(outcome['clips'])} clips")
        else:
            failures.append("Standalone Highlights: no clips rendered.")

    if smart_compilation or narrative_reconstruction:
        stage("Story Composer analysis")
        log("Building the unified analysis bundle for Story Composer...")
        from clipforge.unified_analyzer import probe_source, build_analysis_bundle
        from clipforge.smart_reframe import shot_boundaries
        from clipforge.gemini_highlights import request_story_compositions
        from clipforge.clipforge_contracts import CaptionPlan, CompositionStrategy, RenderSettings
        from clipforge.story_composer import build_composition
        from clipforge.composition_renderer import render_composition
        media = probe_source(source)
        cuts = shot_boundaries(source) if scene else []
        bundle = build_analysis_bundle(media, transcript_rows=selection.get("transcript_spans",[]),
            scene_cuts=cuts, editorial_rows=selection.get("ranked_candidates",[]))
        if vision_result is not None:
            try:
                from clipforge.multimodal_fusion import fuse_visual_evidence
                bundle = fuse_visual_evidence(bundle, vision_result, max_frames=8)
            except Exception as exc:
                log(f"Visual evidence fusion skipped: {str(exc)[:160]}")
        try:
            story = request_story_compositions(bundle.events)
            bundle = replace(bundle, composition_orders=story["composition_orders"],
                event_roles=story["event_roles"], event_dependencies=story["event_dependencies"])
            log("Gemini supplied separate Smart Compilation and Narrative Reconstruction story maps.")
        except Exception as exc:
            log(f"Story map unavailable; deterministic editorial ordering will be used. {type(exc).__name__}: {str(exc)[:150]}")
        strategies = []
        if smart_compilation:
            strategies.append(CompositionStrategy.SMART_COMPILATION)
        if narrative_reconstruction:
            strategies.append(CompositionStrategy.NARRATIVE_RECONSTRUCTION)
        width, height = (1080, 1920) if resolution == "1080p" else (720, 1280)
        for strategy in strategies:
            try:
                stage(f"Rendering {strategy.value}")
                edl = build_composition(bundle, strategy, target_duration_seconds=story_seconds)
                edl = replace(edl, captions=CaptionPlan(enabled=captions,preset_id=cap_style,burn_in=burn,export_srt=True),
                    render=RenderSettings(width=width,height=height,fps=30))
                output_path = destination / f"{source.stem}_{strategy.value}.mp4"
                rendered = render_composition(bundle,edl,output_path,layout=style,auto_reframe=auto,
                    scene_detection=scene,subject_mode=subject_mode,resolution=resolution,log=log)
                successes.append(f"{edl.title}: {rendered['duration_seconds']:.1f}s")
                for segment in edl.segments:
                    event = next((item for item in bundle.events if item.event_id in segment.event_ids),None)
                    suggestion_items.append({"output":str(rendered["output"]),"start":segment.source_in,
                        "duration":segment.duration_seconds,"title":event.topic if event else edl.title,
                        "reason":segment.reason,"summary":event.summary if event else ""})
            except Exception as exc:
                failures.append(f"{strategy.value}: {type(exc).__name__}: {str(exc)[:220]}")
                log(f"{strategy.value} failed: {str(exc)[:220]}")

    if not successes:
        raise RuntimeError("No requested output completed. " + " | ".join(failures))
    stage("Finalizing production assets")
    try:
        from clipforge.title_hashtag_suggestions import write_suggestion_markdown
        suggestion_file = write_suggestion_markdown(destination,suggestion_items,
            selection.get("transcript_spans",[]),allow_ai=ai)
        if suggestion_file:
            log(f"Title and hashtag suggestions saved: {suggestion_file.name}")
            successes.append("Title & Hashtag Suggestions: " + suggestion_file.name)
    except Exception as exc:
        failures.append("Title & Hashtag Suggestions: " + str(exc)[:180])
        log("Title/hashtag suggestions could not be generated: " + str(exc)[:180])
    summary = "\\n".join(successes) + f"\\n\\nOutput folder: {destination}"
    if failures:
        summary += "\\n\\nSome outputs could not be created:\\n" + "\\n".join(failures)
    return {"output_directory":str(destination),"successes":successes,"failures":failures,"summary":summary}


def run_job(job: JobRecord, progress: ProgressCallback, log: LogCallback = print) -> dict[str, Any]:
    return run_production(job.source_path, job.output_directory, job.config_snapshot, log, progress)
