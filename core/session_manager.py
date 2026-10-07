from database.repositories.session_repository import SessionRepository
from database.models import StudySession
from core.event_bus import bus
from core.states import SessionState, VALID_TRANSITIONS, StateTransitionError

class SessionController:
    def __init__(self):
        self.active_session_id = None
        self.state = SessionState.IDLE
        self.repo = SessionRepository()

    def _change_state(self, new_state: SessionState):
        """Sistemin durumunu güvenlik kontrollerinden geçirerek değiştirir."""
        if new_state not in VALID_TRANSITIONS[self.state]:
            raise StateTransitionError(f"GECERSIZ DURUM GECISI: {self.state.name} -> {new_state.name}")
        
        old_state = self.state
        self.state = new_state
        print(f"[FSM] State Degisti: {old_state.name} -> {self.state.name}")
        
        # State değişimini tüm sisteme duyur
        bus.publish("STATE_CHANGED", {
            "old": old_state.name, 
            "new": self.state.name, 
            "session_id": self.active_session_id
        })

    def start_session(self, subject, topic, duration):
        """Yeni bir çalışma oturumu başlatır."""
        self._change_state(SessionState.STUDYING)
        
        new_session = StudySession(
            id=None, subject=subject, topic=topic, 
            planned_duration=duration, status=self.state.value
        )
        self.active_session_id = self.repo.create_session(new_session)
        
        print(f"OTURUM BASLADI: {subject} - {topic} ({duration} dk) | ID: {self.active_session_id}")
        bus.publish("SESSION_STARTED", {"session_id": self.active_session_id})

    def stop_session(self, interrupted=False):
        """Aktif oturumu bitirir veya yarıda kesildi (interrupted) olarak işaretler."""
        if self.active_session_id:
            # Normal bitiş mi yoksa çöktü/zorla durduruldu mu?
            next_state = SessionState.INTERRUPTED if interrupted else SessionState.COMPLETED
            self._change_state(next_state)
            
            self.repo.update_session_status(self.active_session_id, self.state.value)
            print(f"OTURUM BİTTİ. (Durum kayıt edildi: {self.state.value})")
            
            bus.publish("SESSION_STOPPED", {"session_id": self.active_session_id})
            
            # Oturum kapandıktan sonra sistemi tekrar Boşta (IDLE) durumuna çek
            self._change_state(SessionState.IDLE)
            self.active_session_id = None