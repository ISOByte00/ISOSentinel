"""
Database connection and schema management for SQLite (guardian.db).
"""
import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS study_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    topic TEXT NOT NULL,
    planned_duration_minutes INTEGER NOT NULL,
    actual_duration_minutes INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    status TEXT NOT NULL CHECK (status IN ('PREPARING', 'STUDY', 'BREAK', 'COMPLETED', 'INTERRUPTED', 'RECOVERY', 'ERROR')),
    interruptions_count INTEGER DEFAULT 0,
    completion_rate REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS pomodoro_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    study_session_id INTEGER NOT NULL,
    sequence_number INTEGER NOT NULL,
    segment_type TEXT NOT NULL CHECK (segment_type IN ('STUDY', 'BREAK')),
    planned_minutes INTEGER NOT NULL,
    actual_minutes INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    status TEXT NOT NULL CHECK (status IN ('RUNNING', 'COMPLETED', 'INTERRUPTED')),
    FOREIGN KEY (study_session_id) REFERENCES study_sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS question_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    study_session_id INTEGER,
    exam_type TEXT NOT NULL CHECK (exam_type IN ('TYT', 'AYT')),
    subject TEXT NOT NULL,
    topic TEXT NOT NULL,
    total_questions INTEGER NOT NULL,
    correct_count INTEGER NOT NULL,
    wrong_count INTEGER NOT NULL,
    empty_count INTEGER NOT NULL,
    net_score REAL NOT NULL,
    accuracy_rate REAL NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (study_session_id) REFERENCES study_sessions(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    study_session_id INTEGER,
    rule_name TEXT NOT NULL,
    process_name TEXT NOT NULL,
    executable_path TEXT,
    process_hash TEXT,
    severity TEXT NOT NULL DEFAULT 'HIGH',
    action_taken TEXT NOT NULL DEFAULT 'kill',
    reason TEXT NOT NULL,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (study_session_id) REFERENCES study_sessions(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS system_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL CHECK (event_type IN ('STARTED', 'HEARTBEAT', 'CLEAN_EXIT', 'UNEXPECTED_SHUTDOWN', 'CLOCK_CHANGED', 'GUARD_CRASH')),
    details TEXT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sessions_status ON study_sessions(status);
CREATE INDEX IF NOT EXISTS idx_violations_session ON violations(study_session_id);
CREATE INDEX IF NOT EXISTS idx_question_batches_subject ON question_batches(subject, topic);
CREATE INDEX IF NOT EXISTS idx_system_events_type ON system_events(event_type, recorded_at);
"""


class DatabaseManager:
    """Manages SQLite database connections and schema creation."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """Returns a configured SQLite connection."""
        conn = sqlite3.connect(
            str(self.db_path),
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def initialize(self):
        """Creates tables, indices and applies pragmas."""
        logger.info(f"Initializing database at {self.db_path}")
        with self.get_connection() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()
        logger.info("Database schema initialized successfully.")