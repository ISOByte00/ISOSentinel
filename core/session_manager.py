from database.repositories.session_repository import SessionRepository
from database.models import StudySession
from core.event_bus import bus

class SessionController:
    def __init__(self):
        self.active_session_id = None
        self.status = "IDLE"
        self.repo = SessionRepository()

    def start_session(self, subject, topic, duration):
        new_session = StudySession(
            id=None, subject=subject, topic=topic, 
            planned_duration=duration, status='STUDYING'
        )
        self.active_session_id = self.repo.create_session(new_session)
        self.status = "STUDYING"
        
        print(f"OTURUM BASLADI: {subject} - {topic} ({duration} dk) | ID: {self.active_session_id}")
        
        # Olayı sisteme fırlat
        bus.publish("SESSION_STARTED", {"session_id": self.active_session_id})

    def stop_session(self):
        if self.active_session_id:
            self.repo.update_session_status(self.active_session_id, 'COMPLETED')
            
            print("OTURUM BİTTİ.")
            
            # Olayı sisteme fırlat
            bus.publish("SESSION_STOPPED", {"session_id": self.active_session_id})
            
            self.status = "COMPLETED"
            self.active_session_id = None