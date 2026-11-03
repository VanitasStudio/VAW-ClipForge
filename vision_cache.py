"""Content-addressed local cache for optional vision-provider results."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from vision_provider import VisionFrame, VisionResult


def default_vision_cache_dir() -> Path:
    base = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData/Local"))
    return base / "VanitasStudio" / "ClipForge" / "vision-cache"


class CachedVisionProvider:
    def __init__(
        self,
        provider,
        cache_dir: str | Path | None = None,
        *,
        max_cache_bytes: int = 1_000_000_000,
    ):
        self.provider = provider
        self.cache_dir = Path(cache_dir or default_vision_cache_dir()).resolve()
        self.max_cache_bytes = max(50_000_000, int(max_cache_bytes))
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key(self, source: str | Path, max_frames: int) -> str:
        path = Path(source).resolve()
        stat = path.stat()
        provider_name = getattr(self.provider, "name", self.provider.__class__.__name__)
        payload = f"{path}|{stat.st_size}|{stat.st_mtime_ns}|{provider_name}|{max_frames}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _load(self, key: str) -> VisionResult | None:
        manifest_path = self.cache_dir / f"{key}.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            frames = []
            for item in manifest.get("frames", []):
                frame_path = (self.cache_dir / item["file"]).resolve()
                frame_path.relative_to(self.cache_dir)
                data = frame_path.read_bytes()
                if data:
                    frames.append(VisionFrame(
                        timestamp_seconds=float(item["timestamp_seconds"]),
                        image_bytes=data,
                        mime_type=str(item.get("mime_type", "image/jpeg")),
                        source=str(manifest.get("provider", getattr(self.provider, "name", self.provider.__class__.__name__))),
                    ))
            if not frames:
                return None
            os.utime(manifest_path, None)
            return VisionResult(
                provider=str(manifest.get("provider", getattr(self.provider, "name", self.provider.__class__.__name__))),
                frames=tuple(frames),
                transcript_text="",
                metadata={**manifest.get("metadata", {}), "cache": "hit"},
                warnings=tuple(manifest.get("warnings", [])),
            )
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            return None

    def analyze(self, source: str | Path, *, duration_seconds: float,
                max_frames: int = 12) -> VisionResult:
        key = self._key(source, max_frames)
        cached = self._load(key)
        if cached is not None:
            return cached
        result = self.provider.analyze(
            source, duration_seconds=duration_seconds, max_frames=max_frames
        )
        if not result.frames:
            return result
        frame_records = []
        for index, frame in enumerate(result.frames):
            filename = f"{key}_{index:02d}.jpg"
            target = self.cache_dir / filename
            temporary = self.cache_dir / f"{filename}.tmp"
            temporary.write_bytes(frame.image_bytes)
            os.replace(temporary, target)
            frame_records.append({
                "file": filename,
                "timestamp_seconds": frame.timestamp_seconds,
                "mime_type": frame.mime_type,
            })
        manifest = {
            "provider": result.provider,
            "frames": frame_records,
            "metadata": result.metadata,
            "warnings": list(result.warnings),
        }
        temporary_manifest = self.cache_dir / f"{key}.json.tmp"
        temporary_manifest.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary_manifest, self.cache_dir / f"{key}.json")
        self._prune_cache()
        return result

    def _prune_cache(self) -> None:
        manifests = sorted(
            self.cache_dir.glob("*.json"),
            key=lambda item: item.stat().st_mtime,
        )
        entries = []
        total = 0
        for manifest_path in manifests:
            files = [manifest_path]
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                for item in manifest.get("frames", []):
                    frame_path = (self.cache_dir / item["file"]).resolve()
                    frame_path.relative_to(self.cache_dir)
                    if frame_path.is_file():
                        files.append(frame_path)
            except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
                continue
            size = sum(item.stat().st_size for item in files if item.is_file())
            total += size
            entries.append((manifest_path, files, size))
        for manifest_path, files, size in entries:
            if total <= self.max_cache_bytes:
                break
            for item in files:
                try:
                    item.unlink(missing_ok=True)
                except OSError:
                    pass
            total -= size
