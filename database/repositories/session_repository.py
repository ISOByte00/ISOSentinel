from database.database import get_connection
from database.models import StudySession

class SessionRepository:
    def __init__(self):
        self.conn = get_connection()

    def create_session(self, session: StudySession) -> int:
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO study_sessions (subject, topic, planned_duration, status)
            VALUES (?, ?, ?, ?)
        """, (session.subject, session.topic, session.planned_duration, session.status))
        self.conn.commit()
        session.id = cursor.lastrowid
        return session.id

    def update_session_status(self, session_id: int, status: str):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE study_sessions SET status = ? WHERE id = ?
        """, (status, session_id))
        self.conn.commit()

    def update_actual_duration(self, session_id: int, duration: int):
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE study_sessions SET actual_duration = ? WHERE id = ?
        """, (duration, session_id))
        self.conn.commit()

    def get_session(self, session_id: int) -> StudySession:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM study_sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        if row:
            return StudySession(**dict(row))
        return None