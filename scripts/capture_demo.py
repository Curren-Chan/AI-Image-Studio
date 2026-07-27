"""Capture a short, reproducible GIF from the real UI in credential-free mock mode."""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image
from PySide6.QtWidgets import QApplication

from core.coordinator import Coordinator
from ui.main_window import MainWindow


def grab_frame(window: MainWindow, frame_path: Path) -> Image.Image:
    if not window.grab().save(str(frame_path), "PNG"):
        raise RuntimeError("Qt could not capture the application window")
    with Image.open(frame_path) as image:
        frame = image.convert("RGB")
    width = 960
    height = round(frame.height * width / frame.width)
    return frame.resize((width, height), Image.Resampling.LANCZOS)


def pump(app: QApplication, seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.03)


def main() -> int:
    output = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "docs" / "assets" / "demo.gif"
    output.parent.mkdir(parents=True, exist_ok=True)
    frames: list[Image.Image] = []

    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix="gpt-image-studio-demo-") as data_dir:
        coordinator = Coordinator(project_root=data_dir, load_plugins=False)
        window = MainWindow(coordinator)
        window.resize(1200, 950)
        window.show()
        pump(app, 0.7)

        frame_path = Path(data_dir) / "frame.png"
        frames.extend([grab_frame(window, frame_path)] * 3)

        prompt = "雨の東京、ネオン、静かな侍、映画のような光"
        for index in range(1, len(prompt) + 1, 4):
            window.prompt_panel.prompt_input.setPlainText(prompt[:index])
            pump(app, 0.08)
            frames.append(grab_frame(window, frame_path))
        window.prompt_panel.prompt_input.setPlainText(prompt)
        pump(app, 0.12)
        frames.append(grab_frame(window, frame_path))

        window.prompt_panel.request_generation()
        for _ in range(18):
            pump(app, 0.22)
            frames.append(grab_frame(window, frame_path))
            if window.preview_panel.current_image_path:
                break

        if not window.preview_panel.current_image_path:
            raise RuntimeError("Mock generation did not finish before the capture timeout")

        pump(app, 0.5)
        final_frame = grab_frame(window, frame_path)
        frames.extend([final_frame] * 8)

        window.close()
        coordinator.shutdown(timeout_seconds=5.0)
        app.processEvents()

    palette_frames = [frame.quantize(colors=128, method=Image.Quantize.MEDIANCUT) for frame in frames]
    palette_frames[0].save(
        output,
        save_all=True,
        append_images=palette_frames[1:],
        duration=140,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(f"Wrote {output} ({output.stat().st_size / 1024 / 1024:.2f} MiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
