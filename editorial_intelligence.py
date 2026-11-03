"""Deterministic editorial scoring and local HTML report for VAW ClipForge v1.0."""
from __future__ import annotations
import html
import json
from pathlib import Path

WEIGHTS = {
    "hook_strength": 0.18,
    "payoff_strength": 0.18,
    "context_independence": 0.15,
    "clarity": 0.10,
    "visual_interest": 0.12,
    "pacing": 0.10,
    "novelty": 0.07,
    "retention_potential": 0.10,
}
VISUAL_TYPES = {
    "animation", "illustration", "infographic", "diagram",
    "screen_recording", "live_action", "mixed", "unknown",
}
RETENTION_RISKS = {
    "none", "slow_opening", "context_heavy", "repetitive",
    "low_visual_change", "weak_payoff", "abrupt_transition", "uncertain",
}


def _score(value, fallback=50.0):
    try:
        result = float(value)
        if result != result or result in (float("inf"), float("-inf")):
            return float(fallback)
        return max(0.0, min(100.0, result))
    except (TypeError, ValueError):
        return float(fallback)


def enrich_candidate(row):
    """Attach explainable weighted scores; never interpret scores as view guarantees."""
    base = _score(row.get("score", 50))
    metric_count = sum(row.get(k) is not None for k in WEIGHTS)
    metrics = {key: _score(row.get(key), base) for key in WEIGHTS}
    if metric_count >= 3:
        weighted = sum(metrics[k] * weight for k, weight in WEIGHTS.items())
        editorial = weighted if metric_count == len(WEIGHTS) else (weighted * 0.82 + base * 0.18)
    else:
        editorial = base
    retention = _score(row.get("retention_potential"),
                       metrics["hook_strength"] * 0.45
                       + metrics["payoff_strength"] * 0.35
                       + metrics["pacing"] * 0.20 if metric_count else base)
    visual_type = str(row.get("visual_type", "unknown")).strip().lower()
    if visual_type not in VISUAL_TYPES:
        visual_type = "unknown"
    risk = str(row.get("retention_risk", "uncertain")).strip().lower()
    if risk not in RETENTION_RISKS:
        risk = "uncertain"
    result = dict(row)
    result.update({
        **metrics,
        "ai_score": round(base, 1),
        "editorial_score": round(editorial, 1),
        "retention_potential": round(retention, 1),
        "visual_type": visual_type,
        "visual_notes": str(row.get("visual_notes", "Not assessed by model."))[:420],
        "retention_risk": risk,
        "retention_reason": str(row.get("retention_reason", ""))[:420],
        "edit_suggestion": str(row.get("edit_suggestion", ""))[:420],
        "metric_coverage": metric_count,
        "metrics_reported": [key for key in WEIGHTS if row.get(key) is not None],
    })
    return result


def _bar(label, value):
    name = html.escape(label.replace("_", " ").title())
    if value is None:
        return '<div class="metric"><div><span>' + name + '</span><b>n/a</b></div><div class="track"></div></div>'
    value = _score(value)
    return (
        '<div class="metric"><div><span>' + name
        + '</span><b>' + str(round(value)) + '</b></div><div class="track"><i style="width:'
        + str(round(value)) + '%"></i></div></div>'
    )


