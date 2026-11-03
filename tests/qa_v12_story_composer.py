"""Story Composer planning tests; no network or Gemini quota is used."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from clipforge_contracts import (
    AnalysisBundle, EditorialEvent, MediaSource, SegmentRole,
    CompositionStrategy, validate_edl,
)
from story_composer import build_composition, build_compositions


class StoryComposerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        path = Path(self.temp.name) / "source.mp4"
        path.write_bytes(b"test")
        self.source = MediaSource("src_test", str(path), 180, 1920, 1080, 30, True)
        self.events = (
            EditorialEvent("event_1", 0, 22, "Hook moment", "Opens the idea",
                           SegmentRole.HOOK, .95),
            EditorialEvent("event_2", 30, 55, "Context moment", "Explains the setup",
                           SegmentRole.CONTEXT, .88),
            EditorialEvent("event_3", 70, 95, "Payoff moment", "Resolves the idea",
                           SegmentRole.PAYOFF, .97),
            EditorialEvent("event_4", 110, 135, "Extra moment", "Adds supporting detail",
                           SegmentRole.SUPPORT, .70),
        )
        self.bundle = AnalysisBundle(
            bundle_id="analysis_test", source=self.source, events=self.events,
            composition_orders={
                "smart_compilation": ("event_3", "event_1", "event_4"),
                "narrative_reconstruction": ("event_1", "event_2", "event_3"),
            },
            event_roles={"event_1": "hook", "event_2": "context", "event_3": "payoff"},
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_builds_both_distinct_compositions(self):
        outputs = build_compositions(self.bundle, target_duration_seconds=60)
        self.assertEqual(set(outputs), {
            "smart_compilation", "narrative_reconstruction"
        })
        smart = outputs["smart_compilation"]
        narrative = outputs["narrative_reconstruction"]
        self.assertNotEqual(
            [s.event_ids[0] for s in smart.segments],
            [s.event_ids[0] for s in narrative.segments],
        )
        self.assertTrue(validate_edl(smart, self.source).valid)
        self.assertTrue(validate_edl(narrative, self.source).valid)

    def test_respects_narrative_dependencies(self):
        bundle = AnalysisBundle(
            bundle_id="analysis_deps", source=self.source, events=self.events,
            composition_orders={
                "narrative_reconstruction": ("event_3", "event_2", "event_1")
            },
            event_dependencies={"event_3": ("event_2",), "event_2": ("event_1",)},
        )
        edl = build_composition(bundle, CompositionStrategy.NARRATIVE_RECONSTRUCTION)
        ids = [segment.event_ids[0] for segment in edl.segments]
        self.assertLess(ids.index("event_1"), ids.index("event_2"))
        self.assertLess(ids.index("event_2"), ids.index("event_3"))

    def test_never_truncates_to_fit_180_seconds(self):
        # Complete source moments are retained; no event is shortened to hit the cap.
        long_events = (
            EditorialEvent("long_1", 0, 100, "Long 1", "Complete story", confidence=.9),
            EditorialEvent("long_2", 100, 180, "Long 2", "Complete story", confidence=.8),
        )
        bundle = AnalysisBundle("long", self.source, events=long_events)
        edl = build_composition(bundle, CompositionStrategy.SMART_COMPILATION)
        self.assertEqual(edl.duration_seconds, 180)
        self.assertEqual([s.source_out - s.source_in for s in edl.segments], [100, 80])

    def test_rejects_missing_narrative_prerequisite(self):
        bundle = AnalysisBundle(
            "missing_dependency", self.source, events=self.events[:2],
            event_dependencies={"event_2": ("event_not_present",)},
        )
        with self.assertRaisesRegex(ValueError, "unavailable prerequisite"):
            build_composition(bundle, CompositionStrategy.NARRATIVE_RECONSTRUCTION)

    def test_rejects_dependency_cycle(self):
        bundle = AnalysisBundle(
            "dependency_cycle", self.source, events=self.events[:2],
            event_dependencies={"event_1": ("event_2",), "event_2": ("event_1",)},
        )
        with self.assertRaisesRegex(ValueError, "cycle"):
            build_composition(bundle, CompositionStrategy.NARRATIVE_RECONSTRUCTION)

    def test_rejects_when_fewer_than_two_valid_moments(self):
        bundle = AnalysisBundle("one", self.source, events=(self.events[0],))
        with self.assertRaises(ValueError):
            build_composition(bundle, CompositionStrategy.SMART_COMPILATION)

    def test_rejects_overlapping_repetitive_moments(self):
        overlap = (
            EditorialEvent("a", 10, 40, "A", "First", confidence=.9),
            EditorialEvent("b", 12, 42, "B", "Mostly same source", confidence=.8),
        )
        bundle = AnalysisBundle("overlap", self.source, events=overlap)
        with self.assertRaises(ValueError):
            build_composition(bundle, CompositionStrategy.SMART_COMPILATION)

    def test_rejects_unknown_gemini_event_ids(self):
        bundle = AnalysisBundle(
            "unknown-order", self.source, events=self.events,
            composition_orders={"smart_compilation": ("event_1", "not-an-event")},
        )
        with self.assertRaisesRegex(ValueError, "unknown event IDs"):
            build_composition(bundle, CompositionStrategy.SMART_COMPILATION)

    def test_rejects_duplicate_gemini_event_ids(self):
        bundle = AnalysisBundle(
            "duplicate-order", self.source, events=self.events,
            composition_orders={"smart_compilation": ("event_1", "event_1")},
        )
        with self.assertRaisesRegex(ValueError, "duplicate event IDs"):
            build_composition(bundle, CompositionStrategy.SMART_COMPILATION)


if __name__ == "__main__":
    unittest.main(verbosity=2)
