from database.database import get_connection
from database.models import Violation, ProcessCacheItem

class GuardRepository:
    def __init__(self):
        self.conn = get_connection()

    def get_connection(self):
        return get_connection()

    def create_tables(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS process_cache (
                    process_name TEXT PRIMARY KEY,
                    file_hash TEXT,
                    status TEXT,
                    original_filename TEXT,
                    product_name TEXT,
                    company_name TEXT,
                    file_size INTEGER,
                    parent_process TEXT
                )
            ''')
            conn.commit()

    def log_violation(self, violation: Violation):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO violations (session_id, process_name, process_path, file_hash, severity)
            VALUES (?, ?, ?, ?, ?)
        """, (violation.session_id, violation.process_name, violation.process_path, violation.file_hash, violation.severity))
        self.conn.commit()

    def get_cached_item(self, exe_path: str) -> dict:
        """Cache kaydını hash'i ile birlikte döndürür (Stale Cache Bypass'ı engellemek için)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT status, file_hash FROM process_cache WHERE process_name = ?', (exe_path,))
            row = cursor.fetchone()
            if row:
                return {"status": row[0], "file_hash": row[1]}
            return None

    def set_cached_status(self, item: ProcessCacheItem):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO process_cache 
                (process_name, file_hash, status, original_filename, product_name, company_name, file_size, parent_process)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (item.process_name, item.file_hash, item.status, item.original_filename, 
                  item.product_name, item.company_name, item.file_size, item.parent_process))
            conn.commit()

    def check_if_hash_is_blocked(self, file_hash: str) -> bool:
        """Dosyanın adı değişmiş olsa bile, Hash (parmak izini) daha önce yasaklanmış mı diye bakar."""
        if not file_hash:
            return False
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT status FROM process_cache WHERE file_hash = ? AND status = "BLOCKED"', (file_hash,))
            return cursor.fetchone() is not None