"""Optional stdio MCP adapter for @oamaestro/video-vision-mcp.

The server is launched only when explicitly enabled. Source media stays local;
the adapter invokes only bounded frame extraction. It does not request transcripts
or invoke the MCP project's cloud/AI analysis paths.
"""
from __future__ import annotations

import json
import math
import os
import queue
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from clipforge.vision_provider import VisionFrame, VisionResult

PROVIDER_NAME = "video-vision-mcp"
MAX_FRAME_BYTES = 1_800_000
MAX_TOTAL_BYTES = 12_000_000
PROTOCOL_VERSION = "2024-11-05"


class VisionProviderError(RuntimeError):
    pass


def is_enabled() -> bool:
    return os.getenv("CLIPFORGE_VIDEO_VISION_ENABLED", "0").strip().lower() in {
        "1", "true", "yes", "on"
    }


def _server_command() -> list[str]:
    configured = os.getenv("CLIPFORGE_VIDEO_VISION_MCP_PATH", "").strip()
    if configured:
        root = Path(configured).expanduser().resolve()
    else:
        local_app_data = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData/Local"))
        root = local_app_data / "VanitasStudio" / "ClipForge" / "video-vision-mcp"
    entry = root if root.is_file() else root / "dist" / "index.js"
    if not entry.is_file():
        raise VisionProviderError(
            "Video Vision MCP is not installed. Run setup_video_vision_mcp.ps1, "
            "or set CLIPFORGE_VIDEO_VISION_MCP_PATH to its built dist/index.js or repository folder."
        )
    node = shutil.which("node")
    if not node:
        raise VisionProviderError("Node.js was not found. Install Node.js 18 or newer.")
    return [node, str(entry)]


class _MCPStdioClient:
    def __init__(self, command: list[str], *, timeout: float = 180.0):
        self.command = command
        self.timeout = timeout
        self.process: subprocess.Popen | None = None
        self.messages: queue.Queue = queue.Queue()
        self.reader: threading.Thread | None = None
        self.next_id = 1

    def start(self) -> None:
        try:
            self.process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        except OSError as exc:
            raise VisionProviderError(f"Could not start Video Vision MCP: {exc}") from None
        self.reader = threading.Thread(target=self._read_stdout, daemon=True)
        self.reader.start()
        self._request("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "vaw-clipforge", "version": "1.2.0"},
        })
        self._notify("notifications/initialized", {})

    def _read_stdout(self) -> None:
        assert self.process and self.process.stdout
        for line in self.process.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                self.messages.put(json.loads(line))
            except ValueError:
                self.messages.put({"_protocol_error": "Server wrote non-JSON data to stdout."})
        self.messages.put({"_process_exit": self.process.poll() if self.process else None})

    def _notify(self, method: str, params: dict) -> None:
        if not self.process or not self.process.stdin:
            raise VisionProviderError("Video Vision MCP is not running.")
        payload = {"jsonrpc": "2.0", "method": method, "params": params}
        self.process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
        self.process.stdin.flush()

    def _request(self, method: str, params: dict) -> dict:
        if not self.process or not self.process.stdin:
            raise VisionProviderError("Video Vision MCP is not running.")
        request_id = self.next_id
        self.next_id += 1
        payload = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        self.process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
        self.process.stdin.flush()
        deadline = time.monotonic() + self.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise VisionProviderError(f"Video Vision MCP timed out during {method}.")
            try:
                message = self.messages.get(timeout=min(remaining, 2.0))
            except queue.Empty:
                if self.process.poll() is not None:
                    raise VisionProviderError("Video Vision MCP exited unexpectedly.")
                continue
            if "_protocol_error" in message:
                raise VisionProviderError(message["_protocol_error"])
            if "_process_exit" in message:
                raise VisionProviderError("Video Vision MCP exited before responding.")
            if message.get("id") != request_id:
                continue
            if "error" in message:
                error = message["error"]
                raise VisionProviderError(str(error.get("message", "MCP request failed"))[:300])
            result = message.get("result")
            if not isinstance(result, dict):
                raise VisionProviderError(f"Video Vision MCP returned an invalid {method} response.")
            return result

    def list_tools(self) -> list[dict]:
        result = self._request("tools/list", {})
        tools = result.get("tools", [])
        return tools if isinstance(tools, list) else []

    def call_tool(self, name: str, arguments: dict) -> dict:
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            text = " ".join(
                str(item.get("text", "")) for item in result.get("content", [])
                if isinstance(item, dict)
            )
            raise VisionProviderError(text[:400] or "Video Vision MCP analysis failed.")
        return result

    def close(self) -> None:
        process = self.process
        if not process:
            return
        try:
            if process.poll() is None and process.stdin:
                try:
                    self._request("shutdown", {})
                    self._notify("exit", {})
                except Exception:
                    pass
                process.stdin.close()
                process.wait(timeout=4)
        except Exception:
            try:
                process.terminate()
                process.wait(timeout=3)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
        try:
            if process.stdout:
                process.stdout.close()
        except Exception:
            pass
        self.process = None



