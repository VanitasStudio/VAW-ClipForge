"""Queue operations and immutable effective configuration snapshots."""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
from typing import Any, Iterable
from .events import EventCallback, emit
from .models import JobRecord, JobStatus, utc_now
from .store import QueueStore

class QueueManager:
    def __init__(self,store: QueueStore,output_root: str | Path,on_event: EventCallback | None=None):
        self.store=store; self.output_root=Path(output_root).expanduser().resolve(); self.output_root.mkdir(parents=True,exist_ok=True); self.on_event=on_event
        self.store.recover_interrupted()

    def add_sources(self,source_paths: Iterable[str | Path],preset_id: str,base_config: dict[str,Any],overrides: dict[str,dict[str,Any]] | None=None) -> list[JobRecord]:
        overrides=overrides or {}
        prepared=[]
        for source_path in source_paths:
            source=Path(source_path).expanduser().resolve()
            config=dict(base_config); config.update(overrides.get(str(source),{}))
            prepared.append(JobRecord.create(source,preset_id,config,self.output_root))
        added=self.store.add_many(prepared)
        for job in added:
            emit(self.on_event,"job_queued",job.job_id,f"Queued {job.source_name}",source_path=job.source_path,output_directory=job.output_directory)
        return added

    def list_jobs(self): return self.store.list_jobs()
    def remove_pending(self,job_id: str):
        self.store.remove(job_id); emit(self.on_event,"job_removed",job_id,"Pending job removed.")

    def update_progress(self,job_id: str,stage: str,progress: float | None=None) -> JobRecord:
        job=self.store.get(job_id)
        if job is None: raise KeyError(job_id)
        if job.status != JobStatus.PROCESSING: raise ValueError("Progress can only be updated for a processing job.")
        value=job.progress if progress is None else max(0.0,min(100.0,float(progress)))
        updated=replace(job,current_stage=stage,progress=value); self.store.update(updated)
        emit(self.on_event,"job_progress",job_id,stage,stage=stage,progress=value); return updated

    def complete(self,job_id: str) -> JobRecord:
        job=self._require_processing(job_id); updated=replace(job,status=JobStatus.COMPLETED,current_stage="completed",progress=100.0,completed_at=utc_now(),error=None)
        self.store.update(updated); emit(self.on_event,"job_completed",job_id,f"Completed {job.source_name}"); return updated

    def fail(self,job_id: str,error: str) -> JobRecord:
        job=self._require_processing(job_id); updated=replace(job,status=JobStatus.FAILED,completed_at=utc_now(),error=str(error)[:2000])
        self.store.update(updated); emit(self.on_event,"job_failed",job_id,updated.error or "Job failed."); return updated

    def update_config(self,job_id: str,overrides: dict[str,Any]) -> JobRecord:
        job=self.store.get(job_id)
        if job is None: raise KeyError(job_id)
        if job.status != JobStatus.QUEUED: raise ValueError("Only queued jobs can be reconfigured.")
        snapshot=dict(job.config_snapshot); snapshot.update(overrides)
        # JSON round-trip validates serializability and detaches nested mutable values.
        import json
        snapshot=json.loads(json.dumps(snapshot,ensure_ascii=False))
        updated=replace(job,config_snapshot=snapshot)
        self.store.update(updated)
        emit(self.on_event,"job_config_updated",job_id,"Queued job configuration updated.")
        return updated

    def retry(self,job_id: str) -> JobRecord:
        job=self.store.get(job_id)
        if job is None: raise KeyError(job_id)
        if job.status not in {JobStatus.FAILED,JobStatus.CANCELLED}: raise ValueError("Only failed or cancelled jobs can be retried.")
        updated=replace(job,status=JobStatus.QUEUED,current_stage=None,progress=0.0,started_at=None,completed_at=None,error=None,retry_count=job.retry_count+1)
        self.store.update(updated); emit(self.on_event,"job_retried",job_id,f"Retry queued for {job.source_name}",retry_count=updated.retry_count); return updated

    def claim_next(self): return self.store.claim_next()
    def _require_processing(self,job_id: str) -> JobRecord:
        job=self.store.get(job_id)
        if job is None: raise KeyError(job_id)
        if job.status != JobStatus.PROCESSING: raise ValueError(f"Job {job_id} is not processing.")
        return job