def write_editorial_report(manifest, output_path):
    """Write a self-contained report; no CDN, scripts, analytics, or network calls."""
    output_path = Path(output_path)
    ranked = manifest.get("ranked_candidates", [])
    selected = [x for x in ranked if x.get("selection_status") == "selected"]
    if not selected:
        selected = manifest.get("clips", [])
    cards = []
    for item in ranked:
        selected_flag = item.get("selection_status") == "selected"
        title = html.escape(str(item.get("title") or "Untitled candidate"))
        reason = html.escape(str(item.get("reason") or ""))
        hook = html.escape(str(item.get("hook") or ""))
        context = html.escape(str(item.get("context") or ""))
        payoff = html.escape(str(item.get("payoff") or ""))
        visual_notes = html.escape(str(item.get("visual_notes") or ""))
        retention_reason = html.escape(str(item.get("retention_reason") or ""))
        edit = html.escape(str(item.get("edit_suggestion") or ""))
        risk = html.escape(str(item.get("retention_risk") or "uncertain")).replace("_", " ")
        visual_type = html.escape(str(item.get("visual_type") or "unknown")).replace("_", " ")
        status = "SELECTED" if selected_flag else html.escape(str(item.get("selection_status") or "ranked")).upper()
        start = float(item.get("start", 0))
        end = float(item.get("end", 0))
        duration = float(item.get("duration", max(0, end-start)))
        reported = set(item.get("metrics_reported", []))
        metrics = "".join(_bar(k, item.get(k) if k in reported else None) for k in WEIGHTS)
        if not reported:
            metrics = '<p class="muted">Individual dimension scores unavailable; legacy overall score used.</p>'
        cards.append(
            '<article class="candidate"><header><div><span class="rank">#'
            + str(item.get("editorial_rank", "?")) + '</span><span class="status">'
            + status + '</span></div><strong>' + str(round(_score(item.get("editorial_score", 0))))
            + '<small>/100 editorial</small></strong></header><h2>' + title + '</h2>'
            + '<p class="time">' + f'{start:.1f}s – {end:.1f}s · {duration:.1f}s'
            + ' · Retention potential ' + str(round(_score(item.get("retention_potential", 0))))
            + '/100</p><p>' + reason + '</p><div class="story">'
            + '<div><label>HOOK</label><p>' + hook + '</p></div>'
            + '<div><label>CONTEXT</label><p>' + context + '</p></div>'
            + '<div><label>PAYOFF</label><p>' + payoff + '</p></div></div>'
            + '<details><summary>Editorial breakdown</summary><div class="metrics">' + metrics
            + '</div><p><b>Visual:</b> ' + visual_type + ' — ' + visual_notes + '</p>'
            + '<p><b>Retention risk:</b> ' + risk + '. ' + retention_reason + '</p>'
            + '<p><b>Edit suggestion:</b> ' + edit + '</p></details></article>'
        )
    avg = (sum(_score(x.get("editorial_score")) for x in selected) / len(selected)) if selected else 0
    source = html.escape(str(manifest.get("source", "Unknown source")))
    model = html.escape(str(manifest.get("model", "Unknown model")))
    generated = html.escape(str(manifest.get("created", "")))
    note = html.escape(str(manifest.get("retention_note",
        "Retention potential is an AI editorial estimate, not a prediction of actual views or watch time.")))
    page = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>VAW ClipForge Editorial Report</title>
<style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#0d111b;color:#eef2fb;font:15px/1.55 Segoe UI,Arial,sans-serif}
main{max-width:1050px;margin:auto;padding:34px 22px 60px}.eyebrow{color:#f16b7d;letter-spacing:.14em;font-size:12px;font-weight:700}
h1{font-size:32px;margin:5px 0 4px}.muted,.time,small{color:#9daac0}.meta{overflow-wrap:anywhere;font-size:13px;margin:12px 0 22px}
.summary{display:flex;gap:14px;flex-wrap:wrap;margin:20px 0 28px}.stat{background:#171e2c;border:1px solid #303b50;border-radius:14px;padding:15px 18px;min-width:160px}
.stat b{display:block;font-size:27px}.candidate{background:#151c29;border:1px solid #344057;border-radius:16px;padding:20px;margin:16px 0}
header{display:flex;justify-content:space-between;align-items:center;gap:12px}.rank{font-size:21px;font-weight:800;color:#ff7185;margin-right:12px}
.status{font-size:10px;letter-spacing:.1em;border:1px solid #60718e;border-radius:20px;padding:4px 9px;color:#b8c7df}
header strong{font-size:25px;text-align:right}header small{display:block;font-size:10px;font-weight:500}
h2{font-size:20px;margin:14px 0 2px}.story{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:16px 0}
.story>div{background:#1c2637;border-radius:10px;padding:12px}.story label{font-size:10px;letter-spacing:.12em;color:#ff8293;font-weight:800}
.story p{margin:5px 0 0}.metrics{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin:14px 0}
.metric>div:first-child{display:flex;justify-content:space-between;font-size:12px}.track{height:6px;background:#303b50;border-radius:9px;overflow:hidden;margin-top:4px}
.track i{display:block;height:100%;background:#e45c72}details{margin-top:15px}summary{cursor:pointer;color:#bdc9dc}
footer{margin-top:28px;color:#9daac0;font-size:12px;border-top:1px solid #303b50;padding-top:18px}
@media(max-width:650px){.story{grid-template-columns:1fr}.metrics{grid-template-columns:1fr}main{padding:22px 14px}}
</style></head><body><main><div class="eyebrow">VAW / CLIPFORGE · V1.0</div>
<h1>AI Editorial Intelligence</h1><div class="muted">Story quality · visual relevance · retention potential</div>
<div class="meta">Source: """ + source + """<br>Model: """ + model + """ · """ + generated + """</div>
<section class="summary"><div class="stat"><b>""" + str(len(ranked)) + """</b><span class="muted">Valid candidates ranked</span></div>
<div class="stat"><b>""" + str(len(selected)) + """</b><span class="muted">Selected clips</span></div>
<div class="stat"><b>""" + str(round(avg)) + """/100</b><span class="muted">Average selected editorial score</span></div></section>
""" + ("".join(cards) if cards else '<p>No valid candidates to review.</p>') + """
<footer>""" + note + """<br>AI-assisted editorial guidance only. Review the original context, factual accuracy, rights, subtitles and final cut before publishing. This report is generated locally.</footer>
</main></body></html>"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(page, encoding="utf-8")
    return output_path
