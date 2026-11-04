"""Typed data contracts for production queue jobs."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

class JobStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass(frozen=True)
class JobRecord:
    job_id: str
    source_path: str
    source_name: str
    status: JobStatus
    preset_id: str
    config_snapshot: dict[str, Any]
    output_directory: str
    current_stage: str | None = None
    progress: float = 0.0
    created_at: str = field(default_factory=utc_now)
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None
    retry_count: int = 0

    @classmethod
    def create(cls, source_path: str | Path, preset_id: str, config_snapshot: dict[str, Any], output_root: str | Path) -> "JobRecord":
        source = Path(source_path).expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(f"Source video does not exist: {source}")
        from clipforge.clip_engine import EXTS
        if source.suffix.lower() not in EXTS:
            raise ValueError(f"Unsupported source video format: {source.suffix}")
        if not preset_id.strip():
            raise ValueError("A production preset ID is required.")
        job_id = str(uuid4())
        output = Path(output_root).expanduser().resolve() / f"{source.stem}_{job_id[:8]}"
        snapshot = json.loads(json.dumps(config_snapshot, ensure_ascii=False))
        return cls(job_id, str(source), source.name, JobStatus.QUEUED, preset_id, snapshot, str(output))

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["status"] = self.status.value
        return result

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "JobRecord":
        values = dict(payload)
        values["status"] = JobStatus(values["status"])
        return cls(**values)

@dataclass(frozen=True)
class QueueEvent:
    kind: str
    job_id: str | None
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
