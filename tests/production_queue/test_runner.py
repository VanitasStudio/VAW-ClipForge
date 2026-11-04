from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from clipforge.production_queue.runner import run_production


class ProductionRunnerTests(unittest.TestCase):
    def test_offline_standalone_pipeline_adapter_reports_stages_and_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            source=root/"sample.mp4"
            source.write_bytes(b"placeholder")
            output=root/"exports"/"sample_job"
            stages=[]
            config={
                "ai":False,"standalone":True,"smart_compilation":False,
                "narrative_reconstruction":False,"count":1,"seconds":20,
                "resolution":"720p","layout":"fit","captions":False,
                "burn":False,"context_duration":False,"autoframe":False,
                "scenedetect":False,"caption_style":"karaoke",
            }
            selection={"clips":[{"start":1,"end":11,"title":"Test highlight"}],"transcript_spans":[]}
            outcome={"clips":[{"ok":True,"output":str(output/"clip_01.mp4"),
                "start":1,"duration":10,"title":"Test highlight"}]}
            with patch("clipforge.clip_engine.process",return_value=selection), \
                 patch("clipforge.smart_reframe.export_v04",return_value=outcome), \
                 patch("clipforge.title_hashtag_suggestions.write_suggestion_markdown",return_value=None):
                result=run_production(source,output,config,log=lambda _message:None,
                    progress=lambda stage,value:stages.append((stage,value)))
            self.assertIn("Standalone Highlights: 1/1 clips",result["successes"])
            self.assertEqual(result["output_directory"],str(output.resolve()))
            self.assertIn("Source validation",[stage for stage,_ in stages])
            self.assertIn("Standalone rendering",[stage for stage,_ in stages])
            self.assertIn("Finalizing production assets",[stage for stage,_ in stages])

    def test_story_composer_is_rejected_in_offline_mode(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/"sample.mp4"
            source.write_bytes(b"placeholder")
            with self.assertRaisesRegex(ValueError,"requires Gemini"):
                run_production(source,Path(temp)/"out",{
                    "ai":False,"standalone":False,"smart_compilation":True,
                    "narrative_reconstruction":False,
                },log=lambda _message:None)


if __name__=="__main__":
    unittest.main()
