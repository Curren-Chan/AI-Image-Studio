# -*- coding: utf-8 -*-
import unittest
from unittest.mock import MagicMock, patch
from api.client import ApiClient
from api.model_registry import MODEL_REGISTRY
from services.image_gen.hotapi_provider import HotApiProvider
from services.image_gen.manager import ImageGenerationManager

class HotApiProviderTests(unittest.TestCase):
    def setUp(self):
        self.api_client = ApiClient(hotapi_key="hk_live_test123")
        self.provider = HotApiProvider(self.api_client)
        self.manager = ImageGenerationManager(self.api_client)

    def test_registered_hotapi_models_exist(self):
        hotapi_models = [k for k, v in MODEL_REGISTRY.items() if v.get("provider") == "hotapi"]
        self.assertIn("hotapi-z-image-spicy", hotapi_models)
        self.assertIn("hotapi-seedream-50-lite-spicy", hotapi_models)
        self.assertIn("hotapi-seedream-50-pro-spicy", hotapi_models)
        self.assertIn("hotapi-qwen-image-edit-spicy", hotapi_models)
        self.assertIn("hotapi-face-swap-spicy", hotapi_models)

        # Ensure all models carry TAG_NSFW
        for model_id in hotapi_models:
            tags = MODEL_REGISTRY[model_id].get("tags", [])
            self.assertIn("NSFW対応", tags)

    def test_mock_mode_generation(self):
        mock_api_client = ApiClient(hotapi_key=None)
        mock_provider = HotApiProvider(mock_api_client)
        img_bytes, pixel_size, cost = mock_provider.generate("z-image-spicy", "a spicy test prompt", "1024x1024", "standard")
        self.assertIsInstance(img_bytes, bytes)
        self.assertGreater(len(img_bytes), 0)
        self.assertEqual(pixel_size, "1024x1024")
        self.assertEqual(cost, 0.024)

    @patch("requests.post")
    @patch("requests.get")
    def test_real_api_task_submission_and_polling(self, mock_get, mock_post):
        # Mock file upload / submission
        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 202
        mock_post_resp.json.return_value = {"id": "task_hotapi_test_999", "status": "queued"}
        mock_post.return_value = mock_post_resp

        # Mock task polling & image download
        mock_poll_resp = MagicMock()
        mock_poll_resp.status_code = 200
        mock_poll_resp.json.return_value = {
            "id": "task_hotapi_test_999",
            "status": "succeeded",
            "output": {"images": [{"url": "https://cdn.hotapi.ai/test_output.png"}]}
        }

        mock_dl_resp = MagicMock()
        mock_dl_resp.status_code = 200
        mock_dl_resp.content = b"fake_hotapi_image_png_bytes"

        mock_get.side_effect = [mock_poll_resp, mock_dl_resp]

        img_bytes, pixel_size, cost = self.provider.generate(
            "z-image-spicy", "test spicy prompt", "1024x1024", "standard"
        )
        self.assertEqual(img_bytes, b"fake_hotapi_image_png_bytes")
        self.assertEqual(pixel_size, "1024x1024")
        self.assertEqual(cost, 0.024)
        self.assertTrue(mock_post.called)
        self.assertTrue(mock_get.called)

    def test_manager_dispatches_hotapi(self):
        self.assertIn("hotapi", self.manager.providers)

if __name__ == "__main__":
    unittest.main()
