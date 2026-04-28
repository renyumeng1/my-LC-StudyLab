# Suggested Commands

Windows / PowerShell project commands inferred from current files:

- List files: `rg --files`
- Search text: `rg "pattern"`
- Backend dependency management likely uses uv/pyproject; inspect `backend/pyproject.toml` before adding dependencies.
- Potential backend checks after code changes: run the project's configured test/lint commands if added later. No concrete test/lint scripts were observed during onboarding.