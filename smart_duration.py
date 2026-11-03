"""Context-aware clip boundary analysis for VAW ClipForge v0.9.

Whisper runs locally. It is used to snap AI-selected story ranges to complete
spoken sentences, not to choose highlights by itself. Transcript cache stays
inside the export folder and is keyed to the exact source file.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_END = re.compile(r"""[.!?…]["'”’)\]]*$""")

def _patch_av_compat():
    """faster-whisper compatibility with PyAV versions that removed metadata_errors."""
    try:
        import av
        if (getattr(av.open, "_vaw_context_compat", False)
                or getattr(av.open, "_vaw_patched", False)
                or getattr(av.open, "_vaw_compat", False)):
            return
        original = av.open
        def compatible(*args, **kwargs):
            kwargs.pop("metadata_errors", None)
            return original(*args, **kwargs)
        compatible._vaw_context_compat = True
        av.open = compatible
    except Exception:
        # The transcriber will surface a useful error if PyAV is unavailable.
        return

def _is_sentence_end(text: str) -> bool:
    return bool(_END.search(str(text).strip()))

def _build_sentences(words: list[dict]) -> list[dict]:
    """Build utterance spans from Whisper word timestamps and natural pauses."""
    spans = []
    current = []

    def flush():
        nonlocal current
        if not current:
            return
        spans.append({
            "start": round(float(current[0]["start"]), 3),
            "end": round(float(current[-1]["end"]), 3),
            "text": " ".join(x["text"] for x in current).strip(),
            "word_count": len(current),
        })
        current = []

    for word in words:
        if not word.get("text"):
            continue
        if current:
            gap = float(word["start"]) - float(current[-1]["end"])
            # Do not impose an arbitrary time split inside a long sentence.
            if gap > 0.95 or _is_sentence_end(current[-1]["text"]):
                flush()
        current.append(word)
        if _is_sentence_end(word["text"]):
            flush()
    flush()
    return [s for s in spans if s["end"] > s["start"]]

def analyze_boundaries(source, cache_dir, model_size="base", log=print):
    """Transcribe a source locally and cache sentence-level boundary candidates."""
    source = Path(source).resolve()
    cache_dir = Path(cache_dir).resolve()
    if not source.is_file():
        raise FileNotFoundError("Source video is unavailable for local transcript analysis.")
    stat = source.stat()
    fingerprint = {
        "path": str(source),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "model": model_size,
        "version": 2,
    }
    cache = cache_dir / "context-boundaries-v09.json"
    if cache.is_file():
        try:
            saved = json.loads(cache.read_text(encoding="utf-8"))
            if saved.get("fingerprint") == fingerprint and saved.get("sentences"):
                log("Reused cached local transcript boundaries.")
                return saved["sentences"]
        except (OSError, ValueError, TypeError):
            pass

    _patch_av_compat()
    from auto_captions import get_model
    model = get_model(model_size, log)
    log("Context analysis: transcribing source locally to find complete sentence boundaries...")
    segments, info = model.transcribe(
        str(source), beam_size=1, best_of=1, word_timestamps=True,
        vad_filter=True, condition_on_previous_text=False,
    )
    words = []
    for segment in segments:
        segment_words = getattr(segment, "words", None) or []
        if segment_words:
            for item in segment_words:
                try:
                    start, end = float(item.start), float(item.end)
                    text = str(item.word).strip()
                except (TypeError, ValueError, AttributeError):
                    continue
                if text and end > start:
                    words.append({"start": start, "end": end, "text": text})
        else:
            text = str(getattr(segment, "text", "")).strip()
            tokens = text.split()
            start = float(segment.start)
            end = float(segment.end)
            if tokens and end > start:
                step = (end - start) / len(tokens)
                words.extend({
                    "start": start + i * step,
                    "end": start + (i + 1) * step,
                    "text": token,
                } for i, token in enumerate(tokens))

    if not words:
        raise RuntimeError("Whisper could not produce word timestamps for boundary analysis.")
    sentences = _build_sentences(words)
    if not sentences:
        raise RuntimeError("No usable sentence boundaries were detected.")
    cache_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "fingerprint": fingerprint,
        "language": getattr(info, "language", None),
        "word_count": len(words),
        "sentence_count": len(sentences),
        "sentences": sentences,
    }
    cache.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"Local transcript ready: {len(words)} words, {len(sentences)} utterance boundaries.")
    return sentences

def align_interval(start, end, sentences, total, min_duration=12.0, max_duration=180.0):
    """Snap a candidate to natural utterance boundaries without imposing target length."""
    start = max(0.0, min(float(total), float(start)))
    end = max(start, min(float(total), float(end)))
    if not sentences:
        duration = end - start
        if min_duration <= duration <= max_duration:
            return start, end, {"start": "model", "end": "model"}
        return None

    spans = sorted(sentences, key=lambda x: float(x["start"]))
    start_kind = "model"
    end_kind = "model"

    # Start at the beginning of the sentence that contains the AI's proposed hook.
    containing = next((s for s in spans
                       if float(s["start"]) - .05 <= start <= float(s["end"]) + .05), None)
    if containing:
        # Always include the full opening sentence, even if it starts several
        # seconds before Gemini's approximate timestamp.
        start = float(containing["start"])
        start_kind = "sentence"
    else:
        nearest = min(spans, key=lambda s: abs(float(s["start"]) - start))
        if abs(float(nearest["start"]) - start) <= 2.75:
            start = float(nearest["start"])
            start_kind = "sentence"

    # Finish at the end of the sentence containing the AI's proposed payoff.
    containing = next((s for s in spans
                       if float(s["start"]) + .05 <= end <= float(s["end"]) + .05), None)
    if containing:
        # Always finish the sentence containing the proposed payoff.
        end = float(containing["end"])
        end_kind = "sentence"
    else:
        following = next((s for s in spans if float(s["start"]) >= end - .05), None)
        previous = next((s for s in reversed(spans) if float(s["end"]) <= end + .05), None)
        # Prefer the sentence that just finished when the AI timestamp is in a pause.
        if previous and end - float(previous["end"]) <= 1.25:
            end = float(previous["end"])
            end_kind = "sentence"
        elif following and float(following["start"]) - end <= 1.75:
            end = float(following["end"])
            end_kind = "sentence"

    start = max(0.0, min(float(total), start))
    end = max(start, min(float(total), end))

    # A short candidate can grow to the next complete sentence; target seconds is soft.
    if end - start < min_duration:
        for span in spans:
            span_end = float(span["end"])
            if span_end > end and span_end - start <= max_duration:
                end = span_end
                end_kind = "sentence"
                if end - start >= min_duration:
                    break

    # Never truncate a longer story just to fit a Shorts limit. Gemini must
    # propose a shorter, independently complete story beat; otherwise skip it.
    if end - start > max_duration:
        return None

    duration = end - start
    if duration < min_duration or duration > max_duration or end <= start:
        return None
    return round(start, 3), round(end, 3), {
        "start": start_kind,
        "end": end_kind,
    }
