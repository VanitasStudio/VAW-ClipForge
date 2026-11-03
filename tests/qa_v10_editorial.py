from pathlib import Path
import tempfile
from clipforge.editorial_intelligence import enrich_candidate, write_editorial_report
from clipforge.gemini_highlights import select_best, rank_candidates

def candidate(start,end,title,base,metrics,visual="animation"):
    return {
        "start":start,"end":end,"score":base,"complete":True,
        "title":title,"reason":"A self-contained story with a clear payoff.",
        "hook":"An unexpected opening question.",
        "context":"The minimum setup a new viewer needs.",
        "payoff":"A satisfying answer or reveal.",
        "visual_type":visual,"visual_notes":"Frames show a clear animated diagram.",
        "retention_risk":"none","retention_reason":"Question opens and resolves.",
        "edit_suggestion":"Hold the graphic through the reveal.",
        **metrics
    }

strong={
 "hook_strength":95,"payoff_strength":94,"context_independence":93,
 "clarity":91,"visual_interest":88,"pacing":90,"novelty":89,
 "retention_potential":94
}
weak={
 "hook_strength":48,"payoff_strength":42,"context_independence":55,
 "clarity":58,"visual_interest":50,"pacing":45,"novelty":40,
 "retention_potential":43
}
medium={
 "hook_strength":78,"payoff_strength":76,"context_independence":80,
 "clarity":82,"visual_interest":75,"pacing":78,"novelty":73,
 "retention_potential":79
}
rows=[
 candidate(10,40,"Strong animation story",70,strong),
 candidate(15,45,"Weak but loud moment",98,weak),
 candidate(65,95,"Second useful story",77,medium,"infographic"),
]
enriched=enrich_candidate(rows[0])
assert enriched["editorial_score"]>90,enriched
selected,ranked=select_best(rows,2,120,30,return_ranked=True)
assert len(ranked)==3,ranked
assert ranked[0]["title"]=="Strong animation story",[(x["title"],x["editorial_score"]) for x in ranked]
assert len(selected)==2,selected
assert {x["title"] for x in selected}=={"Strong animation story","Second useful story"},selected
weak_row=next(x for x in ranked if x["title"]=="Weak but loud moment")
assert weak_row["selection_status"]=="skipped_overlap",weak_row
assert selected[0]["editorial_rank"]==1
assert selected[0]["retention_potential"]==94
with tempfile.TemporaryDirectory(prefix="clipforge-v10-qa-") as tmp:
    manifest={
      "version":"v1.0","source":"synthetic-animation-documentary.mp4",
      "model":"mock-gemini","created":"2026-11-03T23:00:00",
      "retention_note":"AI estimate only; not a view prediction.",
      "ranked_candidates":ranked,"clips":selected
    }
    report=write_editorial_report(manifest,Path(tmp)/"ai-editorial-report.html")
    text=report.read_text(encoding="utf-8")
    assert "AI Editorial Intelligence" in text
    assert "Strong animation story" in text
    assert "HOOK" in text and "PAYOFF" in text
    assert "Retention potential" in text
    assert "not a view prediction" in text
    assert "animation" in text
print("EDITORIAL_SCORE",enriched["editorial_score"])
print("RANKING",[(x["editorial_rank"],x["title"],x["selection_status"]) for x in ranked])
print("SELECTED",[x["title"] for x in selected])
print("LOCAL_HTML_REPORT_PASS")
print("V10_EDITORIAL_QA_PASS")
