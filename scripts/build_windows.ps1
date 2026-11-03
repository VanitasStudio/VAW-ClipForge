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
    "--hidden-import", "vanitas_widgets",
    "--hidden-import", "composition_review",
    "--hidden-import", "review_editor",
    "--hidden-import", "gemini_connection",
    "--hidden-import", "video_vision_adapter",
    "--hidden-import", "multimodal_fusion",
    "--hidden-import", "vision_cache",
    "--hidden-import", "vision_quality",
    "--hidden-import", "title_hashtag_suggestions",
    "--hidden-import", "story_composer",
    "--hidden-import", "unified_analyzer",
    "--hidden-import", "smart_duration",
    "--hidden-import", "smart_reframe",
    "--hidden-import", "subject_tracking",
    "--hidden-import", "subtitle_presets",
    "--hidden-import", "url_source",
    "--hidden-import", "secure_config",
    "$Root\clipforge_gui.py"
)
Write-Host "Building VAW ClipForge for Windows..." -ForegroundColor Cyan
& $PyInstaller @PyInstallerArgs
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }
$Exe = "$Root\dist\VAW-ClipForge.exe"
if (-not (Test-Path $Exe)) { throw "Build finished but EXE was not found." }
$Size = [math]::Round((Get-Item $Exe).Length / 1MB, 1)
Write-Host "BUILD SUCCESS: $Exe ($Size MB)" -ForegroundColor Green
