param(
    [switch]$Clean
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$Root = (Get-Location).Path
$PyInstaller = Join-Path $env:APPDATA "Python\Python314\Scripts\pyinstaller.exe"
if (-not (Test-Path $PyInstaller)) { $PyInstaller = "pyinstaller" }
if ($Clean) {
    Remove-Item "$Root\build" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item "$Root\dist\VAW-ClipForge.exe" -Force -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Force "$Root\build", "$Root\dist" | Out-Null
$PyInstallerArgs = @(
    "--noconfirm", "--onefile", "--windowed",
    "--distpath", "$Root\dist",
    "--workpath", "$Root\build\work",
    "--specpath", "$Root\build",
    "--name", "VAW-ClipForge",
    "--icon", "$Root\assets\branding\vanitas.ico",
    "--add-data", "$Root\assets;assets",
    "--collect-all", "cv2",
    "--collect-all", "PIL",
    "--collect-all", "av",
    "--collect-all", "faster_whisper",
    "--collect-all", "ctranslate2",
    "--collect-all", "scenedetect",
    "--collect-all", "yt_dlp",
    "--collect-all", "onnxruntime",
    "--collect-all", "imageio_ffmpeg",
    "--hidden-import", "clipforge.vanitas_widgets",
    "--hidden-import", "clipforge.composition_review",
    "--hidden-import", "clipforge.review_editor",
    "--hidden-import", "clipforge.gemini_connection",
    "--hidden-import", "clipforge.video_vision_adapter",
    "--hidden-import", "clipforge.multimodal_fusion",
    "--hidden-import", "clipforge.vision_cache",
    "--hidden-import", "clipforge.vision_quality",
    "--hidden-import", "clipforge.title_hashtag_suggestions",
    "--hidden-import", "clipforge.story_composer",
    "--hidden-import", "clipforge.unified_analyzer",
    "--hidden-import", "clipforge.smart_duration",
    "--hidden-import", "clipforge.smart_reframe",
    "--hidden-import", "clipforge.subject_tracking",
    "--hidden-import", "clipforge.subtitle_presets",
    "--hidden-import", "clipforge.url_source",
    "--hidden-import", "clipforge.secure_config",
    "$Root\main.py"
)
Write-Host "Building VAW ClipForge for Windows..." -ForegroundColor Cyan
& $PyInstaller @PyInstallerArgs
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
$Exe = "$Root\dist\VAW-ClipForge.exe"
if (-not (Test-Path $Exe)) { throw "Build finished but EXE was not found." }
$Size = [math]::Round((Get-Item $Exe).Length / 1MB, 1)
Write-Host "BUILD SUCCESS: $Exe ($Size MB)" -ForegroundColor Green