def _compress_image(data: bytes, mime_type: str = "image/jpeg") -> bytes:
    if mime_type.lower() in {"image/jpeg", "image/jpg"} and len(data) <= MAX_FRAME_BYTES:
        return data
    try:
        import cv2
        import numpy as np
        image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            return b""
        height, width = image.shape[:2]
        scale = min(1.0, 1280.0 / max(width, height))
        if scale < 1.0:
            image = cv2.resize(image, (int(width * scale), int(height * scale)))
        for quality in (82, 72, 62, 52):
            ok, encoded = cv2.imencode(
                ".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality]
            )
            if ok and len(encoded) <= MAX_FRAME_BYTES:
                return encoded.tobytes()
    except Exception:
        return b""
    return b""


def analyze_video(source: str | Path, *, duration_seconds: float,
                  max_frames: int = 12, timeout: float = 240.0) -> VisionResult:
    """Extract bounded, evenly distributed local frames through Video Vision MCP."""
    path = Path(source).resolve()
    if not path.is_file():
        raise VisionProviderError("Video Vision MCP requires an existing local video file.")
    if not math.isfinite(float(duration_seconds)) or float(duration_seconds) <= 0:
        raise ValueError("duration_seconds must be positive and finite.")
    if not 1 <= int(max_frames) <= 24:
        raise ValueError("max_frames must be between 1 and 24.")
    client = _MCPStdioClient(_server_command(), timeout=timeout)
    with tempfile.TemporaryDirectory(prefix="vaw-clipforge-vision-") as temp_dir:
        output_dir = Path(temp_dir).resolve()
        try:
            client.start()
            tools = client.list_tools()
            tool = next((item for item in tools if item.get("name") == "extract_frames"), None)
            if not tool:
                raise VisionProviderError("Installed Video Vision MCP does not expose extract_frames.")
            schema = tool.get("inputSchema", {})
            properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
            if "source" not in properties or "mode" not in properties:
                raise VisionProviderError("Video Vision MCP extract_frames schema is incompatible.")
            timestamps = (
                [float(duration_seconds) / 2.0]
                if int(max_frames) == 1
                else [
                    max(0.0, (float(duration_seconds) - min(0.5, float(duration_seconds) * 0.02))
                        * index / (int(max_frames) - 1))
                    for index in range(int(max_frames))
                ]
            )
            arguments: dict[str, Any] = {
                "source": str(path),
                "mode": "targeted",
                "timestamps": [f"{value:.3f}" for value in timestamps],
            }
            # Targeted mode receives an explicit bounded timestamp list.
            optional = {
                "max_width": 768,
                "output_dir": str(output_dir),
            }
            arguments.update({key: value for key, value in optional.items() if key in properties})
            result = client.call_tool("extract_frames", arguments)
            text = "\n".join(
                str(item.get("text", "")) for item in result.get("content", [])
                if isinstance(item, dict) and item.get("type") == "text"
            )
            try:
                records = json.loads(text)
            except (ValueError, TypeError):
                raise VisionProviderError(("Video Vision MCP returned an invalid frame manifest: " + text)[:400]) from None
            if not isinstance(records, list):
                raise VisionProviderError("Video Vision MCP frame manifest must be a list.")

            frames = []
            total_bytes = 0
            if len(records) > int(max_frames):
                if int(max_frames) == 1:
                    records = [records[len(records) // 2]]
                else:
                    chosen = [
                        round(index * (len(records) - 1) / (int(max_frames) - 1))
                        for index in range(int(max_frames))
                    ]
                    records = [records[index] for index in chosen]
            for index, record in enumerate(records):
                if not isinstance(record, dict) or not record.get("path"):
                    continue
                candidate = Path(str(record["path"])).resolve()
                try:
                    candidate.relative_to(output_dir)
                except ValueError:
                    raise VisionProviderError("Video Vision MCP returned a frame outside its assigned temporary directory.")
                if not candidate.is_file():
                    continue
                try:
                    raw = candidate.read_bytes()
                except OSError:
                    continue
                image = _compress_image(raw, "image/jpeg")
                if not image or total_bytes + len(image) > MAX_TOTAL_BYTES:
                    continue
                record_index = max(0, int(record.get("frame_number", index + 1)) - 1)
                timestamp = timestamps[min(record_index, len(timestamps) - 1)]
                timestamp = max(0.0, min(float(duration_seconds), float(timestamp)))
                frames.append(VisionFrame(
                    timestamp_seconds=timestamp,
                    image_bytes=image,
                    mime_type="image/jpeg",
                    source=PROVIDER_NAME,
                ))
                total_bytes += len(image)

            warnings = ()
            if not frames:
                warnings = ("Video Vision MCP returned no usable key frames; ClipForge will use its built-in frame sampler.",)
            return VisionResult(
                provider=PROVIDER_NAME,
                frames=tuple(frames),
                transcript_text="",
                metadata={
                    "tool": "extract_frames",
                    "mode": "targeted",
                    "frame_count": len(frames),
                    "backend": "local bounded targeted frame extraction; no transcript or cloud model invoked",
                },
                warnings=warnings,
            )
        finally:
            client.close()


class VideoVisionMCPProvider:
    name = PROVIDER_NAME

    def analyze(self, source: str | Path, *, duration_seconds: float,
                max_frames: int = 12) -> VisionResult:
        return analyze_video(source, duration_seconds=duration_seconds, max_frames=max_frames)
