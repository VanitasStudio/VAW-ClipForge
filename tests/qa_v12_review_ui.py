"""Tkinter construction and edit/save smoke test for the multi-segment Review Studio."""
from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from clipforge_contracts import (
    AnalysisBundle, EditorialEvent, SegmentRole, TranscriptSpan,
    CompositionStrategy, dumps_contract,
)
from composition_review import CompositionReview
from story_composer import build_composition
from unified_analyzer import probe_source


ROOT = Path(__file__).resolve().parents[1]


class CompositionReviewUITests(unittest.TestCase):
    def test_review_studio_builds_and_saves_edits(self):
        source_path = ROOT / "samples" / "synthetic-demo.mp4"
        if not source_path.is_file():
            self.skipTest("Synthetic source fixture is unavailable.")
        source = probe_source(source_path)
        bundle = AnalysisBundle(
            "review-ui", source,
            transcript=(TranscriptSpan("caption-1", 2, 5, "Original caption text"),),
            events=(
                EditorialEvent("hook", 1, 14, "Hook", "Opening", SegmentRole.HOOK, .9),
                EditorialEvent("payoff", 20, 33, "Payoff", "Ending", SegmentRole.PAYOFF, .9),
            ),
        )
        edl = build_composition(bundle, CompositionStrategy.NARRATIVE_RECONSTRUCTION, target_duration_seconds=30)
        with tempfile.TemporaryDirectory(prefix="clipforge-review-ui-") as temp:
            edl_path = Path(temp) / "story.edl.json"
            analysis_path = Path(temp) / "story.analysis.json"
            edl_path.write_text(dumps_contract(edl), encoding="utf-8")
            analysis_path.write_text(dumps_contract(bundle), encoding="utf-8")
            try:
                app = CompositionReview(edl_path)
            except Exception as exc:
                if "display" in str(exc).lower() or "tk" in str(exc).lower():
                    self.skipTest(f"Tk display unavailable: {exc}")
                raise
            try:
                app.root.withdraw()
                app.root.update_idletasks()
                self.assertEqual(app.listbox.size(), 2)
                self.assertIsNotNone(app.timeline_canvas)
                self.assertIsNotNone(app.preview_label)
                self.assertIsNotNone(app.caption_list)
                self.assertEqual(app.caption_list.size(), 1)
                app.caption_var.set("Edited caption text")
                app._apply_caption()
                self.assertEqual(app.bundle.transcript[0].text, "Edited caption text")

                app.transition_var.set("cross_dissolve")
                app._apply_segment()
                self.assertEqual(app.edl.transitions[0].kind.value, "cross_dissolve")

                app.title_var.set("Edited Review Composition")
                app._save()
                saved_edl = json.loads(edl_path.read_text(encoding="utf-8"))
                saved_analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
                self.assertEqual(saved_edl["title"], "Edited Review Composition")
                self.assertEqual(saved_analysis["transcript"][0]["text"], "Edited caption text")
            finally:
                app.root.destroy()


if __name__ == "__main__":
    unittest.main(verbosity=2)
