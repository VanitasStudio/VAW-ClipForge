# Contributing

## Before opening a pull request

1. Keep changes focused and explain the user-visible impact.
2. Preserve local-first media processing and explicit Gemini opt-in.
3. Follow docs/VANITAS_BRAND_UI.md for all interface changes.
4. Add or update regression tests for changed behavior.
5. Run the Windows QA script: powershell -ExecutionPolicy Bypass -File .\scripts\run_qa.ps1.
6. Never commit media, generated exports, API keys, model caches, backups or build output.

## UI requirements

- Use Archivo for functional UI and Quantico only for product display/wordmark.
- Reuse shared controls from vanitas_widgets.py.
- Do not introduce platform-native dropdowns or scrollbars.
- Verify pointer and keyboard interaction for every interactive control.
- Keep UI copy concise and source files UTF-8 encoded.

## Pull requests

Describe the problem, approach, tests run, and Windows-specific verification. Include screenshots for user-visible UI changes.
