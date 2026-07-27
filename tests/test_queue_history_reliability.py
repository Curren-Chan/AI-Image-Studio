import json
import os
import tempfile
import threading
import time
import unittest

from database.connection import DbConnectionManager
from database.schema import setup_schema
from services.history_service import HistoryService
from services.queue_service import QueueService


class _BlockingGenerationService:
    def __init__(self):
        self.entered = threading.Event()
        self.release = threading.Event()

    def generate_single(self, **_kwargs):
        self.entered.set()
        self.release.wait(5.0)
        return {"success": True}


class QueueHistoryReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test.db")
        self.db_service = DbConnectionManager(self.db_path)
        conn = self.db_service.get_connection()
        setup_schema(conn)
        conn.close()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _insert_project(self) -> int:
        conn = self.db_service.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO projects (name, description) VALUES (?, ?);",
            ("Test Project", "Temporary test project"),
        )
        conn.commit()
        project_id = cursor.lastrowid
        conn.close()
        return project_id

    def _insert_job(self, project_id: int, status: str) -> int:
        conn = self.db_service.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO jobs (
                project_id, status, prompt_jp, style, size,
                negative_prompt, quality, batch_count, model_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                project_id,
                status,
                "test prompt",
                "Standard",
                "1024x1024",
                "",
                "standard",
                1,
                "openai-gpt-image-2",
            ),
        )
        conn.commit()
        job_id = cursor.lastrowid
        conn.close()
        return job_id

    def test_running_and_pending_jobs_are_paused_on_recovery(self):
        project_id = self._insert_project()
        job_id_running = self._insert_job(project_id, "Running")
        job_id_pending = self._insert_job(project_id, "Pending")
        queue_service = QueueService(self.db_service)

        recovered_count = queue_service.recover_interrupted_jobs()

        conn = self.db_service.get_connection()
        status_running = conn.execute(
            "SELECT status FROM jobs WHERE id = ?;", (job_id_running,)
        ).fetchone()[0]
        status_pending = conn.execute(
            "SELECT status FROM jobs WHERE id = ?;", (job_id_pending,)
        ).fetchone()[0]
        conn.close()
        self.assertEqual(recovered_count, 2)
        self.assertEqual(status_running, "Paused")
        self.assertEqual(status_pending, "Paused")

    def test_shutdown_keeps_non_daemon_worker_alive_until_provider_returns(self):
        project_id = self._insert_project()
        generation_service = _BlockingGenerationService()
        queue_service = QueueService(self.db_service)
        queue_service.start_consumer(generation_service)
        queue_service.add_job(
            project_id=project_id,
            prompt_jp="test prompt",
            translation_rule="Standard",
            size="1024x1024",
            negative_prompt="",
            quality="standard",
            batch_count=2,
            model_id="openai-gpt-image-2",
        )

        try:
            self.assertTrue(generation_service.entered.wait(2.0))
            started_at = time.perf_counter()
            stopped = queue_service.stop_consumer(timeout_seconds=0.05)
            elapsed = time.perf_counter() - started_at

            self.assertFalse(stopped)
            self.assertLess(elapsed, 0.5)
            self.assertFalse(queue_service.consumer.daemon)
        finally:
            generation_service.release.set()
            self.assertTrue(queue_service.stop_consumer(timeout_seconds=2.0))

        self.assertFalse(queue_service.consumer.is_alive())
        job = queue_service.get_job(1)
        self.assertEqual(job["status"], "Paused")
        self.assertEqual(job["completed_count"], 1)

    def test_model_id_round_trip_and_existing_json_backfill(self):
        project_id = self._insert_project()
        history_service = HistoryService(self.db_service)
        image_path = os.path.join(self.temp_dir.name, "existing.png")
        metadata_path = os.path.splitext(image_path)[0] + ".json"
        with open(image_path, "wb") as image_file:
            image_file.write(b"test")

        record_id = history_service.add_image_record(
            project_id=project_id,
            filename="existing.png",
            image_path=image_path,
            prompt_jp="prompt",
            prompt_en="prompt",
            negative_prompt="",
            size="1024x1024",
            style="Standard",
            quality="standard",
            cost=0.0,
            model_name="Qwen Image 2 Edit",
            provider="fal",
            model_id="fal-qwen-image-2-edit",
        )
        self.assertGreater(record_id, 0)
        history = history_service.get_history(project_id=project_id)
        self.assertEqual(
            history[0]["metadata"]["model_id"], "fal-qwen-image-2-edit"
        )

        conn = self.db_service.get_connection()
        conn.execute(
            "UPDATE images SET model_id = NULL WHERE id = ?;", (record_id,)
        )
        conn.commit()
        conn.close()
        with open(metadata_path, "w", encoding="utf-8") as metadata_file:
            json.dump({"model_id": "fal-qwen-image-2-edit"}, metadata_file)

        conn = self.db_service.get_connection()
        setup_schema(conn)
        restored_model_id = conn.execute(
            "SELECT model_id FROM images WHERE id = ?;", (record_id,)
        ).fetchone()[0]
        conn.close()
        self.assertEqual(restored_model_id, "fal-qwen-image-2-edit")


if __name__ == "__main__":
    unittest.main()
