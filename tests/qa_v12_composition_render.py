"""Real FFmpeg composition render smoke test using a synthetic local fixture."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from clipforge.clipforge_contracts import (
    AnalysisBundle, CaptionPlan, EditorialEvent, SegmentRole, TranscriptSpan,
    CompositionStrategy, RenderSettings, TransitionKind, TransitionSpec,
)
from clipforge.composition_renderer import render_composition
from clipforge.composition_review import load_bundle, load_edl
from clipforge.story_composer import build_composition
from clipforge.unified_analyzer import probe_source
from clipforge.clip_engine import probe_duration


ROOT = Path(__file__).resolve().parents[1]


class CompositionRenderTests(unittest.TestCase):
    def test_renders_concat_sidecars_and_review_roundtrip(self):
        source_path = ROOT / "samples" / "synthetic-demo.mp4"
        if not source_path.is_file():
            self.skipTest("Synthetic source fixture is unavailable.")
        source = probe_source(source_path)
        if source.duration_seconds < 30:
            self.skipTest("Synthetic source fixture is too short.")
        bundle = AnalysisBundle(
            bundle_id="render-smoke",
            source=source,
            transcript=(
                TranscriptSpan("t1", 1, 6, "This is the opening hook."),
                TranscriptSpan("t2", 20, 25, "Here is the final payoff."),
            ),
            events=(
                EditorialEvent("e1", 1, 14, "Opening", "A complete opening hook.",
                               SegmentRole.HOOK, .95, visual_summary="Opening visual"),
                EditorialEvent("e2", 20, 33, "Payoff", "A complete final payoff.",
                               SegmentRole.PAYOFF, .90, visual_summary="Payoff visual"),
            ),
        )
        edl = build_composition(
            bundle, CompositionStrategy.NARRATIVE_RECONSTRUCTION,
            target_duration_seconds=30,
        )
        from dataclasses import replace
        edl = replace(
            edl,
            captions=CaptionPlan(enabled=True, preset_id="minimal", burn_in=True, export_srt=True),
            render=RenderSettings(width=720, height=1280, fps=30),
        )
        with tempfile.TemporaryDirectory(prefix="clipforge-composition-qa-") as temp:
            output = Path(temp) / "story.mp4"
            manifest = render_composition(
                bundle, edl, output,
                layout="fit", auto_reframe=False, scene_detection=False,
                resolution="720p", log=lambda _message: None,
            )
            self.assertTrue(Path(manifest["output"]).is_file())
            self.assertTrue(output.with_suffix(".srt").is_file())
            self.assertTrue(output.with_suffix(".ass").is_file())
            self.assertTrue(output.with_suffix(".edl.json").is_file())
            self.assertTrue(output.with_suffix(".analysis.json").is_file())
            self.assertTrue(output.with_suffix(".composition.json").is_file())
            duration = probe_duration(output)
            self.assertGreaterEqual(duration, 25)
            self.assertLessEqual(duration, 27)
            loaded_bundle = load_bundle(output.with_suffix(".analysis.json"))
            loaded_edl = load_edl(output.with_suffix(".edl.json"))
            self.assertEqual(loaded_bundle.source.source_id, source.source_id)
            self.assertEqual(len(loaded_edl.segments), 2)
            self.assertEqual(loaded_edl.strategy, CompositionStrategy.NARRATIVE_RECONSTRUCTION)

            dissolve_edl = replace(
                edl,
                transitions=(TransitionSpec(
                    edl.segments[0].segment_id,
                    edl.segments[1].segment_id,
                    TransitionKind.CROSS_DISSOLVE,
                    0.25,
                ),),
                captions=CaptionPlan(enabled=False),
            )
            dissolve_output = Path(temp) / "story_dissolve.mp4"
            dissolve_manifest = render_composition(
                bundle, dissolve_edl, dissolve_output,
                layout="fit", auto_reframe=False, scene_detection=False,
                resolution="720p", log=lambda _message: None,
            )
            self.assertTrue(Path(dissolve_manifest["output"]).is_file())
            dissolve_duration = probe_duration(dissolve_output)
            self.assertGreaterEqual(dissolve_duration, 25)
            self.assertLessEqual(dissolve_duration, 27)


if __name__ == "__main__":
    unittest.main(verbosity=2)
