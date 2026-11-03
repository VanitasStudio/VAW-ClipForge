# Local Performance Engine

ClipForge profiles the host machine and selects safe local processing backends. Original media and full transcripts remain on the user's device.

## Runtime policy

- Whisper uses NVIDIA CUDA only when CTranslate2, CUDA 12 cuBLAS, and cuDNN 9 runtime libraries are available.
- If CUDA is unavailable or inference fails, Whisper automatically retries with CPU `int8` inference.
- CPU inference reserves capacity for the desktop by using a bounded thread budget and one worker.
- Whisper transcript boundaries are cached against the exact source file, model, and analyzer version.
- Scene detection samples every other frame (15 fps for a 30 fps source) to reduce decode work while retaining practical editorial cut precision.
- FFmpeg probes NVENC with a real encode before selecting it. Story segment rendering, final composition encoding, and subtitle burn-in use NVIDIA NVENC when available; otherwise they use `libx264`.

## PC-VAWRIEL profile (verified 4 November 2026)

- AMD Ryzen 5 PRO 4655G — 6 cores / 12 threads.
- 16 GB system memory.
- NVIDIA GeForce GTX 1660 SUPER — 6 GB VRAM.
- FFmpeg `h264_nvenc` runtime encode probe: passed.
- CTranslate2 reports a CUDA device, but this Windows installation does not currently expose `cublas64_12.dll` and `cudnn64_9.dll`. Whisper therefore selects CPU `int8` instead of entering a GPU path that cannot complete inference.

## Optional CUDA enablement

Install a compatible CUDA 12 runtime and cuDNN 9 runtime for CTranslate2, then restart ClipForge. The application re-checks the libraries at startup and will select CUDA FP16 when the runtime is usable. No CUDA toolkit installation is required for the current CPU/NVENC workflow.

## Diagnostics

The activity log reports the selected Whisper backend, transcription progress, scene-scan frame count and duration, and the selected FFmpeg encoder. Users can set `CLIPFORGE_WHISPER_DEVICE=auto`, `cuda`, or `cpu` to override backend preference for diagnostics.
