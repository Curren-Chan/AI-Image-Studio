import logging
from services.base import BaseService

class ProjectService(BaseService):
    def __init__(self, db_service=None):
        super().__init__(db_service)
        self.active_project_id = None
        self.ensure_default_project()
        
    def ensure_default_project(self):
        """Ensures that at least one project exists in the database on startup."""
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM projects;")
                if cursor.fetchone()[0] == 0:
                    cursor.execute("INSERT INTO projects (name, description) VALUES (?, ?);",
                                   ("Default Project", "Default workspace for imported images"))
                    conn.commit()

                cursor.execute("SELECT id FROM projects ORDER BY id ASC LIMIT 1;")
                row = cursor.fetchone()
                if row:
                    self.active_project_id = row[0]
        except Exception as e:
            logging.error(f"Failed to setup default project: {e}")

    def create_project(self, name: str, description: str = "") -> int:
        try:
            with self.connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO projects (name, description) VALUES (?, ?);", (name, description))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logging.error(f"Failed to create project: {e}")
            raise e

    def get_projects(self) -> list:
        try:
            with self.connection() as conn:
                rows = conn.execute(
                    "SELECT id, name, description, created_at FROM projects ORDER BY name ASC;"
                ).fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logging.error(f"Failed to fetch projects: {e}")
            return []

    def set_active_project(self, project_id: int):
        self.active_project_id = project_id

    def get_active_project_id(self) -> int:
        if self.active_project_id is None:
            self.ensure_default_project()
        return self.active_project_id
        
    def delete_project(self, project_id: int):
        """Deletes a project. Note: images will cascade to NULL project_id in database."""
        try:
            with self.connection() as conn:
                conn.execute("DELETE FROM projects WHERE id = ?;", (project_id,))
                conn.commit()
            # If active project was deleted, reset active pointer
            if self.active_project_id == project_id:
                self.active_project_id = None
                self.ensure_default_project()
        except Exception as e:
            logging.error(f"Failed to delete project: {e}")
            raise e

    def get_active_project_name(self) -> str:
        active_id = self.get_active_project_id()
        try:
            with self.connection() as conn:
                row = conn.execute(
                    "SELECT name FROM projects WHERE id = ?;", (active_id,)
                ).fetchone()
            if row:
                return row[0]
            return "Unknown Project"
        except Exception as e:
            logging.error(f"Failed to fetch active project name: {e}")
            return "Default Project"
