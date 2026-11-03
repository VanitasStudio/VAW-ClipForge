"""Local hardware profiling and safe acceleration policy for VAW ClipForge.

The app stays local-first. CUDA is preferred when CTranslate2 can see a GPU;
all accelerated paths retain a CPU fallback for machines without CUDA runtime
libraries or with insufficient GPU resources.
"""
from __future__ import annotations

import ctypes
import os
import subprocess
from dataclasses import dataclass
from functools import lru_cache

_CUDA_DLL_HANDLES = []


def _windows_cuda_runtime_ready() -> bool:
    """CTranslate2 CUDA requires CUDA 12 cuBLAS and cuDNN 9 runtime DLLs."""
    if os.name != "nt":
        return True
    try:
        for name in ("cublas64_12.dll", "cudnn64_9.dll"):
            _CUDA_DLL_HANDLES.append(ctypes.WinDLL(name))
        return True
    except (OSError, AttributeError):
        _CUDA_DLL_HANDLES.clear()
        return False


@lru_cache(maxsize=4)
def video_encoder_args(ffmpeg_path: str, quality: int = 22) -> tuple[str, ...]:
    """Use NVIDIA NVENC when the installed FFmpeg can really encode with it."""
    probe = [
        ffmpeg_path, "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=black:s=320x240:d=0.1",
        "-frames:v", "1", "-an", "-c:v", "h264_nvenc",
        "-preset", "p4", "-rc", "vbr", "-cq", str(int(quality)),
        "-b:v", "0", "-pix_fmt", "yuv420p", "-f", "null", "-",
    ]
    try:
        run_options = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.PIPE,
            "timeout": 15,
            "check": False,
        }
        if os.name == "nt":
            run_options["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        result = subprocess.run(probe, **run_options)
        if result.returncode == 0:
            return (
                "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "vbr",
                "-cq", str(int(quality)), "-b:v", "0", "-pix_fmt", "yuv420p",
            )
    except (OSError, subprocess.TimeoutExpired):
        pass
    return ("-c:v", "libx264", "-preset", "veryfast", "-crf", str(int(quality)), "-pix_fmt", "yuv420p")


def video_encoder_label(ffmpeg_path: str) -> str:
    return "NVIDIA NVENC" if "h264_nvenc" in video_encoder_args(ffmpeg_path) else "CPU x264"


@dataclass(frozen=True)
class LocalPerformanceProfile:
    device: str
    compute_type: str
    cpu_threads: int
    num_workers: int
    opencv_threads: int
    logical_cpus: int
    physical_cpus: int
    cuda_devices: int
    reason: str

    @property
    def label(self) -> str:
        if self.device == "cuda":
            return f"NVIDIA CUDA / {self.compute_type}"
        return f"CPU / {self.compute_type}"


def detect_local_performance(preference: str | None = None) -> LocalPerformanceProfile:
    """Select the fastest safe Whisper backend available on this machine.

    CLIPFORGE_WHISPER_DEVICE may be set to ``auto``, ``cuda`` or ``cpu``.
    An explicit CUDA request still falls back safely if CUDA is unavailable.
    """
    logical = max(1, int(os.cpu_count() or 1))
    try:
        import psutil  # optional; used only to estimate physical cores
        physical = int(psutil.cpu_count(logical=False) or max(1, logical // 2))
    except Exception:
        physical = max(1, logical // 2)

    physical = max(1, min(physical, logical))
    cpu_threads = max(1, min(8, physical - 1 if physical > 2 else physical))
    opencv_threads = max(1, min(4, physical // 2 or 1))
    requested = (preference or os.getenv("CLIPFORGE_WHISPER_DEVICE", "auto")).strip().lower()
    if requested not in {"auto", "cuda", "cpu"}:
        requested = "auto"

    cuda_devices = 0
    cuda_types: set[str] = set()
    runtime_ready = requested == "cpu" or _windows_cuda_runtime_ready()
    if requested != "cpu" and runtime_ready:
        try:
            import ctranslate2
            cuda_devices = int(ctranslate2.get_cuda_device_count())
            if cuda_devices:
                cuda_types = set(ctranslate2.get_supported_compute_types("cuda"))
        except Exception:
            cuda_devices = 0
            cuda_types = set()

    if cuda_devices and cuda_types:
        # FP16 is broadly supported by modern NVIDIA cards, including GTX 16xx.
        # Prefer it for accuracy; CTranslate2 still falls back if the CUDA/cuDNN
        # runtime is missing when the model is actually initialized.
        compute = "float16" if "float16" in cuda_types else (
            "int8_float16" if "int8_float16" in cuda_types else "float32"
        )
        return LocalPerformanceProfile(
            device="cuda", compute_type=compute, cpu_threads=cpu_threads,
            num_workers=1, opencv_threads=opencv_threads,
            logical_cpus=logical, physical_cpus=physical,
            cuda_devices=cuda_devices,
            reason="NVIDIA CUDA device detected; local speech analysis will use GPU acceleration.",
        )

    return LocalPerformanceProfile(
        device="cpu", compute_type="int8", cpu_threads=cpu_threads,
        num_workers=1, opencv_threads=opencv_threads,
        logical_cpus=logical, physical_cpus=physical,
        cuda_devices=cuda_devices,
        reason=("CPU mode was requested." if requested == "cpu" else
                "CUDA runtime unavailable; using optimized CPU inference."),
    )


def profile_summary(profile: LocalPerformanceProfile) -> str:
    return (
        f"Local engine: {profile.label}; {profile.physical_cpus} cores / "
        f"{profile.logical_cpus} threads; CPU fallback budget {profile.cpu_threads} threads."
    )
