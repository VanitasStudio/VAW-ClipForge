# -*- mode: python ; coding: utf-8 -*-
"""Portable PyInstaller entry point for VAW ClipForge."""
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).resolve().parent

datas = [(str(ROOT / "assets"), "assets")]
binaries = []
hiddenimports = [
    "clipforge.production_queue",
    "clipforge.production_queue.models",
    "clipforge.production_queue.store",
    "clipforge.production_queue.manager",
    "clipforge.production_queue.scheduler",
    "clipforge.production_queue.runner",
    "clipforge.vanitas_widgets",
    "clipforge.composition_review",
    "clipforge.review_editor",
    "clipforge.gemini_connection",
    "clipforge.video_vision_adapter",
    "clipforge.multimodal_fusion",
    "clipforge.vision_cache",
    "clipforge.vision_quality",
    "clipforge.title_hashtag_suggestions",
    "clipforge.story_composer",
    "clipforge.unified_analyzer",
    "clipforge.smart_duration",
    "clipforge.smart_reframe",
    "clipforge.subject_tracking",
    "clipforge.subtitle_presets",
    "clipforge.url_source",
    "clipforge.secure_config",
]

for package in (
    "cv2", "PIL", "av", "faster_whisper", "ctranslate2",
    "scenedetect", "yt_dlp", "onnxruntime", "imageio_ffmpeg",
):
    collected = collect_all(package)
    datas += collected[0]
    binaries += collected[1]
    hiddenimports += collected[2]

a = Analysis(
    [str(ROOT / "clipforge" / "clipforge_gui.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="VAW-ClipForge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "assets" / "branding" / "vanitas.ico"),
)
