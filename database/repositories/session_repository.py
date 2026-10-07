"""
Repository for study_sessions and pomodoro_sessions.
"""
import sqlite3
from datetime import datetime
from typing import List, Optional
from database.models import StudySession, PomodoroSession


class SessionRepository:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def create_session(self, session: StudySession) -> StudySession:
        query = """
        INSERT INTO study_sessions (subject, topic, planned_duration_minutes, actual_duration_minutes, started_at, status, interruptions_count, completion_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        started_at = session.started_at or datetime.now()
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (
                session.subject,
                session.topic,
                session.planned_duration_minutes,
                session.actual_duration_minutes,
                started_at,
                session.status,
                session.interruptions_count,
                session.completion_rate
            ))
            session.id = cursor.lastrowid
            session.started_at = started_at
            conn.commit()
        return session

    def update_session(self, session: StudySession):
        query = """
        UPDATE study_sessions
        SET subject = ?, topic = ?, planned_duration_minutes = ?, actual_duration_minutes = ?,
            started_at = ?, ended_at = ?, status = ?, interruptions_count = ?, completion_rate = ?
        WHERE id = ?
        """
        with self.db_manager.get_connection() as conn:
            conn.execute(query, (
                session.subject,
                session.topic,
                session.planned_duration_minutes,
                session.actual_duration_minutes,
                session.started_at,
                session.ended_at,
                session.status,
                session.interruptions_count,
                session.completion_rate,
                session.id
            ))
            conn.commit()

    def get_session_by_id(self, session_id: int) -> Optional[StudySession]:
        query = "SELECT * FROM study_sessions WHERE id = ?"
        with self.db_manager.get_connection() as conn:
            row = conn.execute(query, (session_id,)).fetchone()
            if row:
                return self._row_to_session(row)
        return None

    def get_unfinished_session(self) -> Optional[StudySession]:
        """Returns the most recent active/unfinished session (e.g. after crash)."""
        query = """
        SELECT * FROM study_sessions
        WHERE status IN ('PREPARING', 'STUDY', 'BREAK')
        ORDER BY id DESC LIMIT 1
        """
        with self.db_manager.get_connection() as conn:
            row = conn.execute(query).fetchone()
            if row:
                return self._row_to_session(row)
        return None

    def get_today_sessions(self) -> List[StudySession]:
        query = """
        SELECT * FROM study_sessions
        WHERE date(started_at) = date('now', 'localtime')
        ORDER BY id DESC
        """
        with self.db_manager.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [self._row_to_session(r) for r in rows]

    def create_pomodoro_session(self, pomodoro: PomodoroSession) -> PomodoroSession:
        query = """
        INSERT INTO pomodoro_sessions (study_session_id, sequence_number, segment_type, planned_minutes, actual_minutes, started_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        started_at = pomodoro.started_at or datetime.now()
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (
                pomodoro.study_session_id,
                pomodoro.sequence_number,
                pomodoro.segment_type,
                pomodoro.planned_minutes,
                pomodoro.actual_minutes,
                started_at,
                pomodoro.status
            ))
            pomodoro.id = cursor.lastrowid
            pomodoro.started_at = started_at
            conn.commit()
        return pomodoro

    def update_pomodoro_session(self, pomodoro: PomodoroSession):
        query = """
        UPDATE pomodoro_sessions
        SET sequence_number = ?, segment_type = ?, planned_minutes = ?, actual_minutes = ?,
            started_at = ?, ended_at = ?, status = ?
        WHERE id = ?
        """
        with self.db_manager.get_connection() as conn:
            conn.execute(query, (
                pomodoro.sequence_number,
                pomodoro.segment_type,
                pomodoro.planned_minutes,
                pomodoro.actual_minutes,
                pomodoro.started_at,
                pomodoro.ended_at,
                pomodoro.status,
                pomodoro.id
            ))
            conn.commit()

    def _parse_dt(self, val) -> Optional[datetime]:
        if val is None:
            return None
        if isinstance(val, datetime):
            return val
        if isinstance(val, str):
            return datetime.fromisoformat(val)
        return None

    def _row_to_session(self, row: sqlite3.Row) -> StudySession:
        started_at = self._parse_dt(row["started_at"])
        ended_at = self._parse_dt(row["ended_at"])
        return StudySession(
            id=row["id"],
            subject=row["subject"],
            topic=row["topic"],
            planned_duration_minutes=row["planned_duration_minutes"],
            actual_duration_minutes=row["actual_duration_minutes"],
            started_at=started_at,
            ended_at=ended_at,
            status=row["status"],
            interruptions_count=row["interruptions_count"],
            completion_rate=row["completion_rate"]
        )
