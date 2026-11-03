# Repository structure

    VAW-ClipForge/
    ??? clipforge/              Application package and runtime modules
    ??? assets/                 Brand assets, fonts, icons and bundled resources
    ??? docs/                   Product, architecture and release documentation
    ?   ??? archive/releases/   Historical release notes
    ??? scripts/                Build, QA and setup automation
    ??? tests/                  Automated tests and QA fixtures
    ??? tools/
    ?   ??? diagnostics/        Maintainer diagnostics
    ?   ??? legacy_patches/     Historical one-off migration scripts (not runtime)
    ??? .github/                GitHub workflows and templates
    ??? main.py                 Thin application entry point
    ??? START_CLIPFORGE.cmd     Windows launcher for packaged executable
    ??? START_REVIEW_STUDIO.cmd Windows Review Studio launcher

## Import policy

Runtime modules are imported through the clipforge package (for example,
from clipforge.clip_engine import probe_duration). Tests use the same public
package path. New runtime modules belong in clipforge/; do not add application
modules to the repository root.

## Build policy

scripts/build_windows.ps1 packages main.py with PyInstaller. Static package
imports are preferred; explicit hidden imports use fully-qualified clipforge.*
names. Bundled assets remain at the repository/bundle root and are resolved
independently of the Python package location.
