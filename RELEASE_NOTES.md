# VAW ClipForge v1.2.1 ? Vanitas Studio Identity & Controls

## Brand system
- Replaced the Porto Web orange accent with the master Vanitas Studio logo palette: obsidian, midnight navy, metallic silver, electric cobalt and ionic blue.
- Standardized the main workspace, Review Studio and Composition Review around the same palette and Archivo / Quantico typography.
- Replaced geometric-cut styling with rounded cards, buttons, controls and popup surfaces.

## Custom controls
- Custom dropdowns support pointer and keyboard selection, including correct popup placement across multi-monitor Windows desktops.
- Canvas scrollbars use a dark track, rounded slate thumb and electric-blue hover/drag feedback.
- Custom rounded buttons, numeric steppers, checkboxes and sliders use the shared brand palette.
- Fixed malformed punctuation in Composition Review's window title.

## Repository architecture
- Moved all 28 runtime modules into the dedicated `clipforge/` Python package.
- Added a minimal root `main.py` entry point; application source no longer lives in the repository root.
- Updated application imports, QA tests, diagnostics, Review Studio launch routing and PyInstaller hidden imports for package-based execution.
- Added `docs/REPOSITORY_STRUCTURE.md` and updated the contributor-facing repository overview.
- Rebuilt the Windows one-file executable and verified the application launches from the packaged build.
- Full maintained QA suite: 53 tests passed.

## Quality
- Added regression coverage for branded controls, popup placement, selection behavior and Windows packaging.
- Preserved the one-file, windowed Windows executable workflow.
