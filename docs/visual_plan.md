# Visual launch plan

This plan is optimized for a GitHub README, X, Product Hunt, Hacker News, and short-form developer demos. The goal is to show a believable transformation—not a feature tour.

## Visual direction

- Use the dark theme, 16:9 canvas, and a clean desktop with notifications disabled.
- Capture at 1920×1080, then export the README GIF at 1280×720 or 1440×810.
- Use one high-contrast example throughout: a short Japanese prompt that becomes an immediately recognizable, polished image.
- Keep the cursor movement deliberate. One action per shot; no hunting through menus.
- Hide API keys, account names, balances, local paths, notifications, and unrelated browser tabs.
- Prefer real-time UI motion. Speed up only provider wait time, and disclose the cut with a subtle progress transition.

## Required README GIF

Target: **6–9 seconds**, silent, under **10 MB**, looping cleanly.

1. **0.0–1.5 s — The idea**  
   Open on the Generation tab with `雨の東京、ネオン、静かな侍` typed into the prompt field. Frame the prompt, model picker, and preview together.
2. **1.5–3.0 s — One decisive action**  
   Select a visually recognizable model preset and click the bright **Generate** button. Keep the pointer still after the click.
3. **3.0–6.5 s — Momentum**  
   Show the background job bar moving from queued to complete. Compress only the waiting portion; retain the UI feedback.
4. **6.5–9.0 s — Payoff**  
   Reveal the generated image and its prompt/model metadata. End on the exact frame used at the start of the loop or crossfade to it.

Recommended tools: ScreenToGif on Windows, Kap on macOS, or OBS plus `ffmpeg`. This repository also includes `scripts/capture_demo.py`, which records a reproducible mock-mode GIF from the real UI for documentation and CI-safe previews.

Export checklist:

- Crop out the OS taskbar and window chrome where possible.
- Remove pauses longer than 500 ms except the deliberate reveal.
- Export at 12–15 fps with a 64–128 color adaptive palette.
- Verify readable text at 50% browser zoom.
- Save as `docs/assets/demo.gif` and confirm it renders from the GitHub file view.

Example optimization command:

```bash
ffmpeg -i demo-source.mp4 -vf "fps=15,scale=1280:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer" -loop 0 docs/assets/demo.gif
```

## Screenshot shot list

### 1. Hero — “the whole creative loop”

- Show the Generation tab at 1440×900.
- Keep a concise Japanese prompt on the left and the strongest finished result on the right.
- Make the selected model, style, and Generate action visible without scrolling.
- Avoid empty panels, dialogs, test images, and long prompts.
- README caption: **From idea to organized asset in one workspace.**

### 2. Model catalog — “choose the right engine”

- Fill the viewport with model cards and keep provider tags visible.
- Select one useful filter so the interface looks active, not staged.
- Capture a hover tooltip only if it adds a concrete capability or cost detail.
- Caption: **Compare providers without leaving your project.**

### 3. Expert mode — “power without clutter”

- Use a model with distinctive controls and expose 3–5 meaningful parameters.
- Keep the resulting preview visible so controls and consequence share one frame.
- Caption: **Simple defaults. Model-native control when it matters.**

### 4. Queue and gallery — “production workflow”

- Queue: show one running job, two pending variations, and clear progress.
- Gallery: show a coherent 2×3 set from one campaign, with one favorite selected.
- Never include customer assets, personal filenames, or unreleased brand work.
- Caption: **Batch, compare, recover context, and keep moving.**

## 15-second launch video storyboard

| Time | Picture | On-screen copy | Audio / motion |
| --- | --- | --- | --- |
| 0–3 s | Rapid split-screen: provider tabs and scattered output files collapse into one polished GPT Image Studio window; flash the final image for 0.4 s. | **AI image workflows are fragmented.** | Tight impact sound, then silence. |
| 3–5 s | Type one short Japanese idea into the prompt field. | **Write naturally.** | Keystrokes at 1.3× speed. |
| 5–7 s | Pick a provider/model and switch briefly from Simple to Expert. | **Choose any engine.** | One clean cursor arc. |
| 7–10 s | Click Generate; queue animation accelerates; the final image lands in the preview. | **Create in one flow.** | Progress pulse into reveal hit. |
| 10–12 s | Gallery view shows variations, favorite, and metadata/context restore. | **Every result stays reusable.** | Quick 2-shot montage. |
| 12–15 s | Logo and hero result on dark background. | **GPT Image Studio**  
**Open source · Star on GitHub**  
`github.com/YOUR_GITHUB_USERNAME/GPT-Image-Studio` | Hold URL for a full 2 seconds. |

## Platform-specific edits

- **X:** upload native MP4, use the final image as the poster frame, and put the repository link in the first post plus the first reply.
- **Product Hunt:** lead with the 15-second video, then hero screenshot, model catalog, Expert mode, and gallery. Avoid text-heavy slides.
- **Hacker News:** use the real UI GIF in the README but keep the post itself factual: what it does, why it was built, architecture, and limitations.

## Final visual QA

- [ ] The first frame communicates “AI image studio” without narration.
- [ ] A real input → action → output transformation is visible.
- [ ] No secret, username, absolute path, balance, notification, or private asset appears.
- [ ] The GIF loops cleanly and is below 10 MB.
- [ ] The video URL remains readable for at least 2 seconds.
- [ ] All visuals match the current release UI.

