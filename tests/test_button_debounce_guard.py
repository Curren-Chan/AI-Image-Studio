# -*- coding: utf-8 -*-
import os
import sys
import tempfile
import unittest

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database.connection import DbConnectionManager
from database.schema import setup_schema
from services.queue_service import QueueService


class ButtonDebounceAndQueueGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.temp_dir.name, "test_guard.db")
        self.db_service = DbConnectionManager(db_path)
        conn = self.db_service.get_connection()
        setup_schema(conn)
        conn.execute("INSERT OR IGNORE INTO projects (id, name, description) VALUES (1, 'Test Project', 'Test');")
        conn.commit()
        conn.close()
        self.queue_service = QueueService(self.db_service)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_queue_deduplication_guard_prevents_duplicate_pending_jobs(self):
        job1_id = self.queue_service.add_job(
            project_id=1,
            prompt_jp="テスト用プロンプト",
            translation_rule="Standard",
            size="1024x1024",
            negative_prompt="bad quality",
            quality="standard",
            batch_count=1,
            model_id="openai-gpt-image-2",
        )
        self.assertGreater(job1_id, 0)

        # Immediate duplicate submission
        job2_id = self.queue_service.add_job(
            project_id=1,
            prompt_jp="テスト用プロンプト",
            translation_rule="Standard",
            size="1024x1024",
            negative_prompt="bad quality",
            quality="standard",
            batch_count=1,
            model_id="openai-gpt-image-2",
        )
        # Should return the existing pending job ID without creating a new duplicate
        self.assertEqual(job1_id, job2_id)

        jobs = self.queue_service.get_jobs()
        pending_jobs = [j for j in jobs if j["status"] == "Pending"]
        self.assertEqual(len(pending_jobs), 1)

    def test_queue_allows_different_prompts(self):
        job1_id = self.queue_service.add_job(
            project_id=1,
            prompt_jp="プロンプトA",
            translation_rule="Standard",
            size="1024x1024",
            negative_prompt="",
            quality="standard",
            batch_count=1,
            model_id="openai-gpt-image-2",
        )
        job2_id = self.queue_service.add_job(
            project_id=1,
            prompt_jp="プロンプトB",
            translation_rule="Standard",
            size="1024x1024",
            negative_prompt="",
            quality="standard",
            batch_count=1,
            model_id="openai-gpt-image-2",
        )
        self.assertNotEqual(job1_id, job2_id)

        jobs = self.queue_service.get_jobs()
        pending_jobs = [j for j in jobs if j["status"] == "Pending"]
        self.assertEqual(len(pending_jobs), 2)


if __name__ == "__main__":
    unittest.main()
