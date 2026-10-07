from database.database import get_connection
from database.models import Violation, ProcessCacheItem

class GuardRepository:
    def __init__(self):
        self.conn = get_connection()

    def log_violation(self, violation: Violation):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO violations (session_id, process_name, process_path, file_hash, severity)
            VALUES (?, ?, ?, ?, ?)
        """, (violation.session_id, violation.process_name, violation.process_path, violation.file_hash, violation.severity))
        self.conn.commit()

    def get_cached_status(self, process_name: str) -> str:
        cursor = self.conn.cursor()
        cursor.execute("SELECT status FROM process_cache WHERE process_name = ?", (process_name,))
        row = cursor.fetchone()
        return row['status'] if row else None

    def set_cached_status(self, cache_item: ProcessCacheItem):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO process_cache (process_name, file_hash, status, last_checked)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (cache_item.process_name, cache_item.file_hash, cache_item.status))
        self.conn.commit()