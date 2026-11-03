# Security Policy

## Reporting a vulnerability

Do not publish exploit details, API keys, credentials, private media, or personal data in a public issue. Contact the repository maintainers privately through the repository owner profile and include:

- A concise impact summary
- Affected version or commit
- Reproduction steps that do not expose real user data
- Suggested mitigation, if known

## Security expectations

- Gemini is optional and explicit; local processing remains the default fallback.
- Never commit API keys, tokens, DPAPI material, credentials, or private source media.
- Treat downloaded media and metadata as untrusted input.
- Keep optional providers isolated and bounded.
