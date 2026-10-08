import sqlite3
from config.settings import DB_PATH

def get_connection():
    """Veritabanı bağlantısı oluşturur ve döner."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Gerekli tablolar yoksa oluşturur."""
    conn = get_connection()
    cursor = conn.cursor()

    # Oturum Tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS study_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT,
            topic TEXT,
            planned_duration INTEGER,
            actual_duration INTEGER DEFAULT 0,
            status TEXT DEFAULT 'PLANNED',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

# İhlal Kayıtları Tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            process_name TEXT,
            process_path TEXT,
            file_hash TEXT,
            severity TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES study_sessions (id)
        )
    """)

    # Soru Verileri Tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS question_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            subject TEXT,
            topic TEXT,
            correct_count INTEGER DEFAULT 0,
            wrong_count INTEGER DEFAULT 0,
            empty_count INTEGER DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES study_sessions (id)
        )
    """)

    # Sistem Tarafından Öğrenilen Uygulama Hafızası
    cursor.execute("""
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
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Veritabanı tabloları başarıyla oluşturuldu.")