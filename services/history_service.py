import os
import json
import logging
from typing import Any
import os
import json
import logging
from typing import Any
from services.base import BaseService

class HistoryService(BaseService):
    def __init__(self, db_service=None):
        super().__init__(db_service)
        
    def cleanup_duplicate_records(self) -> int:
        """Removes duplicate image records from SQLite, keeping the row with the largest ID."""
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                # Delete duplicate records keeping the one with max(id)
                cursor.execute("""
                    DELETE FROM images 
                    WHERE id NOT IN (
                        SELECT MAX(id) 
                        FROM images 
                        GROUP BY lower(image_path)
                    );
                """)
                deleted_count = cursor.rowcount
                conn.commit()
                if deleted_count > 0:
                    logging.info(f"[DB CLEANUP] Cleaned up {deleted_count} duplicate image records.")
                return deleted_count
        except Exception as e:
            logging.error(f"[DB CLEANUP] Failed to cleanup duplicate image records: {e}")
            return 0

    def add_image_record(self, project_id: int | None, filename: str, image_path: str, prompt_jp: str, prompt_en: str, negative_prompt: str, size: str, style: str, quality: str, cost: float, model_name: str | None = None, provider: str | None = None, style_preset: str | None = None, expert_params: str | None = None, model_id: str | None = None) -> int:
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            if project_id is not None:
                exists = cursor.execute(
                    "SELECT 1 FROM projects WHERE id = ?;", (project_id,)
                ).fetchone()
                if not exists:
                    logging.warning(
                        "Project %s was deleted before history save; storing image unlinked.",
                        project_id,
                    )
                    project_id = None
            
            cursor.execute("""
                INSERT INTO images (project_id, filename, image_path, prompt_jp, prompt_en, negative_prompt, size, style, quality, cost, model_name, provider, style_preset, expert_params, model_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (project_id, filename, image_path, prompt_jp, prompt_en, negative_prompt, size, style, quality, cost, model_name, provider, style_preset, expert_params, model_id))
            conn.commit()
            image_id = cursor.lastrowid
            return image_id
        except Exception as e:
            logging.error(f"Failed to save image record in database: {e}")
            return -1
        finally:
            if conn is not None:
                conn.close()

    def get_history(self, project_id: int | None = None, search_query: str | None = None, favorite_only: bool = False, sort_order: str = "newest") -> list:
        """Retrieves image generation history from SQLite, matching filters, search queries, and sort order."""
        try:
            with self.connection() as conn:
                cursor = conn.cursor()

                sql = "SELECT id, project_id, filename, image_path, prompt_jp, prompt_en, negative_prompt, size, style, quality, cost, favorite, model_name, provider, model_id, style_preset, expert_params, created_at FROM images WHERE 1=1"
                params: list[Any] = []

                if project_id is not None:
                    sql += " AND project_id = ?"
                    params.append(project_id)

                if favorite_only:
                    sql += " AND favorite = 1"

                if search_query and search_query.strip():
                    sql += " AND (prompt_jp LIKE ? OR prompt_en LIKE ? OR style LIKE ? OR filename LIKE ? OR model_name LIKE ? OR provider LIKE ?)"
                    like_term = f"%{search_query.strip()}%"
                    params.extend([like_term] * 6)

                if sort_order == "oldest":
                    sql += " ORDER BY created_at ASC, id ASC;"
                elif sort_order == "favorite":
                    sql += " ORDER BY favorite DESC, created_at DESC, id DESC;"
                elif sort_order == "filename":
                    sql += " ORDER BY filename ASC, id ASC;"
                else:
                    sql += " ORDER BY created_at DESC, id DESC;"
                cursor.execute(sql, params)
                rows = cursor.fetchall()
            
            history = []
            for row in rows:
                d = dict(row)
                history.append({
                    "image_path": d["image_path"],
                    "metadata": {
                        "timestamp": d["created_at"],
                        "prompt_jp": d["prompt_jp"],
                        "prompt_en": d["prompt_en"],
                        "negative_prompt": d["negative_prompt"],
                        "size": d["size"],
                        "style": d["style"],
                        "quality": d["quality"],
                        "cost": self._safe_cost(d["cost"]),
                        "favorite": bool(d["favorite"]),
                        "filename": d["filename"],
                        "id": d["id"],
                        "model_name": d.get("model_name"),
                        "provider": d.get("provider"),
                        "model_id": d.get("model_id"),
                        "style_preset": d.get("style_preset"),
                        "expert_params": d.get("expert_params")
                    }
                })
            return history

        except Exception as e:
            logging.error(f"Failed to fetch image history: {e}")
            return []

    @staticmethod
    def _safe_cost(value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def toggle_favorite(self, image_path: str) -> bool:
        """Toggles the favorite state of an image in the database. Returns new state."""
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT favorite FROM images WHERE image_path = ?;", (image_path,))
                row = cursor.fetchone()
                if not row:
                    return False
                new_fav = 0 if row[0] else 1
                cursor.execute("UPDATE images SET favorite = ? WHERE image_path = ?;", (new_fav, image_path))
                conn.commit()
            
            # Also toggle JSON file if exists for compatibility
            base_name, _ = os.path.splitext(image_path)
            meta_path = f"{base_name}.json"
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    meta["favorite"] = bool(new_fav)
                    with open(meta_path, "w", encoding="utf-8") as f:
                        json.dump(meta, f, ensure_ascii=False, indent=4)
                except Exception:
                    pass
            return bool(new_fav)
        except Exception as e:
            logging.error(f"Failed to toggle favorite state: {e}")
            return False
