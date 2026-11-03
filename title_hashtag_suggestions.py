"""Per-export YouTube Shorts title and hashtag suggestions.

Only compact, clip-scoped context is sent to Gemini. If the API is unavailable,
a deterministic local fallback still produces a useful Markdown file.
"""
from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path

from secure_config import load_key

MODEL = "gemini-3.6-flash"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
OUTPUT_NAME = "Title and Hashtag Suggestion.md"
MAX_ITEMS = 12  # Gemini batch size; every exported clip is included.
MAX_CONTEXT_CHARS = 420


def _clip_context(item: dict, transcript_spans: list[dict] | None) -> dict:
    start = float(item.get("start", item.get("source_in", 0)) or 0)
    end = float(item.get("end", item.get("source_out", start + float(item.get("duration", 0) or 0))) or start)
    excerpts = []
    for span in transcript_spans or []:
        try:
            if float(span.get("end", 0)) <= start or float(span.get("start", 0)) >= end:
                continue
            text = re.sub(r"\s+", " ", str(span.get("text", ""))).strip()
            if text:
                excerpts.append(text)
        except (TypeError, ValueError):
            continue
    excerpt = " ".join(excerpts)
    if len(excerpt) > MAX_CONTEXT_CHARS:
        excerpt = excerpt[:MAX_CONTEXT_CHARS].rsplit(" ", 1)[0] + "…"
    filename = Path(str(item.get("output") or item.get("filename") or "clip.mp4")).name
    return {
        "clip_id": str(item.get("clip_id") or f"{filename}|{start:.2f}|{end:.2f}"),
        "filename": filename,
        "start": round(start, 2),
        "end": round(end, 2),
        "topic": str(item.get("topic") or item.get("title") or item.get("reason") or "Short-form video"),
        "summary": str(item.get("summary") or item.get("reason") or item.get("payoff") or "")[:240],
        "transcript_excerpt": excerpt,
    }


def _fallback(context: dict) -> dict:
    source = context["topic"].strip()
    source = re.sub(r"\s+", " ", source).strip(" .!?")
    title = source[:68].rstrip(" :,-") or "A Moment Worth Understanding"
    words = re.findall(r"[A-Za-z0-9]+", (source + " " + context["transcript_excerpt"]).lower())
    stop = {"this", "that", "with", "from", "your", "what", "when", "where", "there", "their", "have", "about", "into", "then", "than", "they", "them", "just", "really", "very", "will", "would", "could", "should", "this", "clip", "video", "short"}
    tags = []
    for word in words:
        if len(word) < 4 or word in stop:
            continue
        tag = "#" + word.capitalize()
        if tag.lower() not in {value.lower() for value in tags}:
            tags.append(tag)
        if len(tags) == 5:
            break
    if not tags:
        tags = ["#YouTubeShorts", "#LearnSomething", "#Interesting"]
    return {
        "recommended_title": title,
        "title_options": [title, f"The Story Behind {title[:48]}", f"Why {title[:48]} Matters"],
        "hashtags": tags[:5],
        "angle": "Local fallback based on available clip metadata and transcript.",
    }


