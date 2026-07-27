import logging
import os
import shutil
import uuid

from services.base import BaseService


class GalleryService(BaseService):
    def delete_image_record(self, image_path: str) -> bool:
        """Delete DB record and files without losing files on a DB failure."""
        metadata_path = os.path.splitext(image_path)[0] + ".json"
        staged: list[tuple[str, str]] = []

        try:
            for original in (image_path, metadata_path):
                if not os.path.exists(original):
                    continue
                temporary = f"{original}.deleting-{uuid.uuid4().hex}.tmp"
                os.replace(original, temporary)
                staged.append((original, temporary))
        except OSError as exc:
            logging.error("Failed to stage files for deletion: %s", exc)
            self._restore_staged(staged)
            return False

        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.execute(
                "DELETE FROM images WHERE image_path = ?;", (image_path,)
            )
            if cursor.rowcount != 1:
                conn.rollback()
                self._restore_staged(staged)
                return False
            conn.commit()
        except Exception as exc:
            if conn is not None:
                conn.rollback()
            logging.error("Failed to delete DB record for %s: %s", image_path, exc)
            self._restore_staged(staged)
            return False
        finally:
            if conn is not None:
                conn.close()

        success = True
        for _original, temporary in staged:
            try:
                os.remove(temporary)
            except OSError as exc:
                success = False
                logging.error("Failed to remove staged file %s: %s", temporary, exc)
        return success

    @staticmethod
    def _restore_staged(staged: list[tuple[str, str]]):
        for original, temporary in reversed(staged):
            try:
                if os.path.exists(temporary):
                    os.replace(temporary, original)
            except OSError:
                logging.exception("Failed to restore %s after deletion rollback", original)

    def bulk_export(self, image_paths: list, export_dir: str) -> int:
        success_count = 0
        os.makedirs(export_dir, exist_ok=True)
        for source in image_paths:
            if not os.path.isfile(source):
                continue
            destination = os.path.join(export_dir, os.path.basename(source))
            try:
                shutil.copy2(source, destination)
                success_count += 1
            except OSError as exc:
                logging.error("Failed to export %s: %s", source, exc)
        return success_count
