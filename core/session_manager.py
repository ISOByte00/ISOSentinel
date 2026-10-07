from database.database import get_connection
from restrictions.process_guard import scan_and_kill

class SessionController:
    def __init__(self):
        self.active_session_id = None
        self.status = "IDLE"

    def start_session(self, subject, topic, duration):
        """Yeni bir çalışma oturumu başlatır."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO study_sessions (subject, topic, planned_duration, status)
            VALUES (?, ?, ?, 'STUDYING')
        """, (subject, topic, duration))
        conn.commit()
        self.active_session_id = cursor.lastrowid
        self.status = "STUDYING"
        conn.close()
        print(f"OTURUM BASLADI: {subject} - {topic} ({duration} dk)")

    def check_environment(self):
        """Oturum devam ederken arka plan kısıtlamalarını kontrol eder."""
        if self.status == "STUDYING" and self.active_session_id:
            scan_and_kill(self.active_session_id)

    def stop_session(self):
        """Aktif oturumu bitirir."""
        if self.active_session_id:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE study_sessions SET status = 'COMPLETED' WHERE id = ?
            """, (self.active_session_id,))
            conn.commit()
            conn.close()
            print("OTURUM BİTTİ.")
            self.status = "COMPLETED"
            self.active_session_id = None