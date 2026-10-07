from enum import Enum

class SessionState(Enum):
    IDLE = "IDLE"
    STUDYING = "STUDYING"
    BREAK = "BREAK"
    COMPLETED = "COMPLETED"
    INTERRUPTED = "INTERRUPTED"

# Hangi durumdan hangi durumlara geçilebileceğinin katı kuralları (FSM Transitions)
VALID_TRANSITIONS = {
    SessionState.IDLE: [SessionState.STUDYING],
    SessionState.STUDYING: [SessionState.COMPLETED, SessionState.INTERRUPTED, SessionState.BREAK],
    SessionState.BREAK: [SessionState.STUDYING, SessionState.COMPLETED],
    SessionState.COMPLETED: [SessionState.IDLE],
    SessionState.INTERRUPTED: [SessionState.IDLE, SessionState.STUDYING] # Çöken oturumu kurtarmak için
}

class StateTransitionError(Exception):
    """Geçersiz bir durum geçişi yapılmaya çalışıldığında fırlatılır."""
    pass