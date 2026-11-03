$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    Write-Host "Compiling ClipForge runtime and supported QA modules..." -ForegroundColor Cyan
    @'
from pathlib import Path
import py_compile
root = Path(".")
files = list(root.glob("*.py"))
files += list((root / "tests").glob("qa_v12_*.py"))
files += list((root / "tests").glob("qa_v11_*.py"))
for path in files:
    py_compile.compile(str(path), doraise=True)
print(f"PY_COMPILE_OK: {len(files)} modules")
'@ | python -
    if ($LASTEXITCODE -ne 0) { throw "Python compilation failed." }

    Write-Host "Running v1.2 feature tests and v1.1 regression tests..." -ForegroundColor Cyan
    $tests = @(
        "tests.qa_v12_contracts",
        "tests.qa_v12_unified_analyzer",
        "tests.qa_v12_story_composer",
        "tests.qa_v12_video_vision",
        "tests.qa_v12_vision_intelligence",
        "tests.qa_v12_composition_render",
        "tests.qa_v12_ui_integration",
        "tests.qa_v12_review_ui",
        "tests.qa_v12_title_hashtags",
        "tests.qa_v12_branding_packaging",
        "tests.qa_v12_vanitas_controls",
        "tests.qa_v12_vanitas_controls_runtime",
        "tests.qa_v11_ui",
        "tests.qa_v11_gui_smoke"
    )
    python -m unittest $tests -v
    if ($LASTEXITCODE -ne 0) { throw "ClipForge QA suite failed." }

    Write-Host "CLIPFORGE_QA_PASS" -ForegroundColor Green
}
finally {
    Pop-Location
}
