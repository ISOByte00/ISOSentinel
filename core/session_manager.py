from database.repositories.session_repository import SessionRepository
from database.models import StudySession
from core.event_bus import bus
from core.states import SessionState, VALID_TRANSITIONS, StateTransitionError
from core.recovery import RecoveryManager

class SessionController:
    def __init__(self):
        self.active_session_id = None
        self.state = SessionState.IDLE
        self.repo = SessionRepository()

    def _change_state(self, new_state: SessionState):
        if new_state not in VALID_TRANSITIONS[self.state]:
            raise StateTransitionError(f"GECERSIZ DURUM GECISI: {self.state.name} -> {new_state.name}")
        
        old_state = self.state
        self.state = new_state
        print(f"[FSM] State Degisti: {old_state.name} -> {self.state.name}")
        
        bus.publish("STATE_CHANGED", {
            "old": old_state.name, 
            "new": self.state.name, 
            "session_id": self.active_session_id
        })

    def start_session(self, subject, topic, duration):
        self._change_state(SessionState.STUDYING)
        
        new_session = StudySession(
            id=None, subject=subject, topic=topic, 
            planned_duration=duration, status=self.state.value
        )
        self.active_session_id = self.repo.create_session(new_session)
        
        print(f"OTURUM BASLADI: {subject} - {topic} ({duration} dk) | ID: {self.active_session_id}")
        
        # Olayı sisteme fırlat
        bus.publish("SESSION_STARTED", {"session_id": self.active_session_id})
        
        # Kurtarma (Recovery) dosyasını ilk süresiyle oluştur
        RecoveryManager.save_state(self.active_session_id, subject, topic, duration * 60)

    def stop_session(self, interrupted=False):
        if self.active_session_id:
            next_state = SessionState.INTERRUPTED if interrupted else SessionState.COMPLETED
            self._change_state(next_state)
            
            self.repo.update_session_status(self.active_session_id, self.state.value)
            print(f"OTURUM BİTTİ. (Durum kayıt edildi: {self.state.value})")
            
            bus.publish("SESSION_STOPPED", {"session_id": self.active_session_id})
            
            self._change_state(SessionState.IDLE)
            self.active_session_id = None
            
            # Temiz bir şekilde kapandığı için kurtarma dosyasına gerek kalmadı, sil!
            RecoveryManager.clear_state()

    def resume_session(self, session_id):
        """Çökmüş bir oturumu veritabanında yeni kayıt açmadan ayağa kaldırır."""
        self.active_session_id = session_id
        self._change_state(SessionState.STUDYING)
        
        print(f"OTURUM KURTARILDI: ID: {self.active_session_id}")
        
        # Olayı sisteme fırlat (Guard tekrar çalışmaya başlasın)
        bus.publish("SESSION_STARTED", {"session_id": self.active_session_id})

    def mark_as_interrupted(self, session_id):
        """Kullanıcı kurtarmayı reddederse oturumu yarıda kesildi olarak kaydeder."""
        self.repo.update_session_status(session_id, SessionState.INTERRUPTED.value)
        print(f"OTURUM İPTAL EDİLDİ (Kurtarılmadı): ID: {session_id}")