import logging
import sqlite3
import threading
import time

from core.event_bus import event_bus
from services.base import BaseService


RESUMABLE_STATUSES = ("Paused", "Failed", "Cancelled")
ACTIVE_STATUSES = ("Pending", "Running")


class QueueService(BaseService):
    def __init__(self, db_service=None):
        super().__init__(db_service)
        self.consumer = None
        self.generation_service = None
        self._recovery_done = False
        self._consumer_lock = threading.Lock()
        self._shutting_down = False
        self._wake_event = threading.Event()
        self._last_error = None
        self._continuous_failures = 0

    def start_consumer(self, generation_service):
        self.generation_service = generation_service
        if not self._recovery_done:
            self.recover_interrupted_jobs()
            self._recovery_done = True
        self.ensure_consumer_running()

    def ensure_consumer_running(self, generation_service=None):
        if generation_service:
            self.generation_service = generation_service
            
        if self._shutting_down:
            return

        with self._consumer_lock:
            if self.consumer and self.consumer.is_alive():
                self._wake_event.set()
                return

            if self.generation_service:
                logging.info("[QUEUE SERVICE] Starting QueueConsumer worker thread...")
                self.consumer = QueueConsumer(self, self.generation_service)
                self.consumer.start()
                self._wake_event.set()

    def stop_consumer(self, timeout_seconds: float | None = 0.0) -> bool:
        self._shutting_down = True
        self._wake_event.set()
        with self._consumer_lock:
            if not self.consumer:
                return True
            self.consumer.stop()
            self._wake_event.set()
            timeout = None if timeout_seconds is None else max(0.0, timeout_seconds)
            self.consumer.join(timeout=timeout)
            return not self.consumer.is_alive()

    def get_consumer_status(self) -> str:
        if self._shutting_down:
            return "shutting_down"
        if self.consumer and self.consumer.is_alive():
            return "running"
        if self._continuous_failures > 5:
            return "faulted"
        return "stopped"

    def recover_interrupted_jobs(self) -> int:
        """Pause unfinished jobs; the user explicitly resumes them after restart."""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE jobs SET status = 'Paused' "
                "WHERE status IN ('Running', 'Pending');"
            )
            recovered_count = cursor.rowcount
            conn.commit()
            if recovered_count:
                logging.info(
                    "Paused %s interrupted/leftover queue job(s) from previous session.",
                    recovered_count,
                )
                event_bus.queue_updated.emit()
            return recovered_count
        except Exception as exc:
            logging.error("Failed to recover interrupted queue jobs: %s", exc)
            return 0
        finally:
            if conn is not None:
                conn.close()

    def add_job(
        self,
        project_id: int,
        prompt_jp: str,
        translation_rule: str,
        size: str,
        negative_prompt: str,
        quality: str,
        batch_count: int,
        model_id: str | None = None,
        provider: str | None = None,
        mode: str = "generate",
        image_path: str | None = None,
        mask_path: str | None = None,
        style_preset: str | None = None,
        expert_params: str | None = None,
    ) -> int:
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO jobs (
                    project_id, status, prompt_jp, prompt_en, style, size,
                    negative_prompt, quality, batch_count, completed_count,
                    model_id, provider, mode, image_path, mask_path,
                    style_preset, expert_params
                ) VALUES (?, 'Pending', ?, NULL, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    project_id,
                    prompt_jp,
                    translation_rule,
                    size,
                    negative_prompt,
                    quality,
                    max(1, int(batch_count)),
                    model_id,
                    provider,
                    mode,
                    image_path,
                    mask_path,
                    style_preset,
                    expert_params,
                ),
            )
            conn.commit()
            job_id = int(cursor.lastrowid)
        except Exception as exc:
            logging.error("Failed to add job to database queue: %s", exc)
            return -1
        finally:
            if conn is not None:
                conn.close()

        event_bus.job_added.emit(job_id)
        event_bus.queue_updated.emit()

        # Self-contained worker lifecycle management & wake signal
        self.ensure_consumer_running()
        return job_id

    def get_jobs(self) -> list:
        conn = None
        try:
            conn = self.get_connection()
            rows = conn.execute(
                """
                SELECT id, project_id, status, prompt_jp, style, size,
                       negative_prompt, quality, batch_count, completed_count,
                       model_id, provider, mode, image_path, mask_path,
                       style_preset, expert_params, created_at
                FROM jobs ORDER BY id ASC;
                """
            ).fetchall()
            return [dict(row) for row in rows]
        except Exception as exc:
            logging.error("Failed to fetch queue jobs: %s", exc)
            return []
        finally:
            if conn is not None:
                conn.close()

    def get_job(self, job_id: int) -> dict | None:
        conn = None
        try:
            conn = self.get_connection()
            row = conn.execute(
                "SELECT * FROM jobs WHERE id = ?;", (job_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            if conn is not None:
                conn.close()

    def update_job_status(
        self,
        job_id: int,
        status: str,
        expected_statuses: tuple[str, ...] | None = None,
    ) -> bool:
        conn = None
        try:
            conn = self.get_connection()
            if expected_statuses:
                placeholders = ",".join("?" for _ in expected_statuses)
                cursor = conn.execute(
                    f"UPDATE jobs SET status = ? WHERE id = ? AND status IN ({placeholders});",
                    (status, job_id, *expected_statuses),
                )
            else:
                cursor = conn.execute(
                    "UPDATE jobs SET status = ? WHERE id = ?;", (status, job_id)
                )
            conn.commit()
            changed = cursor.rowcount == 1
        except Exception as exc:
            logging.error("Failed to update job status: %s", exc)
            return False
        finally:
            if conn is not None:
                conn.close()
        if changed:
            event_bus.job_status_changed.emit(job_id, status)
            event_bus.queue_updated.emit()
        return changed

    def resume_job(self, job_id: int) -> bool:
        success = self.update_job_status(job_id, "Pending", RESUMABLE_STATUSES)
        if success:
            self.ensure_consumer_running()
        return success

    def delete_job(self, job_id: int) -> bool:
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.execute(
                "DELETE FROM jobs WHERE id = ? AND status != 'Running';", (job_id,)
            )
            conn.commit()
            deleted = cursor.rowcount == 1
        except Exception as exc:
            logging.error("Failed to delete job from queue: %s", exc)
            return False
        finally:
            if conn is not None:
                conn.close()
        if deleted:
            event_bus.queue_updated.emit()
        return deleted

    def cancel_next_pending_job(self) -> bool:
        conn = None
        try:
            conn = self.get_connection()
            conn.execute("BEGIN IMMEDIATE;")
            row = conn.execute(
                "SELECT id FROM jobs WHERE status = 'Pending' ORDER BY id ASC LIMIT 1;"
            ).fetchone()
            if not row:
                conn.rollback()
                return False
            job_id = int(row["id"])
            cursor = conn.execute(
                "UPDATE jobs SET status = 'Cancelled' "
                "WHERE id = ? AND status = 'Pending';",
                (job_id,),
            )
            conn.commit()
            cancelled = cursor.rowcount == 1
        except Exception as exc:
            if conn is not None:
                conn.rollback()
            logging.error("Failed to cancel waiting job: %s", exc)
            return False
        finally:
            if conn is not None:
                conn.close()
        if cancelled:
            event_bus.job_status_changed.emit(job_id, "Cancelled")
            event_bus.queue_updated.emit()
        return cancelled

    def claim_next_pending_job_with_status(self) -> tuple[dict | None, bool]:
        """Atomically transition one Pending job to Running and return (job, is_db_locked)."""
        max_attempts = 5
        for attempt in range(max_attempts):
            conn = None
            try:
                conn = self.get_connection()
                conn.execute("BEGIN IMMEDIATE;")
                row = conn.execute(
                    "SELECT * FROM jobs WHERE status = 'Pending' ORDER BY id ASC LIMIT 1;"
                ).fetchone()
                if not row:
                    conn.rollback()
                    return None, False
                job_id = int(row["id"])
                cursor = conn.execute(
                    "UPDATE jobs SET status = 'Running' "
                    "WHERE id = ? AND status = 'Pending';",
                    (job_id,),
                )
                if cursor.rowcount != 1:
                    conn.rollback()
                    return None, False
                conn.commit()
                result = dict(row)
                result["status"] = "Running"
                return result, False
            except (sqlite3.OperationalError, sqlite3.DatabaseError) as exc:
                if conn is not None:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                msg = str(exc).lower()
                if "locked" in msg or "busy" in msg:
                    if attempt < max_attempts - 1:
                        time.sleep(0.05 * (attempt + 1))
                        continue
                    logging.warning("SQLite DB is temporarily busy while claiming job: %s", exc)
                    return None, True
                logging.error("Database error claiming pending job: %s", exc)
                return None, False
            except Exception as exc:
                if conn is not None:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                logging.error("Failed to claim pending job: %s", exc)
                return None, False
            finally:
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass
        return None, True

    def claim_next_pending_job(self) -> dict | None:
        job, _ = self.claim_next_pending_job_with_status()
        return job

    def record_completed_item(self, job_id: int) -> bool:
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.execute(
                """
                UPDATE jobs
                SET completed_count = MIN(batch_count, completed_count + 1)
                WHERE id = ? AND status = 'Running';
                """,
                (job_id,),
            )
            conn.commit()
            return cursor.rowcount == 1
        except Exception as exc:
            logging.error("Failed to store job progress: %s", exc)
            return False
        finally:
            if conn is not None:
                conn.close()

    def has_active_jobs(self, project_id: int) -> bool:
        conn = None
        try:
            conn = self.get_connection()
            row = conn.execute(
                "SELECT 1 FROM jobs WHERE project_id = ? "
                "AND status IN ('Pending', 'Running') LIMIT 1;",
                (project_id,),
            ).fetchone()
            return row is not None
        finally:
            if conn is not None:
                conn.close()

    def has_pending_jobs(self) -> bool:
        conn = None
        try:
            conn = self.get_connection()
            row = conn.execute(
                "SELECT 1 FROM jobs WHERE status = 'Pending' LIMIT 1;"
            ).fetchone()
            return row is not None
        except Exception:
            return False
        finally:
            if conn is not None:
                conn.close()


class QueueConsumer(threading.Thread):
    def __init__(self, queue_service, generation_service):
        super().__init__(name="QueueConsumer", daemon=False)
        self.queue_service = queue_service
        self.generation_service = generation_service
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        logging.info("Queue Consumer Thread started.")
        backoff_delay = 0.1

        while not self._stop_event.is_set():
            job, is_db_locked = self.queue_service.claim_next_pending_job_with_status()
            if is_db_locked:
                time.sleep(backoff_delay)
                backoff_delay = min(1.0, backoff_delay * 1.5)
                continue

            backoff_delay = 0.1

            if not job:
                self.queue_service._wake_event.clear()
                if not self.queue_service.has_pending_jobs():
                    self.queue_service._wake_event.wait(0.5)
                continue

            # Per-job exception boundary: One bad job will not crash the worker thread
            job_id = None
            try:
                job_id = int(job["id"])
                logging.info("Consumer picked up job %s: %s", job_id, job.get("prompt_jp"))
                batch_count = max(1, int(job.get("batch_count") or 1))
                completed_count = max(0, int(job.get("completed_count") or 0))
                failed = False

                for idx in range(completed_count, batch_count):
                    if self._stop_event.is_set():
                        break
                    event_bus.status_updated.emit(
                        f"Generating job {job_id}: {idx + 1}/{batch_count}..."
                    )
                    event_bus.progress_updated.emit(int((idx / batch_count) * 100))

                    result = self.generation_service.generate_single(
                        project_id=job.get("project_id"),
                        prompt_jp=job.get("prompt_jp") or "",
                        translation_rule=job.get("style") or "Standard",
                        size=job.get("size") or "1024x1024",
                        negative_prompt=job.get("negative_prompt") or "",
                        quality=job.get("quality") or "standard",
                        model_id=job.get("model_id"),
                        mode=job.get("mode") or "generate",
                        image_path=job.get("image_path"),
                        mask_path=job.get("mask_path"),
                        style_preset=job.get("style_preset"),
                        expert_params=job.get("expert_params"),
                    )

                    if not result.get("success"):
                        failed = True
                        error = result.get("error", "Unknown generation failure")
                        logging.error("Job %s generation step failed: %s", job_id, error)
                        event_bus.status_updated.emit(f"Job {job_id} failed: {error}")
                        break

                    if not self.queue_service.record_completed_item(job_id):
                        failed = True
                        event_bus.status_updated.emit(
                            f"Job {job_id} failed while saving queue progress."
                        )
                        break
                    completed_count += 1
                    event_bus.image_generated.emit(result)

                if failed:
                    self.queue_service.update_job_status(
                        job_id, "Failed", expected_statuses=("Running",)
                    )
                elif completed_count >= batch_count:
                    self.queue_service.update_job_status(
                        job_id, "Completed", expected_statuses=("Running",)
                    )
                    event_bus.status_updated.emit("Job completed successfully!")
                    event_bus.progress_updated.emit(100)
                    event_bus.gallery_refresh_requested.emit()
                else:
                    self.queue_service.update_job_status(
                        job_id, "Paused", expected_statuses=("Running",)
                    )
                    event_bus.status_updated.emit(
                        f"Job {job_id} paused during application shutdown."
                    )
                self.queue_service._continuous_failures = 0
            except Exception as exc:
                self.queue_service._continuous_failures += 1
                self.queue_service._last_error = str(exc)
                logging.exception("Error while processing queue job %s", job_id)
                if job_id is not None:
                    self.queue_service.update_job_status(
                        job_id, "Failed", expected_statuses=("Running",)
                    )
                    event_bus.status_updated.emit(f"Job {job_id} failed: {exc}")

        logging.info("Queue Consumer Thread terminated.")

