import sqlite3
from database.database import get_connection
from database.models import Violation, ProcessCacheItem

class GuardRepository:
    def __init__(self, db_path: str = None, connection=None):
        self.db_path = db_path
        self._custom_conn = connection

    @property
    def conn(self):
        return self.get_connection()

    def get_connection(self):
        if self._custom_conn is not None:
            return self._custom_conn
        if self.db_path:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
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
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS violations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    process_name TEXT,
                    process_path TEXT,
                    file_hash TEXT,
                    severity TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
        self.migrate_cache_statuses()

    def migrate_cache_statuses(self):
        """Eski veritabanlarındaki BLOCKED ve ALLOWED durumlarını yeni BLOCK ve ALLOW formatına dönüştürür."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE process_cache SET status = 'BLOCK' WHERE status = 'BLOCKED'")
            cursor.execute("UPDATE process_cache SET status = 'ALLOW' WHERE status = 'ALLOWED'")
            conn.commit()

    def log_violation(self, violation: Violation):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO violations (session_id, process_name, process_path, file_hash, severity)
                VALUES (?, ?, ?, ?, ?)
            """, (violation.session_id, violation.process_name, violation.process_path, violation.file_hash, violation.severity))
            conn.commit()

    def get_cached_item(self, exe_path: str) -> dict:
        """Cache kaydını hash'i ile birlikte döndürür (Stale Cache Bypass'ı engellemek için)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT status, file_hash FROM process_cache WHERE process_name = ?', (exe_path,))
            row = cursor.fetchone()
            if row:
                raw_status = row[0]
                # Eski kayıtlardan gelebilecek BLOCKED / ALLOWED durumlarını normalize et
                if raw_status in ("BLOCK", "BLOCKED"):
                    norm_status = "BLOCK"
                elif raw_status in ("ALLOW", "ALLOWED"):
                    norm_status = "ALLOW"
                else:
                    norm_status = raw_status
                return {"status": norm_status, "file_hash": row[1]}
            return None

    def set_cached_status(self, item: ProcessCacheItem):
        # Kaydederken her zaman yeni standart durum formatını kullan (BLOCK / ALLOW)
        norm_status = "BLOCK" if item.status in ("BLOCK", "BLOCKED") else ("ALLOW" if item.status in ("ALLOW", "ALLOWED") else item.status)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO process_cache 
                (process_name, file_hash, status, original_filename, product_name, company_name, file_size, parent_process)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (item.process_name, item.file_hash, norm_status, item.original_filename, 
                  item.product_name, item.company_name, item.file_size, item.parent_process))
            conn.commit()

    def check_if_hash_is_blocked(self, file_hash: str) -> bool:
        """Dosyanın adı veya konumu değişmiş olsa bile, Hash (parmak izi) daha önce yasaklanmış mı diye bakar."""
        if not file_hash:
            return False
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT status FROM process_cache WHERE file_hash = ? AND status IN ("BLOCK", "BLOCKED")', (file_hash,))
            return cursor.fetchone() is not None