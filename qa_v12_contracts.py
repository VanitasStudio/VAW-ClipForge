import unittest

from clipforge_contracts import (
    AudioContinuity, CompositionSegment, CompositionStrategy, EditDecisionList,
    MediaSource, SegmentRole, TransitionKind, TransitionSpec, dumps_contract,
    validate_edl,
)


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.source = MediaSource("source-1", "sample.mp4", 240.0, 1920, 1080, 30.0)

    def make_edl(self):
        segments = (
            CompositionSegment("s1", "source-1", 10.0, 18.0, 0.0, SegmentRole.HOOK),
            CompositionSegment("s2", "source-1", 42.0, 54.0, 8.0, SegmentRole.CONTEXT),
        )
        return EditDecisionList(
            "edl-1", "source-1", "composition-1",
            CompositionStrategy.SMART_COMPILATION, "Test composition", segments,
            (TransitionSpec("s1", "s2", TransitionKind.HARD_CUT),),
            target_duration_seconds=20.0,
        )

    def test_valid_edl(self):
        report = validate_edl(self.make_edl(), self.source)
        self.assertTrue(report.valid, report.issues)

    def test_source_boundary_is_checked(self):
        edl = self.make_edl()
        bad = CompositionSegment("s2", "source-1", 230.0, 250.0, 8.0)
        report = validate_edl(EditDecisionList(
            edl.edl_id, edl.source_id, edl.composition_id, edl.strategy,
            edl.title, (edl.segments[0], bad),
        ), self.source)
        self.assertFalse(report.valid)
        self.assertIn("source_range_exceeded", {issue.code for issue in report.issues})

    def test_json_contract_serialization(self):
        payload = dumps_contract(self.make_edl())
        self.assertIn('"smart_compilation"', payload)
        self.assertIn('"source_in": 10.0', payload)

    def test_invalid_media_metadata_rejected(self):
        with self.assertRaises(ValueError):
            MediaSource("bad", "sample.mp4", 0, 1920, 1080, 30)

    def test_transition_must_connect_adjacent_segments(self):
        edl = self.make_edl()
        invalid = TransitionSpec("s2", "s1", TransitionKind.CROSS_DISSOLVE, 0.3)
        report = validate_edl(EditDecisionList(
            edl.edl_id, edl.source_id, edl.composition_id, edl.strategy,
            edl.title, edl.segments, (invalid,),
        ), self.source)
        self.assertFalse(report.valid)
        self.assertIn("invalid_transition_pair", {issue.code for issue in report.issues})


if __name__ == "__main__":
    unittest.main(verbosity=2)
