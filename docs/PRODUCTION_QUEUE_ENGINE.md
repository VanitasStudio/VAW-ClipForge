# Production Queue Engine

## Current implementation

The queue engine is a local-first, SQLite-backed sequential job scheduler. It is deliberately separate from the Tkinter UI and the media pipeline so both can be integrated without coupling UI callbacks to long-running work.

### Components

- `JobRecord`: serializable job contract, effective preset/config snapshot, isolated output directory, lifecycle timestamps, stage progress, retry count, and error details.
- `QueueStore`: SQLite persistence using WAL, transactional job claiming, and recovery of jobs left in `processing` after an unclean exit.
- `QueueManager`: batch admission, per-source overrides, status transitions, progress updates, retry, and pending-job removal.
- `QueueScheduler`: one background worker; processes one job at a time and continues after an individual job fails.
- `QueueEvent`: structured event payloads for UI integration.

### State lifecycle

`queued -> processing -> completed | failed`

Failed and cancelled jobs may be retried. Retrying preserves the original job ID, effective configuration snapshot, output directory, and cache location so compatible existing pipeline caches can be reused.

### Hybrid preset behavior

The batch preset is copied into each job at admission time. A job-specific override is merged before the snapshot is persisted. Nested configuration values are JSON-copied to prevent later mutation of shared dictionaries from changing an admitted job.

### Output isolation

Each job receives a directory named from the source stem plus an eight-character job ID suffix. Two files with the same source filename therefore cannot share an output directory.

### Recovery and safety

At startup, jobs persisted as `processing` are moved back to `queued`. The runner must be idempotent with respect to its job output directory and should reuse valid source-fingerprint caches where available. The scheduler's pause operation is intentionally pause-after-current; it does not kill FFmpeg or interrupt a partially written render.

### UI integration

The desktop app now exposes a Vanitas-styled Production Queue window with multi-file local import, batch preset capture, job-level overrides (resolution, highlight count/duration, story duration, output modes, captions), sequential start, pause-after-current, resume, retry, pending-job removal, job details, and live state refresh. Queue events are marshalled through the existing UI message queue; worker threads do not manipulate Tk widgets directly.

### Current boundary

The queue engine and GUI wiring are implemented. Automated engine/runner tests, a Windows GUI initialization smoke test, a synthetic-media batch run, and a PyInstaller one-file build pass. The tracked portable build specification is `packaging/VAW-ClipForge.spec`; build with `python -m PyInstaller --noconfirm --distpath dist --workpath build packaging/VAW-ClipForge.spec`. Long-form creator footage, Gemini Story Composer batches, and final release validation remain required before publishing this update.
