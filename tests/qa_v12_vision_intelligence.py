"""Quality, cache and fusion tests for the optional visual intelligence layer."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from clipforge.clipforge_contracts import (
    AnalysisBundle, EditorialEvent, MediaSource, SceneSpan, SegmentRole,
)
from clipforge.multimodal_fusion import fuse_visual_evidence
from clipforge.vision_cache import CachedVisionProvider
from clipforge.vision_provider import VisionFrame, VisionResult
from clipforge.vision_quality import filter_vision_frames


class FakeVisionProvider:
    name = "fake-vision"

    def __init__(self):
        self.calls = 0

    def analyze(self, source, *, duration_seconds, max_frames=12):
        self.calls += 1
        return VisionResult(
            provider=self.name,
            frames=(
                VisionFrame(10.0, b"frame-a"),
                VisionFrame(10.0, b"frame-a-duplicate"),
                VisionFrame(20.0, b"frame-b"),
                VisionFrame(999.0, b"outside"),
            ),
            metadata={"test": True},
        )


class VisionIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source_path = self.root / "source.mp4"
        self.source_path.write_bytes(b"fixture")
        self.source = MediaSource(
            "src", str(self.source_path), 60, 1920, 1080, 30, True
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_quality_filter_discards_duplicate_and_invalid_frames(self):
        frames = (
            VisionFrame(5, b"same"),
            VisionFrame(5, b"different"),
            VisionFrame(80, b"outside"),
            VisionFrame(float("nan"), b"bad-time"),
            VisionFrame(20, b"unique"),
        )
        report = filter_vision_frames(frames, duration_seconds=60, max_frames=8)
        self.assertEqual([f.timestamp_seconds for f in report.frames], [5, 20])
        self.assertEqual(report.duplicate_count, 1)
        self.assertEqual(report.rejected_count, 2)

    def test_fusion_attaches_visual_evidence_to_events_and_scenes(self):
        bundle = AnalysisBundle(
            "analysis", self.source,
            scenes=(
                SceneSpan("scene_1", 0, 30),
                SceneSpan("scene_2", 30, 60),
            ),
            events=(
                EditorialEvent(
                    "event_1", 5, 25, "Hook", "A hook", SegmentRole.HOOK,
                    .9, tags=("animation",), visual_summary="Animated opening",
                ),
                EditorialEvent(
                    "event_2", 35, 55, "Payoff", "A payoff", SegmentRole.PAYOFF,
                    .9, tags=("screen_recording",), visual_summary="UI demonstration",
                ),
            ),
        )
        result = VisionResult(
            "test",
            frames=(VisionFrame(10, b"frame-1"), VisionFrame(45, b"frame-2")),
        )
        fused = fuse_visual_evidence(bundle, result)
        self.assertEqual(fused.events[0].visual_evidence_seconds, (10.0,))
        self.assertEqual(fused.events[1].visual_evidence_seconds, (45.0,))
        self.assertIn("Animated opening", fused.scenes[0].visual_summary)
        self.assertIn("screen_recording", fused.scenes[1].visual_tags)

    def test_cache_avoids_reprocessing_same_source_revision(self):
        provider = FakeVisionProvider()
        cached = CachedVisionProvider(provider, self.root / "cache")
        first = cached.analyze(self.source_path, duration_seconds=60, max_frames=8)
        second = cached.analyze(self.source_path, duration_seconds=60, max_frames=8)
        self.assertEqual(provider.calls, 1)
        self.assertEqual(len(first.frames), len(second.frames))
        self.assertEqual(second.metadata["cache"], "hit")


if __name__ == "__main__":
    unittest.main(verbosity=2)
