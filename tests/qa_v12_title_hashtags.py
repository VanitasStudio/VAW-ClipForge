"""QA for per-export title and hashtag suggestions."""
import tempfile
import unittest
from pathlib import Path

from title_hashtag_suggestions import (
    OUTPUT_NAME,
    generate_suggestions,
    write_suggestion_markdown,
)


class TitleHashtagSuggestionTests(unittest.TestCase):
    def setUp(self):
        self.items = [
            {
                "output": "science_v04_01.mp4",
                "start": 10,
                "duration": 20,
                "title": "Why the Moon Looks Bigger",
                "reason": "A clear explanation of the horizon illusion.",
            },
            {
                "output": "science_v04_02.mp4",
                "start": 50,
                "duration": 15,
                "title": "How Rockets Reach Orbit",
                "reason": "A concise explanation of orbital velocity.",
            },
        ]
        self.transcript = [
            {"start": 11, "end": 16, "text": "The moon is not actually getting bigger."},
            {"start": 52, "end": 58, "text": "A rocket needs enough horizontal speed to stay in orbit."},
        ]

    def test_provider_suggestions_are_matched_to_each_clip(self):
        calls = []
        def provider(contexts, key, model):
            calls.extend(contexts)
            return {"clips": [
                {
                    "clip_id": contexts[0]["clip_id"],
                    "recommended_title": "The Moon Illusion Explained",
                    "title_options": ["The Moon Illusion Explained", "Why the Moon Seems Huge"],
                    "hashtags": ["#Moon", "#Science", "#OpticalIllusion"],
                    "angle": "A quick explanation of perspective.",
                },
                {
                    "clip_id": contexts[1]["clip_id"],
                    "recommended_title": "The Speed That Keeps Rockets in Orbit",
                    "title_options": ["The Speed That Keeps Rockets in Orbit"],
                    "hashtags": ["#RocketScience", "#Space", "#Physics"],
                    "angle": "Orbital velocity explained.",
                },
            ]}
        result, mode = generate_suggestions(self.items, self.transcript, provider=provider, allow_ai=True)
        self.assertEqual(mode, "Gemini")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["recommended_title"], "The Moon Illusion Explained")
        self.assertEqual(result[1]["recommended_title"], "The Speed That Keeps Rockets in Orbit")
        self.assertIn("moon", calls[0]["transcript_excerpt"].lower())
        self.assertIn("rocket", calls[1]["transcript_excerpt"].lower())

    def test_writes_one_markdown_file_for_all_clips(self):
        with tempfile.TemporaryDirectory() as temp:
            path = write_suggestion_markdown(
                temp, self.items, self.transcript,
                provider=lambda contexts, key, model: {"clips": []}, allow_ai=True,
            )
            self.assertEqual(path.name, OUTPUT_NAME)
            content = path.read_text(encoding="utf-8")
            self.assertIn("Source: local fallback", content)
            self.assertIn("science_v04_01.mp4", content)
            self.assertIn("science_v04_02.mp4", content)
            self.assertEqual(content.count("## Clip "), 2)
            self.assertIn("Recommended title", content)
            self.assertIn("Hashtags", content)

    def test_invalid_provider_response_falls_back_locally(self):
        result, mode = generate_suggestions(
            self.items, self.transcript,
            provider=lambda contexts, key, model: {"clips": "not-a-list"}, allow_ai=True,
        )
        self.assertEqual(mode, "local fallback")
        self.assertEqual(len(result), 2)
        self.assertTrue(result[0]["recommended_title"])
        self.assertTrue(result[0]["hashtags"])

    def test_cloud_suggestions_are_disabled_without_ai_opt_in(self):
        called = []
        def forbidden_provider(*args):
            called.append(True)
            return {"clips": []}
        result, mode = generate_suggestions(
            self.items, self.transcript, provider=forbidden_provider, allow_ai=False
        )
        self.assertEqual(mode, "local fallback")
        self.assertEqual(len(result), 2)
        self.assertEqual(called, [])

    def test_story_segments_sharing_one_mp4_keep_distinct_suggestion_ids(self):
        segments = [
            {"output": "story_composition.mp4", "start": 12, "duration": 18, "title": "The setup"},
            {"output": "story_composition.mp4", "start": 42, "duration": 21, "title": "The payoff"},
        ]
        captured = []
        def provider(contexts, key, model):
            captured.extend(contexts)
            return {"clips": [
                {"clip_id": contexts[0]["clip_id"], "recommended_title": "The Setup", "hashtags": ["#Story"]},
                {"clip_id": contexts[1]["clip_id"], "recommended_title": "The Payoff", "hashtags": ["#Payoff"]},
            ]}
        result, _ = generate_suggestions(segments, provider=provider, allow_ai=True)
        self.assertNotEqual(captured[0]["clip_id"], captured[1]["clip_id"])
        self.assertEqual([item["recommended_title"] for item in result], ["The Setup", "The Payoff"])

    def test_all_exported_clips_are_included_across_gemini_batches(self):
        items = [
            {"output": f"clip_{index:02}.mp4", "start": index * 20, "duration": 12, "title": f"Topic {index}"}
            for index in range(13)
        ]
        calls = []
        def provider(contexts, key, model):
            calls.append(len(contexts))
            return {"clips": [
                {"clip_id": item["clip_id"], "recommended_title": f"Title {index}", "hashtags": ["#Topic"]}
                for index, item in enumerate(contexts)
            ]}
        result, mode = generate_suggestions(items, provider=provider, allow_ai=True)
        self.assertEqual(calls, [12, 1])
        self.assertEqual(len(result), 13)
        self.assertEqual(mode, "Gemini")

    def test_unrelated_transcript_is_not_included(self):
        result, _ = generate_suggestions(
            self.items, [{"start": 500, "end": 510, "text": "SECRET unrelated transcript"}],
            provider=lambda contexts, key, model: {"clips": []},
        )
        self.assertNotIn("SECRET", result[0]["transcript_excerpt"])


if __name__ == "__main__":
    unittest.main()
