"""Single-worker sequential scheduler with safe pause-after-current semantics."""
from __future__ import annotations
import threading
from typing import Callable
from .events import EventCallback,emit
from .manager import QueueManager
from .models import JobRecord
ProgressCallback=Callable[[str,float | None],None]
JobRunner=Callable[[JobRecord,ProgressCallback],None]

class QueueScheduler:
    def __init__(self,manager: QueueManager,runner: JobRunner,on_event: EventCallback | None=None):
        self.manager=manager; self.runner=runner; self.on_event=on_event or manager.on_event
        self._thread: threading.Thread | None=None; self._wake=threading.Event(); self._pause=threading.Event(); self._shutdown=threading.Event(); self._lock=threading.Lock(); self._current_job_id: str | None=None
    @property
    def is_running(self): return bool(self._thread and self._thread.is_alive())
    @property
    def current_job_id(self): return self._current_job_id
    def start(self):
        with self._lock:
            if self.is_running: self._wake.set(); return
            self._shutdown.clear(); self._pause.clear(); self._thread=threading.Thread(target=self._run,name="ClipForgeQueueWorker",daemon=True); self._thread.start(); self._wake.set()
    def notify_new_jobs(self): self._wake.set()
    def pause_after_current(self):
        self._pause.set(); emit(self.on_event,"queue_pausing",self._current_job_id,"Queue will pause after the active job finishes.")
    def resume(self):
        self._pause.clear(); self._wake.set(); emit(self.on_event,"queue_resumed",self._current_job_id,"Queue resumed.")
    def shutdown(self,wait: bool=True,timeout: float | None=None):
        self._shutdown.set(); self._wake.set(); thread=self._thread
        if wait and thread and thread.is_alive(): thread.join(timeout=timeout)
    def _progress(self,job_id: str) -> ProgressCallback:
        def callback(stage: str,progress: float | None=None): self.manager.update_progress(job_id,stage,progress)
        return callback
    def _run(self):
        emit(self.on_event,"queue_started",None,"Sequential production queue started.")
        while not self._shutdown.is_set():
            if self._pause.is_set(): self._wake.clear(); self._wake.wait(.5); continue
            job=self.manager.claim_next()
            if job is None: self._wake.clear(); self._wake.wait(.5); continue
            self._current_job_id=job.job_id; emit(self.on_event,"job_started",job.job_id,f"Started {job.source_name}")
            try: self.runner(job,self._progress(job.job_id))
            except Exception as exc: self.manager.fail(job.job_id,f"{type(exc).__name__}: {exc}")
            else: self.manager.complete(job.job_id)
            finally: self._current_job_id=None
        emit(self.on_event,"queue_stopped",None,"Queue scheduler stopped.")
