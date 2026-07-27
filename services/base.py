from contextlib import contextmanager


class BaseService:
    def __init__(self, db_service=None):
        self.db_service = db_service
        
    def get_connection(self):
        if self.db_service:
            return self.db_service.get_connection()
        raise RuntimeError("Database service not initialized in BaseService.")

    @contextmanager
    def connection(self):
        conn = self.get_connection()
        try:
            yield conn
        finally:
            conn.close()
