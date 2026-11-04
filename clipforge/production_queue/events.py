"""Queue event callback helpers."""
from typing import Any, Callable
EventCallback = Callable[[dict[str, Any]], None]

def emit(callback: EventCallback | None, kind: str, job_id: str | None, message: str, **data: Any) -> None:
    if callback is None:
        return
    try:
        callback({"kind": kind, "job_id": job_id, "message": message, "data": data})
    except Exception:
        return