def _request_gemini(contexts: list[dict], key: str, model: str = MODEL) -> dict:
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,100}", model):
        raise ValueError("Invalid Gemini model identifier.")
    prompt = (
        "You are a YouTube Shorts packaging editor. For each clip, create an accurate, "
        "high-curiosity but non-misleading short title and relevant hashtags. The channel "
        "publishes in English. Do not invent facts, names, claims, or events. Avoid generic "
        "clickbait, ALL CAPS, emoji stuffing, and hashtags unrelated to the actual clip. "
        "Return 3 distinct title options (ideally 35-65 characters, hard max 75), one "
        "recommended title, 5-8 useful hashtags (mix of specific topic and relevant niche; "
        "include #Shorts only when appropriate), and a one-sentence angle. Keep each clip "
        "strictly matched by clip_id. Return only JSON with shape "
        '{"clips":[{"clip_id":"...","recommended_title":"...","title_options":["..."],'
        '"hashtags":["#..."],"angle":"..."}]}.\n\nCLIPS:\n'
        + json.dumps(contexts, ensure_ascii=False)
    )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.35,
            "maxOutputTokens": 4096,
        },
    }
    request = urllib.request.Request(
        ENDPOINT.format(model=model),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        raw = response.read(500001)
    if len(raw) > 500000:
        raise ValueError("Gemini title response exceeded the response limit.")
    envelope = json.loads(raw.decode("utf-8"))
    text = envelope["candidates"][0]["content"]["parts"][0]["text"]
    data = json.loads(text)
    if not isinstance(data.get("clips"), list):
        raise ValueError("Gemini returned an invalid clip suggestions payload.")
    return data


def generate_suggestions(
    items: list[dict],
    transcript_spans: list[dict] | None = None,
    *,
    provider=None,
    key: str | None = None,
    model: str = MODEL,
    allow_ai: bool = False,
) -> tuple[list[dict], str]:
    contexts = [_clip_context(item, transcript_spans) for item in items]
    if not contexts:
        return [], "No successful clips were available."
    generated = {}
    if allow_ai:
        try:
            api_key = key or (load_key() if provider is None else None)
        except Exception:
            api_key = None
        if provider is not None or api_key:
            for offset in range(0, len(contexts), MAX_ITEMS):
                batch = contexts[offset:offset + MAX_ITEMS]
                try:
                    response = provider(batch, key, model) if provider else _request_gemini(
                        batch, api_key, model
                    )
                    if not isinstance(response, dict) or not isinstance(response.get("clips"), list):
                        raise ValueError("Invalid title suggestion response.")
                    for row in response["clips"]:
                        if isinstance(row, dict) and row.get("clip_id"):
                            generated[str(row["clip_id"])] = row
                except Exception:
                    continue
    if not generated:
        mode = "local fallback"
    elif len(generated) >= len(contexts):
        mode = "Gemini"
    else:
        mode = "Gemini + local fallback"
    results = []
    for context in contexts:
        row = generated.get(context["clip_id"], {})
        fallback = _fallback(context)
        title = str(row.get("recommended_title") or fallback["recommended_title"]).strip()[:75]
        options = row.get("title_options")
        if not isinstance(options, list):
            options = fallback["title_options"]
        options = [str(value).strip()[:75] for value in options if str(value).strip()][:3]
        if title not in options:
            options.insert(0, title)
        hashtags = row.get("hashtags")
        if not isinstance(hashtags, list):
            hashtags = fallback["hashtags"]
        clean_tags = []
        for tag in hashtags:
            tag = "#" + re.sub(r"[^A-Za-z0-9_]", "", str(tag).lstrip("#"))
            if len(tag) > 1 and tag.lower() not in {value.lower() for value in clean_tags}:
                clean_tags.append(tag)
            if len(clean_tags) == 8:
                break
        results.append({
            **context,
            "recommended_title": title,
            "title_options": options[:3],
            "hashtags": clean_tags or fallback["hashtags"],
            "angle": str(row.get("angle") or fallback["angle"])[:240],
        })
    return results, mode


def write_suggestion_markdown(
    output_dir: str | Path,
    items: list[dict],
    transcript_spans: list[dict] | None = None,
    *,
    provider=None,
    key: str | None = None,
    model: str = MODEL,
    allow_ai: bool = False,
) -> Path | None:
    suggestions, mode = generate_suggestions(
        items, transcript_spans, provider=provider, key=key, model=model,
        allow_ai=allow_ai,
    )
    if not suggestions:
        return None
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / OUTPUT_NAME
    lines = [
        "# Title and Hashtag Suggestions",
        "",
        f"> Generated: {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')}  ",
        f"> Source: {mode}  ",
        f"> Clips: {len(suggestions)}",
        "",
        "Use the recommended title as the starting point. Check that it accurately represents the clip before publishing.",
        "",
    ]
    for index, item in enumerate(suggestions, 1):
        lines.extend([
            f"## Clip {index} — {item['filename']}",
            "",
            f"**Recommended title**  ",
            item["recommended_title"],
            "",
            "**Alternative titles**",
            *[f"{number}. {title}" for number, title in enumerate(item["title_options"], 1)],
            "",
            "**Hashtags**",
            " ".join(item["hashtags"]),
            "",
            f"**Angle**  ",
            item["angle"],
            "",
            f"<sub>Source time: {item['start']:.2f}s – {item['end']:.2f}s</sub>",
            "",
            "---",
            "",
        ])
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
