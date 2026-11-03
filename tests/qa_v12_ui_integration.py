"""Static acceptance tests for the v1.2 desktop production and review UI."""
from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class V12UIIntegrationTests(unittest.TestCase):
    def test_all_three_outputs_default_enabled(self):
        source = (ROOT / "clipforge_gui.py").read_text(encoding="utf-8-sig")
        tree = ast.parse(source)
        assignments = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Attribute) and target.attr in {
                "standalone_output", "smart_compilation_output", "narrative_output"
            } for target in node.targets)
        ]
        values = {}
        for node in assignments:
            target = next(
                target for target in node.targets
                if isinstance(target, ast.Attribute) and target.attr in {
                    "standalone_output", "smart_compilation_output", "narrative_output"
                }
            )
            if isinstance(node.value, ast.Call):
                keyword = next((item.value for item in node.value.keywords if item.arg == "value"), None)
                if keyword is not None:
                    values[target.attr] = ast.literal_eval(keyword)
        self.assertEqual(values, {
            "standalone_output": True,
            "smart_compilation_output": True,
            "narrative_output": True,
        })

    def test_optional_vision_is_disabled_by_default(self):
        source = (ROOT / "clipforge_gui.py").read_text(encoding="utf-8-sig")
        self.assertIn("self.video_vision=tk.BooleanVar(value=False)", source)
        self.assertIn("Extra local frame sampling (Video Vision MCP)", source)

    def test_story_outputs_are_rendered_by_the_real_edl_renderer(self):
        source = (ROOT / "clipforge_gui.py").read_text(encoding="utf-8-sig")
        self.assertIn("build_composition(", source)
        self.assertIn("render_composition(", source)
        self.assertIn("request_story_compositions(", source)

    def test_review_studio_has_timeline_preview_captions_and_transitions(self):
        source = (ROOT / "composition_review.py").read_text(encoding="utf-8-sig")
        for required in (
            "def _draw_timeline", "def _update_preview", "def _apply_caption",
            "def _apply_transition_value", "def _render",
        ):
            self.assertIn(required, source)

    def test_main_review_action_prefers_composition_edl(self):
        source = (ROOT / "clipforge_gui.py").read_text(encoding="utf-8-sig")
        self.assertIn('folder.glob("*.edl.json")', source)
        self.assertIn('ROOT/"composition_review.py"', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
