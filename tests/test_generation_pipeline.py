import json
import os
import tempfile
import unittest

from core.coordinator import Coordinator


class GenerationPipelineTests(unittest.TestCase):
    def test_mock_generation_uses_isolated_database_and_outputs(self):
        with tempfile.TemporaryDirectory() as project_root:
            coordinator = Coordinator(
                project_root=project_root,
                start_consumer=False,
                load_plugins=False,
            )
            coordinator.api_client.mock_mode = True
            project_id = coordinator.project_service.get_active_project_id()

            result = coordinator.generation_service.generate_single(
                project_id=project_id,
                prompt_jp="テスト用の青い瞳の少女のイラスト",
                translation_rule="Standard",
                size="512x512",
                quality="standard",
                model_id="openai-gpt-image-2",
            )

            self.assertTrue(result["success"], result.get("error"))
            image_path = result["image_path"]
            metadata_path = os.path.splitext(image_path)[0] + ".json"
            self.assertTrue(image_path.startswith(project_root))
            self.assertTrue(os.path.exists(image_path))
            self.assertTrue(os.path.exists(metadata_path))
            with open(metadata_path, "r", encoding="utf-8") as handle:
                metadata = json.load(handle)
            self.assertEqual(metadata["model_id"], "openai-gpt-image-2")

            conn = coordinator.db_service.get_connection()
            try:
                row = conn.execute(
                    "SELECT id FROM images WHERE image_path = ?;", (image_path,)
                ).fetchone()
            finally:
                conn.close()
            self.assertIsNotNone(row)


if __name__ == "__main__":
    unittest.main()
