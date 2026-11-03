"""Video Vision MCP adapter tests; use a fake local MCP server, never the network."""
from __future__ import annotations

import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

import clipforge.video_vision_adapter as adapter


class VideoVisionAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.video = self.root / "source.mp4"
        self.video.write_bytes(b"local fixture")
        ok, encoded = cv2.imencode(".jpg", np.zeros((16, 16, 3), dtype=np.uint8))
        self.image_b64 = base64.b64encode(encoded.tobytes()).decode("ascii")
        self.server = self.root / "fake_mcp_server.py"
        self.server.write_text(
            "import sys,json,os,base64\n"
            f"IMAGE={self.image_b64!r}\n"
            "for line in sys.stdin:\n"
            " m=json.loads(line); method=m.get('method'); rid=m.get('id')\n"
            " if method=='exit': break\n"
            " if rid is None: continue\n"
            " if method=='initialize': result={'protocolVersion':'2024-11-05','capabilities':{},'serverInfo':{'name':'fake','version':'1'}}\n"
            " elif method=='tools/list': result={'tools':[{'name':'extract_frames','inputSchema':{'type':'object','properties':{'source':{'type':'string'},'mode':{'type':'string'},'timestamps':{'type':'array'},'max_width':{'type':'number'},'output_dir':{'type':'string'}}}}]}\n"
            " elif method=='tools/call':\n"
            "  args=m['params']['arguments'];\n"
            "  if args.get('mode')!='targeted' or len(args.get('timestamps',[]))!=4: result={'isError':True,'content':[{'type':'text','text':'expected four targeted timestamps'}]}\n"
            "  else:\n"
            "   os.makedirs(args['output_dir'],exist_ok=True); frame=os.path.join(args['output_dir'],'frame_0001.jpg'); open(frame,'wb').write(base64.b64decode(IMAGE)); result={'content':[{'type':'text','text':json.dumps([{'path':frame,'timestamp':'00:00:00','frame_number':1}])}]}\n"
            " elif method=='shutdown': result={}\n"
            " else: result={}\n"
            " print(json.dumps({'jsonrpc':'2.0','id':rid,'result':result}),flush=True)\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_analyze_video_calls_local_file_tool_and_returns_jpeg(self):
        with patch.object(adapter, "_server_command", return_value=[sys.executable, str(self.server)]):
            result = adapter.analyze_video(self.video, duration_seconds=200, max_frames=4)
        self.assertEqual(result.provider, "video-vision-mcp")
        self.assertEqual(len(result.frames), 1)
        self.assertEqual(result.frames[0].timestamp_seconds, 0.0)
        self.assertEqual(result.frames[0].mime_type, "image/jpeg")
        self.assertTrue(result.frames[0].image_bytes.startswith(b"\xff\xd8"))
        self.assertEqual(result.transcript_text, "")
        self.assertEqual(result.metadata["tool"], "extract_frames")

    def test_disabled_by_default(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(adapter.is_enabled())

    def test_frame_limits_are_enforced(self):
        with self.assertRaises(ValueError):
            adapter.analyze_video(self.video, duration_seconds=30, max_frames=0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
