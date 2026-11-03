"""Focused tests for the v1.2 unified analyzer adapter."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from clipforge_contracts import MediaSource
import unified_analyzer as analyzer


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
             patch("smart_duration.analyze_boundaries", return_value=[
                 {"start": 1, "end": 2, "text": "Local transcript."}
             ]), \
             patch("smart_reframe.shot_boundaries", return_value=[45.0]), \
             patch("gemini_highlights.process_ai", return_value={
                 "ranked_candidates": [
                     {"start": 10, "end": 25, "title": "A moment", "score": 80}
                 ]
             }) as process_ai:
            bundle = analyzer.analyze_source(
                self.media_path, self.root / "cache", provider=lambda *args: [],
            )
        self.assertEqual(len(bundle.transcript), 1)
        self.assertEqual(len(bundle.scenes), 2)
        self.assertEqual(len(bundle.events), 1)
        self.assertFalse(process_ai.call_args.kwargs["render"])
        self.assertFalse(process_ai.call_args.kwargs["context_aware"])
        self.assertEqual(
            process_ai.call_args.kwargs["boundary_spans"],
            [{"start": 1, "end": 2, "text": "Local transcript."}],
        )

    def test_failed_optional_stage_is_reported_without_losing_other_data(self):
        with patch.object(analyzer, "probe_source", return_value=self.media), \
             patch("smart_duration.analyze_boundaries", side_effect=RuntimeError("offline")), \
             patch("smart_reframe.shot_boundaries", return_value=[]), \
             patch("gemini_highlights.process_ai", return_value={
                 "ranked_candidates": [
                     {"start": 12, "end": 30, "title": "Still usable", "score": 72}
                 ]
             }):
            bundle = analyzer.analyze_source(
                self.media_path, self.root / "cache", provider=lambda *args: [],
            )
        self.assertEqual(len(bundle.events), 1)
        self.assertTrue(any("transcript" in warning.lower() for warning in bundle.warnings))


if __name__ == "__main__":
    unittest.main(verbosity=2)
