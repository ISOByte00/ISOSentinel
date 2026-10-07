from database.repositories.session_repository import SessionRepository
from database.models import StudySession
from restrictions.process_guard import scan_and_kill

class SessionController:
    def __init__(self):
        self.active_session_id = None
        self.status = "IDLE"
        self.repo = SessionRepository()

    def start_session(self, subject, topic, duration):
        """Yeni bir çalışma oturumu başlatır."""
        
        # 1. Modeli oluştur
        new_session = StudySession(
            id=None, 
            subject=subject, 
            topic=topic, 
            planned_duration=duration, 
            status='STUDYING'
        )
        
        # 2. Repository aracılığıyla veritabanına kaydet
        self.active_session_id = self.repo.create_session(new_session)
        self.status = "STUDYING"
        print(f"OTURUM BASLADI: {subject} - {topic} ({duration} dk) | ID: {self.active_session_id}")

    def check_environment(self):
        """Oturum devam ederken arka plan kısıtlamalarını kontrol eder."""
        if self.status == "STUDYING" and self.active_session_id:
            scan_and_kill(self.active_session_id)

    def stop_session(self):
        """Aktif oturumu bitirir."""
        if self.active_session_id:
            # Sadece Repository'ye durum güncellemesi gönder
            self.repo.update_session_status(self.active_session_id, 'COMPLETED')
            
            print("OTURUM BİTTİ.")
            self.status = "COMPLETED"
            self.active_session_id = None