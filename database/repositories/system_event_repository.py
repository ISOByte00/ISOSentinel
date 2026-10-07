"""
Repository for system_events table (Anti-Bypass & Audit).
"""
import sqlite3
from datetime import datetime
from typing import List, Optional
from database.models import SystemEvent


class SystemEventRepository:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def record_event(self, event_type: str, details: str = "") -> SystemEvent:
        query = """
        INSERT INTO system_events (event_type, details, recorded_at)
        VALUES (?, ?, ?)
        """
        recorded_at = datetime.now()
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (event_type, details, recorded_at))
            conn.commit()
            return SystemEvent(
                id=cursor.lastrowid,
                event_type=event_type,
                details=details,
                recorded_at=recorded_at
            )

    def get_last_event(self) -> Optional[SystemEvent]:
        query = "SELECT * FROM system_events ORDER BY id DESC LIMIT 1"
        with self.db_manager.get_connection() as conn:
            row = conn.execute(query).fetchone()
            if row:
                return self._row_to_event(row)
        return None

    def get_recent_events(self, limit: int = 50) -> List[SystemEvent]:
        query = "SELECT * FROM system_events ORDER BY id DESC LIMIT ?"
        with self.db_manager.get_connection() as conn:
            rows = conn.execute(query, (limit,)).fetchall()
            return [self._row_to_event(r) for r in rows]

    def _parse_dt(self, val) -> Optional[datetime]:
        if val is None:
            return None
        if isinstance(val, datetime):
            return val
        if isinstance(val, str):
            return datetime.fromisoformat(val)
        return None

    def _row_to_event(self, row: sqlite3.Row) -> SystemEvent:
        recorded_at = self._parse_dt(row["recorded_at"])
        return SystemEvent(
            id=row["id"],
            event_type=row["event_type"],
            details=row["details"] or "",
            recorded_at=recorded_at
        )
