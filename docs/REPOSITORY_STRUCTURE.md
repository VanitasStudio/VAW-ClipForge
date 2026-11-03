# Repository Structure

ClipForge keeps its Windows entry points and runtime modules at the project root so the existing desktop launchers and local imports remain compatible. Supporting material is grouped by purpose.

~~~text
VAW-ClipForge/
├── clipforge_gui.py
├── START_CLIPFORGE.cmd
├── START_REVIEW_STUDIO.cmd
├── runtime modules (*.py)
├── tests/
│   ├── qa_v12_*.py
│   └── qa_v11_*.py
├── docs/
├── scripts/
├── tools/legacy_patches/
├── samples/       # Local-only media fixtures
├── exports/       # Generated media
├── models/        # Downloaded models
├── url-cache/     # Download cache
├── backups/       # Local recovery copies
├── README.md
└── .gitignore
~~~

## Development

Run the supported automated regression suite from the repository root:

~~~powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_qa.ps1
~~~

The suite compiles the Python modules and runs the deterministic v1.2 contract, analyzer, composer, vision, rendering, Review Studio, title/hashtag and v1.1 regression tests.

Some historical QA scripts require local sample media, a configured Gemini key, network access or a visible desktop session. They remain available in tests/ but are not part of the default regression command.

## Historical patch scripts

tools/legacy_patches/ contains one-off scripts used during earlier version migrations. They are retained for audit/history only. Do not run them against the current application unless a specific recovery procedure calls for it.

## Runtime compatibility

The runtime modules intentionally remain at the root for this cleanup pass. Moving them into a Python package would require a separate import/launcher migration and is not necessary to make the repository navigable.
