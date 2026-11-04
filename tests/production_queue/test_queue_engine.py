from __future__ import annotations
import tempfile
import threading
import time
import unittest
from pathlib import Path

from clipforge.production_queue import JobStatus, QueueManager, QueueScheduler, QueueStore


class QueueEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source_a = self.root / "stream.mp4"
        self.source_b = self.root / "stream-copy.mp4"
        self.source_a.write_bytes(b"source-a")
        self.source_b.write_bytes(b"source-b")
        self.store = QueueStore(self.root / "state" / "queue.sqlite3")
        self.manager = QueueManager(self.store, self.root / "exports")

    def tearDown(self):
        self.temp.cleanup()

    def add(self, paths=None, config=None):
        return self.manager.add_sources(paths or [self.source_a], "creator-default", config or {"mode": "standalone"})

    def test_hybrid_config_is_snapshotted_and_output_paths_are_unique(self):
        override = {str(self.source_a.resolve()): {"captions": False}}
        jobs = self.manager.add_sources([self.source_a, self.source_b], "creator-default",
                                        {"mode": "story", "captions": True}, override)
        self.assertFalse(jobs[0].config_snapshot["captions"])
        self.assertTrue(jobs[1].config_snapshot["captions"])
        self.assertNotEqual(jobs[0].output_directory, jobs[1].output_directory)

    def test_batch_admission_handles_twenty_jobs_and_unique_outputs(self):
        paths=[]
        for index in range(20):
            source=self.root / f"source-{index:02d}.mp4"
            source.write_bytes(b"video")
            paths.append(source)
        jobs=self.add(paths,{"mode":"standalone"})
        self.assertEqual(len(jobs),20)
        self.assertEqual(len({job.output_directory for job in jobs}),20)
        self.assertEqual(sum(job.status==JobStatus.QUEUED for job in self.manager.list_jobs()),20)

    def test_batch_admission_is_all_or_nothing_for_invalid_source(self):
        invalid=self.root / "missing.mp4"
        with self.assertRaises(FileNotFoundError):
            self.add([self.source_a,invalid])
        self.assertEqual(self.manager.list_jobs(),[])

    def test_config_override_only_changes_queued_job_snapshot(self):
        nested={"captions":{"enabled":True}}
        job=self.manager.add_sources([self.source_a],"creator-default",nested)[0]
        nested["captions"]["enabled"]=False
        self.assertTrue(self.store.get(job.job_id).config_snapshot["captions"]["enabled"])
        updated=self.manager.update_config(job.job_id,{"resolution":"720p"})
        self.assertEqual(updated.config_snapshot["resolution"],"720p")
        self.manager.claim_next()
        with self.assertRaises(ValueError):
            self.manager.update_config(job.job_id,{"resolution":"1080p"})

    def test_claim_progress_and_complete(self):
        queued = self.add()[0]
        claimed = self.manager.claim_next()
        self.assertEqual(claimed.job_id, queued.job_id)
        self.assertEqual(claimed.status, JobStatus.PROCESSING)
        self.manager.update_progress(claimed.job_id, "analysis", 42)
        completed = self.manager.complete(claimed.job_id)
        self.assertEqual(completed.status, JobStatus.COMPLETED)
        self.assertEqual(completed.progress, 100)
        self.assertIsNone(self.manager.claim_next())

    def test_failed_job_can_be_retried_without_changing_snapshot(self):
        queued = self.add(config={"mode": "story", "resolution": "1080p"})[0]
        claimed = self.manager.claim_next()
        self.manager.fail(claimed.job_id, "render failed")
        retried = self.manager.retry(queued.job_id)
        self.assertEqual(retried.status, JobStatus.QUEUED)
        self.assertEqual(retried.retry_count, 1)
        self.assertEqual(retried.config_snapshot["resolution"], "1080p")

    def test_interrupted_processing_job_is_requeued_on_manager_start(self):
        queued = self.add()[0]
        self.manager.claim_next()
        recovered_manager = QueueManager(self.store, self.root / "exports")
        recovered = recovered_manager.list_jobs()[0]
        self.assertEqual(recovered.status, JobStatus.QUEUED)
        self.assertIn("interrupted", recovered.error)

    def test_only_queued_jobs_can_be_removed(self):
        queued = self.add()[0]
        self.manager.remove_pending(queued.job_id)
        self.assertEqual(self.manager.list_jobs(), [])
        next_job = self.add()[0]
        self.manager.claim_next()
        with self.assertRaises(ValueError):
            self.manager.remove_pending(next_job.job_id)

    def test_scheduler_is_sequential_and_continues_after_failure(self):
        jobs = self.add([self.source_a, self.source_b])
        order = []
        finished = threading.Event()
        def runner(job, progress):
            order.append(job.job_id)
            progress("analysis", 25)
            if job.job_id == jobs[0].job_id:
                raise RuntimeError("intentional test failure")
            finished.set()
        scheduler = QueueScheduler(self.manager, runner)
        scheduler.start()
        scheduler.notify_new_jobs()
        self.assertTrue(finished.wait(5), "second job did not run after first failed")
        scheduler.shutdown(wait=True, timeout=5)
        states = {job.job_id: job.status for job in self.manager.list_jobs()}
        self.assertEqual(order, [jobs[0].job_id, jobs[1].job_id])
        self.assertEqual(states[jobs[0].job_id], JobStatus.FAILED)
        self.assertEqual(states[jobs[1].job_id], JobStatus.COMPLETED)


if __name__ == "__main__":
    unittest.main()
