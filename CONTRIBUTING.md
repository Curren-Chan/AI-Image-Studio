# Contributing to GPT Image Studio

Thanks for helping make creative AI workflows more open and usable. Small, focused changes with a clear before/after are the easiest to review.

## Before you start

- Search existing issues and discussions.
- Open an issue first for large UX changes, new providers, schema migrations, or breaking behavior.
- Never include real API keys, generated customer assets, local databases, logs, or personal paths.
- Keep provider-specific behavior behind the existing provider abstractions.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python main.py
```

The app supports mock mode without credentials. Use real provider calls only when necessary, with low-cost test prompts and keys stored in your ignored `.env`.

## Quality checks

Run these before opening a pull request:

```bash
python scripts/security_check.py
python -m compileall -q api core database plugins services ui utils app.py main.py
python -m pytest -q
```

For UI changes, attach a screenshot or short GIF and state the tested OS, Python version, theme, and display scaling.

## Pull requests

- Use a descriptive title and explain the user-visible outcome.
- Link the issue, if one exists.
- Add or update tests for behavior changes.
- Update README, user guide, model metadata, and changelog when applicable.
- Avoid drive-by formatting or unrelated refactors.
- Keep commits free of secrets and runtime artifacts.

By contributing, you agree that your contributions are licensed under the MIT License.

