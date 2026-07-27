from types import SimpleNamespace
import unittest

from core.event_bus import event_bus
from tests import TEST_APP
from ui.main_window import MainWindow
from ui.panels.gallery_panel import GalleryPanel


class _Card:
    def __init__(self, image_path: str, metadata: dict):
        self.image_path = image_path
        self.metadata = metadata
        self.selected = False

    def set_selected(self, selected: bool):
        self.selected = selected


class _ProjectService:
    def get_active_project_id(self):
        return 1


class _HistoryService:
    def get_history(self, **_kwargs):
        return []


class GalleryNonDestructiveTests(unittest.TestCase):
    def test_gallery_selection_does_not_request_context_load(self):
        coordinator = SimpleNamespace(
            project_service=_ProjectService(),
            history_service=_HistoryService(),
        )
        panel = GalleryPanel(coordinator)
        metadata = {"prompt_jp": "past prompt", "model_id": "past-model"}
        card = _Card("missing-preview.png", metadata)
        panel.cards = [card]
        requests = []
        panel.context_load_requested.connect(
            lambda image_path, context: requests.append((image_path, context))
        )

        panel.on_card_clicked(card.image_path, metadata)

        self.assertTrue(card.selected)
        self.assertIs(panel.selected_card, card)
        self.assertTrue(panel.btn_load_context.isEnabled())
        self.assertEqual(requests, [])

    def test_explicit_load_updates_generation_context_and_ui_event(self):
        metadata = {
            "prompt_jp": "past prompt",
            "prompt_en": "past prompt in English",
            "negative_prompt": "blur",
            "size": "1024x1536",
            "model_id": "past-model",
            "switch_tab": 0,
        }
        generation_calls = []
        preview_calls = []
        label_updates = []
        context_events = []
        window = SimpleNamespace(
            coordinator=SimpleNamespace(
                generation_service=SimpleNamespace(
                    set_context=lambda **kwargs: generation_calls.append(kwargs)
                )
            ),
            preview_panel=SimpleNamespace(
                set_image=lambda image_path, context: preview_calls.append(
                    (image_path, context)
                )
            ),
            prompt_panel=SimpleNamespace(
                update_context_label=lambda: label_updates.append(True)
            ),
        )

        callback = context_events.append
        event_bus.context_changed.connect(callback)
        try:
            MainWindow.on_gallery_context_load_requested(
                window, "selected.png", metadata
            )
            TEST_APP.processEvents()
        finally:
            event_bus.context_changed.disconnect(callback)

        self.assertEqual(preview_calls, [("selected.png", metadata)])
        self.assertEqual(
            generation_calls,
            [
                {
                    "prompt_jp": "past prompt",
                    "prompt_en": "past prompt in English",
                    "size": "1024x1536",
                    "negative_prompt": "blur",
                }
            ],
        )
        self.assertEqual(context_events, [metadata])
        self.assertEqual(label_updates, [True])


if __name__ == "__main__":
    unittest.main()
