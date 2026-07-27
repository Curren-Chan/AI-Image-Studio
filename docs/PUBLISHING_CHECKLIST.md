# Publishing checklist

## One-time repository setup

- [ ] Replace every `YOUR_GITHUB_USERNAME` occurrence with the final GitHub owner.
- [ ] Confirm the repository name. If it is not `GPT-Image-Studio`, update badges, clone commands, discussion links, and video end cards.
- [ ] Update the `LICENSE` copyright holder if a person or organization should be named.
- [ ] Initialize a fresh Git repository from this `github/` directory; do not copy the parent `.git` history.
- [ ] Make the default branch `main` and require CI before merge.
- [ ] Enable Discussions, Issues, private vulnerability reporting, secret scanning/push protection, and Dependabot alerts.
- [ ] Add repository topics: `ai-image-generation`, `pyside6`, `python`, `openai`, `fal-ai`, `desktop-app`, `generative-ai`, `image-editor`.
- [ ] Set the description to: **Multi-provider AI image generation, prompt translation, and asset management in one desktop studio.**
- [ ] Upload a 1280×640 social preview image using the hero visual system.

Find unresolved placeholders:

```bash
git grep -n "YOUR_GITHUB_USERNAME"
```

## Release candidate verification

- [ ] Create `.env` from `.env.example` locally and verify each supported provider separately.
- [ ] Confirm mock mode starts with no `.env`.
- [ ] Run `python scripts/security_check.py`.
- [ ] Run `python -m pytest -q` on Windows and at least one Unix platform.
- [ ] Build with `pyinstaller --noconfirm --clean GPTImageStudio.spec`.
- [ ] Launch the extracted bundle on a clean machine and verify templates, resources, translation rules, gallery, and output folder behavior.
- [ ] Review provider names, model availability, pricing assumptions, and API behavior against current provider documentation.
- [ ] Generate `docs/assets/demo.gif` and inspect every frame for private data.
- [ ] Verify README links and images from GitHub's rendered preview.
- [ ] Update `core/version.py`, `pyproject.toml`, and `CHANGELOG.md` to the same version.

## Launch sequence

1. Publish a tagged GitHub Release and wait for every OS archive to finish.
2. Install one archive from the Release page as a user would.
3. Publish the 15-second native video on X and Product Hunt using `docs/visual_plan.md`.
4. Post a technically honest Show HN with architecture, mock-mode instructions, limitations, and a direct repository link.
5. Answer the first issues quickly, label beginner-friendly work, and turn repeated questions into docs.

