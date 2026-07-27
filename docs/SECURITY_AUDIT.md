# Public release security audit

Audit date: **2026-07-27**  
Scope: the original development workspace and the publish-ready snapshot in this directory.

## Outcome

No high-confidence provider token, GitHub/Slack token, PEM private key, or personal absolute user path was detected in the public source snapshot. API credentials are read from environment variables and the ignored local `.env` file.

This is a best-effort source review, not a guarantee that a previously published Git history is clean. The recommended launch path is to initialize a new repository from this snapshot.

## Sensitive local files excluded

| Item in development workspace | Observed size | Reason excluded |
| --- | ---: | --- |
| `.env` | 711 bytes | May contain live provider credentials. |
| `database.db` | 385,024 bytes | Local projects, generation history, metadata, and settings. |
| `settings.json` | 414 bytes | User-specific preferences and enabled model state. |
| `logs/` | Runtime-dependent | May contain prompts, provider errors, or local paths. |
| `outputs/` | Runtime-dependent | User-generated images and metadata. |
| `配布20260725.zip` | 1,484,006 bytes | Stale release artifact; binaries should come from tagged CI builds. |
| Python/tool caches | Runtime-dependent | Reproducible cache and bytecode data, not source. |

The public `.gitignore` blocks all of the above categories. `.env.example` documents only variable names and dummy values.

## Scan coverage

- Common OpenAI-, Google-, GitHub-, and Slack-style token prefixes
- PEM private-key headers
- Windows, macOS, and Linux user-home absolute paths
- Credential environment-variable usage and configuration flow
- Cache, temporary, database, log, generated-output, archive, and build artifacts
- Git-tracked status of high-risk root files in the development workspace

The original `.env` was inspected by key name only; values were not printed. The following names are expected and documented safely: `OPENAI_API_KEY`, `OPENAI_MODEL_TEXT`, `OPENAI_MODEL_IMAGE`, `FAL_KEY`, `GEMINI_API_KEY`, `XAI_API_KEY`, and `HOTAPI_KEY`.

## Cleanup decisions

- Copied only application source, tests, static resources, templates, and user documentation.
- Excluded live-provider scratch scripts and one-off root test scripts from the public snapshot; maintained tests remain under `tests/`.
- Excluded the internal long-form development diary in favor of the curated `CHANGELOG.md`.
- Preserved the original worktree and its uncommitted changes untouched.
- Added `scripts/security_check.py`; CI fails if a high-confidence secret, personal user path, `.env`, database, or runtime settings file enters the public tree.

## Maintainer actions before launch

1. Revoke and recreate any credential that may ever have been shared, copied into a ZIP, or committed elsewhere.
2. Initialize a new Git repository from this directory instead of reusing an uncertain history.
3. Run `python scripts/security_check.py` before every public push.
4. Enable GitHub secret scanning, push protection, Dependabot alerts, and private vulnerability reporting.
5. Review generated screenshots and GIFs frame by frame for keys, usernames, paths, balances, and private assets.

