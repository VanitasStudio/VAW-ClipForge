# Repository structure

The public repository contains the application package, product assets, documentation and GitHub project metadata. Generated binaries, local model caches, temporary media, one-off patches and maintainer-only test fixtures are kept outside the public source tree.

```text
VAW-ClipForge/
├── .github/              GitHub workflows and contribution templates
├── assets/               Product identity, fonts, icons and bundled resources
├── clipforge/            Application package and runtime modules
├── docs/                 Product, architecture, security and release documentation
├── .gitattributes        Text and line-ending policy
├── .gitignore            Generated and local-only file exclusions
├── CONTRIBUTING.md       Contribution guidelines
├── README.md             Product overview and user documentation
├── RELEASE_NOTES.md      Latest release notes
└── SECURITY.md           Security reporting policy
```

## Import policy

Runtime code belongs in `clipforge/` and should use package-qualified imports, for example:

```python
from clipforge.clip_engine import probe_duration
```

Do not place application modules in the repository root. Keep temporary scripts, local model files, exported media, build output and historical patch utilities out of version control.

## Release artifacts

The Windows desktop executable is a generated release artifact and is not committed to the source repository. Attach the packaged executable to the corresponding GitHub Release. Keep release notes current and avoid committing build output or user-specific configuration.

## GitHub validation

The GitHub Actions workflow performs static Python compilation checks on the application package for pushes and pull requests. Full runtime, UI and video-rendering validation is performed on the Windows maintainer machine before a desktop release.
