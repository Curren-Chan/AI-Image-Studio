import sqlite3
import os
import threading

class DbConnectionManager:
    def __init__(self, db_path=None):
        if db_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(project_root, "database.db")
        self.db_path = os.path.abspath(db_path)
        self._pragma_lock = threading.Lock()
        self._wal_initialized = False
        
    def get_connection(self):
        """Returns a connection to SQLite database with WAL mode and foreign keys enabled."""
        conn = sqlite3.connect(self.db_path, timeout=2.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 2000;")
        with self._pragma_lock:
            if not self._wal_initialized:
                conn.execute("PRAGMA journal_mode = WAL;")
                conn.execute("PRAGMA synchronous = NORMAL;")
                self._wal_initialized = True
        return conn
