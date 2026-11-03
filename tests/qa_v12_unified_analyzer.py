"""Focused tests for the v1.2 unified analyzer adapter."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from clipforge.clipforge_contracts import MediaSource
import clipforge.unified_analyzer as analyzer


class UnifiedAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.media_path = self.root / "source.mp4"
        self.media_path.write_bytes(b"test media")
        self.media = MediaSource(
            source_id="src_test", path=str(self.media_path),
            duration_seconds=90.0, width=1920, height=1080,
            fps=30.0, has_audio=True,
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_transcript_rows_become_contract_spans(self):
        bundle = analyzer.build_analysis_bundle(self.media, transcript_rows=[
            {"start": 1.0, "end": 2.5, "text": "A complete sentence."},
            {"start": 3.0, "end": 3.0, "text": "invalid"},
            {"start": 4.0, "end": 5.0, "text": ""},
            {"start": float("nan"), "end": 6.0, "text": "bad timestamp"},
        ])
        self.assertEqual(len(bundle.transcript), 1)
        self.assertEqual(bundle.transcript[0].text, "A complete sentence.")
        self.assertEqual(bundle.transcript[0].span_id, "utt_00001")

    def test_scene_cuts_form_contiguous_spans(self):
        bundle = analyzer.build_analysis_bundle(
            self.media, scene_cuts=[30.0, 60.0, 30.0, -1.0, 120.0, float("nan")]
        )
        self.assertEqual(
            [(x.start_seconds, x.end_seconds) for x in bundle.scenes],
            [(0.0, 30.0), (30.0, 60.0), (60.0, 90.0)],
        )

    def test_editorial_rows_are_sanitized_and_scored(self):
        bundle = analyzer.build_analysis_bundle(self.media, editorial_rows=[
            {"start": 10, "end": 28, "title": "Useful moment",
             "reason": "Clear payoff", "editorial_score": 86,
             "visual_type": "animation", "retention_risk": "none"},
            {"start": 40, "end": 35, "title": "Invalid"},
            {"start": 50, "end": float("inf"), "title": "Bad timestamp"},
        ])
        self.assertEqual(len(bundle.events), 1)
        self.assertEqual(bundle.events[0].confidence, 0.86)
        self.assertEqual(bundle.events[0].topic, "Useful moment")

    def test_bundle_ids_are_stable_for_same_source_revision(self):
        first = analyzer.build_analysis_bundle(self.media)
        second = analyzer.build_analysis_bundle(self.media)
        self.assertEqual(first.bundle_id, second.bundle_id)

    def test_analyze_source_reuses_existing_analyzers(self):
        with patch.object(analyzer, "probe_source", return_value=self.media), \
             patch("clipforge.smart_duration.analyze_boundaries", return_value=[
                 {"start": 1, "end": 2, "text": "Local transcript."}
             ]), \
             patch("clipforge.smart_reframe.shot_boundaries", return_value=[45.0]), \
             patch("clipforge.gemini_highlights.process_ai", return_value={
                 "ranked_candidates": [
                     {"start": 10, "end": 25, "title": "A moment", "score": 80},
                     {"start": 35, "end": 50, "title": "Second moment", "score": 76}
                 ]
             }) as process_ai:
            bundle = analyzer.analyze_source(
                self.media_path, self.root / "cache", provider=lambda *args: [],
                story_provider=lambda compact, key, model: {
                    "smart_compilation": {
                        "event_ids": ["event_0001", "event_0002"], "roles": {}, "requires": {}
                    },
                    "narrative_reconstruction": {
                        "event_ids": ["event_0001", "event_0002"], "roles": {}, "requires": {}
                    },
                },
            )
        self.assertEqual(bundle.composition_orders["smart_compilation"], ("event_0001", "event_0002"))
        self.assertEqual(len(bundle.transcript), 1)
        self.assertEqual(len(bundle.scenes), 2)
        self.assertEqual(len(bundle.events), 2)
        self.assertEqual(
            bundle.composition_orders["smart_compilation"],
            ("event_0001", "event_0002"),
        )
        self.assertFalse(process_ai.call_args.kwargs["render"])
        self.assertFalse(process_ai.call_args.kwargs["context_aware"])
        self.assertEqual(
            process_ai.call_args.kwargs["boundary_spans"],
            [{"start": 1, "end": 2, "text": "Local transcript."}],
        )

    def test_failed_optional_stage_is_reported_without_losing_other_data(self):
        with patch.object(analyzer, "probe_source", return_value=self.media), \
             patch("clipforge.smart_duration.analyze_boundaries", side_effect=RuntimeError("offline")), \
             patch("clipforge.smart_reframe.shot_boundaries", return_value=[]), \
             patch("clipforge.gemini_highlights.process_ai", return_value={
                 "ranked_candidates": [
                     {"start": 12, "end": 30, "title": "Still usable", "score": 72}
                 ]
             }):
            bundle = analyzer.analyze_source(
                self.media_path, self.root / "cache", provider=lambda *args: [],
            )
        self.assertEqual(len(bundle.events), 1)
        self.assertTrue(any("transcript" in warning.lower() for warning in bundle.warnings))

    def test_optional_vision_provider_fuses_frames_and_story_order(self):
        from clipforge.vision_provider import VisionFrame, VisionResult

        class FakeVision:
            name = "qa-vision"

            def analyze(self, source, *, duration_seconds, max_frames=12):
                return VisionResult(
                    provider=self.name,
                    frames=(
                        VisionFrame(12.0, b"vision-frame-a"),
                        VisionFrame(48.0, b"vision-frame-b"),
                    ),
                )

        with patch.object(analyzer, "probe_source", return_value=self.media), \
             patch("clipforge.smart_duration.analyze_boundaries", return_value=[
                 {"start": 1, "end": 2, "text": "Local transcript."}
             ]), \
             patch("clipforge.smart_reframe.shot_boundaries", return_value=[45.0]), \
             patch("clipforge.gemini_highlights.process_ai", return_value={
                 "ranked_candidates": [
                     {"start": 10, "end": 25, "title": "Opening", "score": 90,
                      "visual_notes": "A clear animated hook."},
                     {"start": 40, "end": 55, "title": "Payoff", "score": 88,
                      "visual_notes": "A useful screen demonstration."},
                 ]
             }) as process_ai:
            bundle = analyzer.analyze_source(
                self.media_path, self.root / "vision-cache-test",
                provider=lambda *args: [],
                vision_provider=FakeVision(),
                vision_enabled=True,
                story_provider=lambda compact, key, model: {
                    "smart_compilation": {
                        "event_ids": ["event_0002", "event_0001"],
                        "roles": {"event_0001": "hook", "event_0002": "payoff"},
                        "requires": {},
                    },
                    "narrative_reconstruction": {
                        "event_ids": ["event_0001", "event_0002"],
                        "roles": {}, "requires": {},
                    },
                },
                log=lambda _message: None,
            )
        self.assertEqual(len(process_ai.call_args.kwargs["vision_frames"]), 2)
        self.assertEqual(bundle.events[0].visual_evidence_seconds, (12.0,))
        self.assertEqual(bundle.events[1].visual_evidence_seconds, (48.0,))
        self.assertEqual(
            bundle.composition_orders["smart_compilation"],
            ("event_0002", "event_0001"),
        )
        self.assertIn("A clear animated hook.", bundle.scenes[0].visual_summary)


if __name__ == "__main__":
    unittest.main(verbosity=2)
