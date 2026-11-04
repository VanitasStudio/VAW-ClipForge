"""SQLite persistence with transactional queue claiming and crash recovery."""
from __future__ import annotations
import json, sqlite3, threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from .models import JobRecord, JobStatus, utc_now

class QueueStore:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path).expanduser().resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self):
        db = sqlite3.connect(str(self.database_path), timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=30000")
        return db

    @contextmanager
    def _session(self):
        db = self._connect()
        try:
            with db:
                yield db
        finally:
            db.close()

    def _initialize(self):
        with self._lock, self._session() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS jobs(job_id TEXT PRIMARY KEY,status TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,payload_json TEXT NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON jobs(status,created_at)")
            db.execute("CREATE TABLE IF NOT EXISTS queue_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")

    def add(self, job: JobRecord) -> JobRecord:
        with self._lock, self._session() as db:
            db.execute("INSERT INTO jobs VALUES(?,?,?,?,?)", (job.job_id,job.status.value,job.created_at,utc_now(),json.dumps(job.to_dict(),ensure_ascii=False)))
        return job

    def add_many(self, jobs: list[JobRecord]) -> list[JobRecord]:
        rows=[(job.job_id,job.status.value,job.created_at,utc_now(),json.dumps(job.to_dict(),ensure_ascii=False)) for job in jobs]
        with self._lock,self._session() as db:
            db.executemany("INSERT INTO jobs VALUES(?,?,?,?,?)",rows)
        return jobs

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock, self._session() as db:
            row=db.execute("SELECT payload_json FROM jobs WHERE job_id=?",(job_id,)).fetchone()
        return JobRecord.from_dict(json.loads(row["payload_json"])) if row else None

    def list_jobs(self) -> list[JobRecord]:
        with self._lock, self._session() as db:
            rows=db.execute("SELECT payload_json FROM jobs ORDER BY created_at,rowid").fetchall()
        return [JobRecord.from_dict(json.loads(row["payload_json"])) for row in rows]

    def update(self, job: JobRecord) -> JobRecord:
        with self._lock, self._session() as db:
            cur=db.execute("UPDATE jobs SET status=?,updated_at=?,payload_json=? WHERE job_id=?",(job.status.value,utc_now(),json.dumps(job.to_dict(),ensure_ascii=False),job.job_id))
            if cur.rowcount != 1: raise KeyError(f"Unknown queue job: {job.job_id}")
        return job

    def remove(self, job_id: str):
        with self._lock, self._session() as db:
            row=db.execute("SELECT status FROM jobs WHERE job_id=?",(job_id,)).fetchone()
            if row is None: raise KeyError(f"Unknown queue job: {job_id}")
            if row["status"] != JobStatus.QUEUED.value: raise ValueError("Only queued jobs can be removed.")
            db.execute("DELETE FROM jobs WHERE job_id=?",(job_id,))

    def claim_next(self) -> JobRecord | None:
        from dataclasses import replace
        with self._lock:
            db=self._connect()
            try:
                db.execute("BEGIN IMMEDIATE")
                row=db.execute("SELECT payload_json FROM jobs WHERE status=? ORDER BY created_at,rowid LIMIT 1",(JobStatus.QUEUED.value,)).fetchone()
                if row is None: db.commit(); return None
                job=JobRecord.from_dict(json.loads(row["payload_json"]))
                claimed=replace(job,status=JobStatus.PROCESSING,started_at=utc_now(),completed_at=None,error=None,current_stage="starting",progress=0.0)
                db.execute("UPDATE jobs SET status=?,updated_at=?,payload_json=? WHERE job_id=?",(claimed.status.value,utc_now(),json.dumps(claimed.to_dict(),ensure_ascii=False),claimed.job_id))
                db.commit(); return claimed
            except Exception:
                db.rollback(); raise
            finally: db.close()

    def recover_interrupted(self) -> int:
        from dataclasses import replace
        recovered=0
        with self._lock:
            db=self._connect()
            try:
                db.execute("BEGIN IMMEDIATE")
                rows=db.execute("SELECT payload_json FROM jobs WHERE status=?",(JobStatus.PROCESSING.value,)).fetchall()
                for row in rows:
                    job=JobRecord.from_dict(json.loads(row["payload_json"]))
                    restored=replace(job,status=JobStatus.QUEUED,current_stage=None,progress=0.0,started_at=None,error="Recovered after an interrupted application session.")
                    db.execute("UPDATE jobs SET status=?,updated_at=?,payload_json=? WHERE job_id=?",(restored.status.value,utc_now(),json.dumps(restored.to_dict(),ensure_ascii=False),restored.job_id)); recovered+=1
                db.commit(); return recovered
            except Exception:
                db.rollback(); raise
            finally: db.close()

    def set_meta(self,key: str,value: Any):
        with self._lock,self._session() as db:
            db.execute("INSERT INTO queue_meta VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,json.dumps(value,ensure_ascii=False)))

    def get_meta(self,key: str,default: Any=None) -> Any:
        with self._lock,self._session() as db: row=db.execute("SELECT value FROM queue_meta WHERE key=?",(key,)).fetchone()
        return json.loads(row["value"]) if row else default
