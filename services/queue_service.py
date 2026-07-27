import logging
import threading

from core.event_bus import event_bus
from services.base import BaseService


RESUMABLE_STATUSES = ("Paused", "Failed", "Cancelled")
ACTIVE_STATUSES = ("Pending", "Running")


class QueueService(BaseService):
    def __init__(self, db_service=None):
        super().__init__(db_service)
        self.consumer = None
        self._recovery_done = False

    def start_consumer(self, generation_service):
        if self.consumer and self.consumer.is_alive():
            return
        if not self._recovery_done:
            self.recover_interrupted_jobs()
            self._recovery_done = True
        self.consumer = QueueConsumer(self, generation_service)
        self.consumer.start()

    def stop_consumer(self, timeout_seconds: float | None = 0.0) -> bool:
        if not self.consumer:
            return True
        self.consumer.stop()
        timeout = None if timeout_seconds is None else max(0.0, timeout_seconds)
        self.consumer.join(timeout=timeout)
        return not self.consumer.is_alive()

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
        return self.update_job_status(job_id, "Pending", RESUMABLE_STATUSES)

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

    def claim_next_pending_job(self) -> dict | None:
        """Atomically transition one Pending job to Running and return it."""
        conn = None
        try:
            conn = self.get_connection()
            conn.execute("BEGIN IMMEDIATE;")
            row = conn.execute(
                "SELECT * FROM jobs WHERE status = 'Pending' ORDER BY id ASC LIMIT 1;"
            ).fetchone()
            if not row:
                conn.rollback()
                return None
            job_id = int(row["id"])
            cursor = conn.execute(
                "UPDATE jobs SET status = 'Running' "
                "WHERE id = ? AND status = 'Pending';",
                (job_id,),
            )
            if cursor.rowcount != 1:
                conn.rollback()
                return None
            conn.commit()
            result = dict(row)
            result["status"] = "Running"
            return result
        except Exception as exc:
            if conn is not None:
                conn.rollback()
            logging.error("Failed to claim pending job: %s", exc)
            return None
        finally:
            if conn is not None:
                conn.close()

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


class QueueConsumer(threading.Thread):
    def __init__(self, queue_service, generation_service):
        # A non-daemon worker prevents Python/Qt teardown while native provider
        # code is still using signals, SQLite, or output files.
        super().__init__(name="QueueConsumer", daemon=False)
        self.queue_service = queue_service
        self.generation_service = generation_service
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        logging.info("Queue Consumer Thread started.")
        while not self._stop_event.is_set():
            job = self.queue_service.claim_next_pending_job()
            if not job:
                self._stop_event.wait(0.25)
                continue

            job_id = int(job["id"])
            logging.info("Consumer picked up job %s: %s", job_id, job["prompt_jp"])
            batch_count = max(1, int(job.get("batch_count") or 1))
            completed_count = max(0, int(job.get("completed_count") or 0))
            failed = False

            try:
                for idx in range(completed_count, batch_count):
                    if self._stop_event.is_set():
                        break
                    event_bus.status_updated.emit(
                        f"Generating job {job_id}: {idx + 1}/{batch_count}..."
                    )
                    event_bus.progress_updated.emit(int((idx / batch_count) * 100))

                    result = self.generation_service.generate_single(
                        project_id=job["project_id"],
                        prompt_jp=job["prompt_jp"] or "",
                        translation_rule=job["style"] or "Standard",
                        size=job["size"] or "1024x1024",
                        negative_prompt=job["negative_prompt"] or "",
                        quality=job["quality"] or "standard",
                        model_id=job["model_id"],
                        mode=job["mode"] or "generate",
                        image_path=job["image_path"],
                        mask_path=job["mask_path"],
                        style_preset=job["style_preset"],
                        expert_params=job["expert_params"],
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
            except Exception as exc:
                logging.exception("Error while processing queue job %s", job_id)
                self.queue_service.update_job_status(
                    job_id, "Failed", expected_statuses=("Running",)
                )
                event_bus.status_updated.emit(f"Job {job_id} failed: {exc}")

        logging.info("Queue Consumer Thread terminated.")
