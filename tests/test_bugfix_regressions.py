import json
import os
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QCheckBox, QMessageBox

from api.client import ApiClient
from api.model_registry import MODEL_REGISTRY
from database.connection import DbConnectionManager
from database.import_helper import import_legacy_history
from database.schema import setup_schema
from services.gallery_service import GalleryService
from services.generation_service import GenerationService
from services.history_service import HistoryService
from services.image_gen.fal_provider import FalImageProvider
from services.queue_service import QueueService
from services.settings_service import SettingsService
from services.template_service import TemplateService
from tests import TEST_APP
from ui.panels.gallery_panel import GalleryPanel


class _ProjectService:
    def get_active_project_id(self):
        return 1


class _HistoryService:
    def get_history(self, **_kwargs):
        return []


class _DeleteCard:
    def __init__(self, path):
        self.image_path = path
        self.cb = QCheckBox()
        self.cb.setChecked(True)


class BugfixRegressionTests(unittest.TestCase):
    def _database(self, root):
        manager = DbConnectionManager(os.path.join(root, "test.db"))
        conn = manager.get_connection()
        setup_schema(conn)
        conn.close()
        return manager

    def _project(self, manager):
        conn = manager.get_connection()
        cursor = conn.execute(
            "INSERT INTO projects (name, description) VALUES ('Test', 'Test');"
        )
        conn.commit()
        project_id = int(cursor.lastrowid)
        conn.close()
        return project_id

    def test_schema_backfill_skips_non_object_json(self):
        with tempfile.TemporaryDirectory() as root:
            manager = self._database(root)
            project_id = self._project(manager)
            image_path = os.path.join(root, "legacy.png")
            open(image_path, "wb").close()
            with open(os.path.splitext(image_path)[0] + ".json", "w", encoding="utf-8") as handle:
                json.dump([], handle)
            conn = manager.get_connection()
            conn.execute(
                "INSERT INTO images (project_id, filename, image_path, model_id) "
                "VALUES (?, 'legacy.png', ?, NULL);",
                (project_id, image_path),
            )
            conn.commit()
            setup_schema(conn)
            conn.close()

    def test_atomic_queue_claim_and_state_guards(self):
        with tempfile.TemporaryDirectory() as root:
            manager = self._database(root)
            project_id = self._project(manager)
            queue = QueueService(manager)
            job_id = queue.add_job(
                project_id,
                "prompt",
                "Standard",
                "1024x1024",
                "",
                "standard",
                1,
                "openai-gpt-image-2",
            )
            barrier = threading.Barrier(3)
            claims = []

            def claim():
                barrier.wait()
                claims.append(queue.claim_next_pending_job())

            threads = [threading.Thread(target=claim) for _ in range(2)]
            for thread in threads:
                thread.start()
            barrier.wait()
            for thread in threads:
                thread.join(2)

            self.assertEqual(sum(item is not None for item in claims), 1)
            self.assertFalse(queue.delete_job(job_id))
            self.assertFalse(queue.resume_job(job_id))

    def test_failed_generation_is_not_marked_completed(self):
        with tempfile.TemporaryDirectory() as root:
            manager = self._database(root)
            project_id = self._project(manager)
            queue = QueueService(manager)

            class FailingGeneration:
                def generate_single(self, **_kwargs):
                    return {"success": False, "error": "expected failure"}

            queue.start_consumer(FailingGeneration())
            job_id = queue.add_job(
                project_id,
                "prompt",
                "Standard",
                "1024x1024",
                "",
                "standard",
                1,
                "openai-gpt-image-2",
            )
            deadline = time.monotonic() + 3
            status = None
            while time.monotonic() < deadline:
                status = queue.get_job(job_id)["status"]
                if status == "Failed":
                    break
                time.sleep(0.02)
            queue.stop_consumer(timeout_seconds=2)
            self.assertEqual(status, "Failed")

    def test_missing_edit_source_never_changes_to_text_generation(self):
        api_client = SimpleNamespace(
            image_model="gpt-image-2",
            mock_mode=True,
            api_key="",
            fal_key="",
            gemini_key="",
            xai_key="",
        )

        class Prompt:
            def set_settings_service(self, _settings):
                pass

        service = GenerationService(
            api_client,
            Prompt(),
            SimpleNamespace(),
            SimpleNamespace(),
            SimpleNamespace(),
            project_root=tempfile.gettempdir(),
        )
        result = service.generate_single(
            project_id=1,
            prompt_jp="edit",
            model_id="fal-qwen-image-2-edit",
            mode="edit",
            image_path="definitely-missing.png",
        )
        self.assertFalse(result["success"])
        self.assertIn("no longer exists", result["error"])

    def test_dimension_and_mock_allocation_limits(self):
        valid, _ = GenerationService.validate_size("4096x4096")
        invalid, error = GenerationService.validate_size("50000x50000")
        self.assertTrue(valid)
        self.assertFalse(invalid)
        self.assertIn("between", error)

    def test_deleted_project_is_saved_as_unlinked_history(self):
        with tempfile.TemporaryDirectory() as root:
            manager = self._database(root)
            project_id = self._project(manager)
            conn = manager.get_connection()
            conn.execute("DELETE FROM projects WHERE id = ?;", (project_id,))
            conn.commit()
            conn.close()
            history = HistoryService(manager)
            record_id = history.add_image_record(
                project_id,
                "image.png",
                os.path.join(root, "image.png"),
                "prompt",
                "prompt",
                "",
                "1024x1024",
                "Standard",
                "standard",
                0.0,
            )
            self.assertGreater(record_id, 0)
            conn = manager.get_connection()
            saved_project = conn.execute(
                "SELECT project_id FROM images WHERE id = ?;", (record_id,)
            ).fetchone()[0]
            conn.close()
            self.assertIsNone(saved_project)

    def test_db_delete_failure_restores_files(self):
        with tempfile.TemporaryDirectory() as root:
            image_path = os.path.join(root, "image.png")
            metadata_path = os.path.join(root, "image.json")
            open(image_path, "wb").close()
            with open(metadata_path, "w", encoding="utf-8") as handle:
                json.dump({}, handle)

            class BrokenDb:
                def get_connection(self):
                    raise OSError("locked")

            service = GalleryService(BrokenDb())
            self.assertFalse(service.delete_image_record(image_path))
            self.assertTrue(os.path.exists(image_path))
            self.assertTrue(os.path.exists(metadata_path))

    def test_api_key_removal_clears_environment_and_provider_fallback(self):
        with tempfile.TemporaryDirectory() as root:
            manager = self._database(root)
            old_value = os.environ.get("FAL_KEY")
            os.environ["FAL_KEY"] = "old-key"
            try:
                settings = SettingsService(manager, project_root=root)
                settings.update_fal_key("")
                client = ApiClient(api_key="other-key", fal_key="")
                client.update_fal_key("")
                provider = FalImageProvider(client)
                self.assertNotIn("FAL_KEY", os.environ)
                self.assertFalse(provider._setup_auth())
            finally:
                if old_value is None:
                    os.environ.pop("FAL_KEY", None)
                else:
                    os.environ["FAL_KEY"] = old_value

    def test_concurrent_settings_writes_keep_valid_json_and_all_keys(self):
        with tempfile.TemporaryDirectory() as root:
            settings = SettingsService(self._database(root), project_root=root)
            threads = [
                threading.Thread(
                    target=settings.save_setting, args=(f"thread_key_{index}", str(index))
                )
                for index in range(12)
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(3)
            with open(settings.settings_json_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            for index in range(12):
                self.assertEqual(data[f"thread_key_{index}"], str(index))

    def test_qwen_edit_uses_list_payload(self):
        arguments = {"prompt": "edit"}
        FalImageProvider._add_edit_source(
            arguments,
            "fal-ai/qwen-image-2/edit",
            "https://example.invalid/input.png",
        )
        self.assertEqual(
            arguments["image_urls"], ["https://example.invalid/input.png"]
        )
        self.assertNotIn("image_url", arguments)

    def test_image_extension_matches_content(self):
        self.assertEqual(
            GenerationService._detect_image_extension(b"\x89PNG\r\n\x1a\nrest"),
            ".png",
        )
        self.assertEqual(
            GenerationService._detect_image_extension(b"\xff\xd8\xffrest"),
            ".jpg",
        )
        self.assertEqual(
            GenerationService._detect_image_extension(b"RIFFxxxxWEBPrest"),
            ".webp",
        )

    def test_enabled_model_defaults_reference_registered_models(self):
        with tempfile.TemporaryDirectory() as root:
            settings = SettingsService(self._database(root), project_root=root)
            enabled = settings.defaults["enabled_models"].split(",")
            self.assertTrue(all(model_id in MODEL_REGISTRY for model_id in enabled))

    def test_empty_template_collection_stays_empty(self):
        with tempfile.TemporaryDirectory() as root:
            service = TemplateService(self._database(root), project_root=root)
            self.assertTrue(service.save_prompt_templates({}))
            self.assertEqual(service.get_prompt_templates(), {})

    def test_legacy_presets_are_removed_only_after_migration(self):
        with tempfile.TemporaryDirectory() as root:
            legacy_path = os.path.join(root, "presets.json")
            with open(legacy_path, "w", encoding="utf-8") as handle:
                json.dump({"Migrated": "content"}, handle)
            service = TemplateService(self._database(root), project_root=root)
            templates = service.get_prompt_templates()
            self.assertEqual(templates["Migrated"], "content")
            self.assertFalse(os.path.exists(legacy_path))
            self.assertEqual(service.get_prompt_templates()["Migrated"], "content")

    def test_incremental_import_recovers_new_output_when_db_is_not_empty(self):
        with tempfile.TemporaryDirectory() as root:
            manager = self._database(root)
            project_id = self._project(manager)
            conn = manager.get_connection()
            conn.execute(
                "INSERT INTO images (project_id, filename, image_path) "
                "VALUES (?, 'old.png', ?);",
                (project_id, os.path.join(root, "old.png")),
            )
            conn.commit()
            output_dir = os.path.join(root, "outputs")
            os.makedirs(output_dir)
            image_path = os.path.join(output_dir, "recovered.jpg")
            open(image_path, "wb").close()
            with open(os.path.join(output_dir, "recovered.json"), "w", encoding="utf-8") as handle:
                json.dump({"cost": None, "model_id": "openai-gpt-image-2"}, handle)
            import_legacy_history(conn, output_dir)
            recovered = conn.execute(
                "SELECT cost FROM images WHERE image_path = ?;", (image_path,)
            ).fetchone()
            conn.close()
            self.assertIsNotNone(recovered)
            self.assertEqual(recovered[0], 0.0)

    def test_gallery_bulk_delete_does_not_process_reentrant_events(self):
        calls = []

        class Gallery:
            def delete_image_record(inner_self, path):
                calls.append(path)
                if len(calls) == 1:
                    QTimer.singleShot(0, panel.refresh_gallery)
                return True

        coordinator = SimpleNamespace(
            project_service=_ProjectService(),
            history_service=_HistoryService(),
            gallery_service=Gallery(),
        )
        panel = GalleryPanel(coordinator)
        panel.cards = [_DeleteCard("one.png"), _DeleteCard("two.png")]
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes), patch.object(
            QMessageBox, "information"
        ), patch.object(QMessageBox, "warning"):
            panel.bulk_delete()
            TEST_APP.processEvents()
        self.assertEqual(calls, ["one.png", "two.png"])


if __name__ == "__main__":
    unittest.main()
