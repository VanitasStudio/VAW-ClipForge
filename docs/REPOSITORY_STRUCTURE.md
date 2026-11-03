# Repository Structure

The three Windows application entry modules and their single-purpose runtime modules remain at the root. This preserves current PyInstaller collection, local imports and Windows launcher compatibility. Supporting files are grouped by purpose.

    VAW-ClipForge/
    |-- assets/                  Vanitas branding, fonts and font licenses
    |-- docs/
    |   |-- archive/releases/    Historical release notes
    |   |-- VANITAS_BRAND_UI.md
    |   |-- REVIEW_STUDIO.md
    |   `-- ...
    |-- scripts/                 Build, QA and optional provider setup
    |-- tests/                   Regression and interaction tests
    |-- tools/
    |   |-- diagnostics/         Maintainer diagnostics
    |   `-- legacy_patches/      Historical one-off migration scripts
    |-- samples/                 Local-only QA media; not committed
    |-- clipforge_gui.py         Main Windows application entry
    |-- review_editor.py         Legacy clip review entry
    |-- composition_review.py    Story Composer review entry
    |-- vanitas_widgets.py       Shared custom Vanitas controls
    |-- START_CLIPFORGE.cmd
    |-- START_REVIEW_STUDIO.cmd
    |-- README.md
    `-- RELEASE_NOTES.md         Latest release only

## Development and QA

Run the supported Windows regression suite from the repository root:

    powershell -ExecutionPolicy Bypass -File .\scripts\run_qa.ps1

The suite compiles runtime modules and executes deterministic v1.2 feature tests, Vanitas control interaction tests, and v1.1 regression tests.

Some historical/manual QA scripts require local media fixtures, a configured Gemini key, network access or an interactive desktop session. Those scripts remain under tests/ but are not part of the default regression gate.

## Local-only data

Generated exports, source videos, Whisper models, URL caches, backups, build output, and local QA media must not be committed. The ignore rules enforce these boundaries.

## Runtime compatibility

Application modules remain at the repository root for the current Windows single-file packaging workflow. A package-layout migration is a separate engineering change because it affects import resolution, PyInstaller collection, and the existing launchers.
