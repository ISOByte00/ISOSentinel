"""
Repository for violations table.
"""
import sqlite3
from datetime import datetime
from typing import List, Optional
from database.models import Violation


class ViolationRepository:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def record_violation(self, violation: Violation) -> Violation:
        query = """
        INSERT INTO violations (
            study_session_id, rule_name, process_name, executable_path,
            process_hash, severity, action_taken, reason, detected_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        detected_at = violation.detected_at or datetime.now()
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (
                violation.study_session_id,
                violation.rule_name,
                violation.process_name,
                violation.executable_path,
                violation.process_hash,
                violation.severity,
                violation.action_taken,
                violation.reason,
                detected_at
            ))
            violation.id = cursor.lastrowid
            violation.detected_at = detected_at
            conn.commit()
        return violation

    def get_session_violations(self, session_id: int) -> List[Violation]:
        query = "SELECT * FROM violations WHERE study_session_id = ? ORDER BY id DESC"
        with self.db_manager.get_connection() as conn:
            rows = conn.execute(query, (session_id,)).fetchall()
            return [self._row_to_violation(r) for r in rows]

    def get_today_violations(self) -> List[Violation]:
        query = """
        SELECT * FROM violations
        WHERE date(detected_at) = date('now', 'localtime')
        ORDER BY id DESC
        """
        with self.db_manager.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [self._row_to_violation(r) for r in rows]

    def get_all_violations(self) -> List[Violation]:
        query = "SELECT * FROM violations ORDER BY id DESC"
        with self.db_manager.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [self._row_to_violation(r) for r in rows]

    def _parse_dt(self, val) -> Optional[datetime]:
        if val is None:
            return None
        if isinstance(val, datetime):
            return val
        if isinstance(val, str):
            return datetime.fromisoformat(val)
        return None

    def _row_to_violation(self, row: sqlite3.Row) -> Violation:
        detected_at = self._parse_dt(row["detected_at"])
        return Violation(
            id=row["id"],
            study_session_id=row["study_session_id"],
            rule_name=row["rule_name"],
            process_name=row["process_name"],
            executable_path=row["executable_path"],
            process_hash=row["process_hash"],
            severity=row["severity"],
            action_taken=row["action_taken"],
            reason=row["reason"],
            detected_at=detected_at
        )
