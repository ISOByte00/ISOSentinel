"""
Session Controller & State Machine for YKS Sentinel.
Manages the study lifecycle, pomodoro segments, and state transitions.
"""
import logging
from datetime import datetime
from typing import Optional
from database.models import StudySession, PomodoroSession
from database.repositories import SessionRepository
from core.event_bus import event_bus
from config.settings import settings

logger = logging.getLogger(__name__)

# Valid session states
STATE_IDLE = "IDLE"
STATE_PREPARING = "PREPARING"
STATE_STUDY = "STUDY"
STATE_BREAK = "BREAK"
STATE_COMPLETED = "COMPLETED"
STATE_INTERRUPTED = "INTERRUPTED"
STATE_RECOVERY = "RECOVERY"
STATE_ERROR = "ERROR"

VALID_TRANSITIONS = {
    STATE_IDLE: [STATE_PREPARING, STATE_RECOVERY],
    STATE_PREPARING: [STATE_STUDY, STATE_IDLE, STATE_ERROR],
    STATE_STUDY: [STATE_BREAK, STATE_COMPLETED, STATE_INTERRUPTED, STATE_ERROR],
    STATE_BREAK: [STATE_STUDY, STATE_COMPLETED, STATE_INTERRUPTED, STATE_ERROR],
    STATE_COMPLETED: [STATE_IDLE],
    STATE_INTERRUPTED: [STATE_IDLE, STATE_RECOVERY],
    STATE_RECOVERY: [STATE_IDLE, STATE_STUDY],
    STATE_ERROR: [STATE_IDLE]
}


class SessionController:
    """Controls session state transitions and pomodoro timing."""

    def __init__(self, session_repo: SessionRepository):
        self.repo = session_repo
        self.state: str = STATE_IDLE
        self.current_session: Optional[StudySession] = None
        self.current_pomodoro: Optional[PomodoroSession] = None
        self.pomodoro_count: int = 0
        self.seconds_left: int = 0
        self.total_study_seconds: int = 0
        self.interruptions_count: int = 0

    def get_state(self) -> str:
        return self.state

    def can_transition_to(self, new_state: str) -> bool:
        return new_state in VALID_TRANSITIONS.get(self.state, [])

    def transition_to(self, new_state: str, reason: str = "") -> bool:
        if not self.can_transition_to(new_state):
            logger.warning(f"Invalid transition from {self.state} to {new_state} ({reason})")
            return False

        old_state = self.state
        self.state = new_state
        logger.info(f"Session State Transition: {old_state} -> {new_state} (Reason: {reason})")

        if self.current_session:
            self.current_session.status = new_state
            self.repo.update_session(self.current_session)

        event_bus.publish("STATE_CHANGED", {
            "old_state": old_state,
            "new_state": new_state,
            "reason": reason,
            "session": self.current_session
        })
        return True

    def prepare_session(self, subject: str, topic: str, duration_minutes: int) -> bool:
        """Sets up a new session before starting."""
        if not self.can_transition_to(STATE_PREPARING):
            return False

        self.current_session = StudySession(
            subject=subject,
            topic=topic,
            planned_duration_minutes=duration_minutes,
            actual_duration_minutes=0,
            status=STATE_PREPARING,
            started_at=datetime.now()
        )
        self.current_session = self.repo.create_session(self.current_session)
        self.pomodoro_count = 0
        self.total_study_seconds = 0
        self.interruptions_count = 0

        self.transition_to(STATE_PREPARING, f"Preparing session for {subject} - {topic}")
        return True

    def start_study_block(self, duration_minutes: Optional[int] = None) -> bool:
        """Starts a study block (Pomodoro)."""
        if self.state not in [STATE_PREPARING, STATE_BREAK, STATE_RECOVERY]:
            logger.warning(f"Cannot start study block from state {self.state}")
            return False

        if not self.current_session:
            logger.error("No active session to start study block for.")
            return False

        minutes = duration_minutes or settings.pomodoro.study_duration_minutes
        self.seconds_left = minutes * 60
        self.pomodoro_count += 1

        self.current_pomodoro = PomodoroSession(
            study_session_id=self.current_session.id,
            sequence_number=self.pomodoro_count,
            segment_type="STUDY",
            planned_minutes=minutes,
            actual_minutes=0,
            started_at=datetime.now(),
            status="RUNNING"
        )
        self.current_pomodoro = self.repo.create_pomodoro_session(self.current_pomodoro)

        self.transition_to(STATE_STUDY, f"Starting Study Block #{self.pomodoro_count}")
        event_bus.publish("SESSION_STARTED", {"session": self.current_session, "pomodoro": self.current_pomodoro})
        return True

    def start_break_block(self, is_long_break: bool = False) -> bool:
        """Starts a short or long break."""
        if self.state != STATE_STUDY:
            return False

        # Complete current study pomodoro
        if self.current_pomodoro:
            self.current_pomodoro.status = "COMPLETED"
            self.current_pomodoro.ended_at = datetime.now()
            self.repo.update_pomodoro_session(self.current_pomodoro)

        minutes = (
            settings.pomodoro.long_break_minutes
            if (is_long_break or (self.pomodoro_count % settings.pomodoro.pomodoros_until_long_break == 0))
            else settings.pomodoro.short_break_minutes
        )
        self.seconds_left = minutes * 60

        self.current_pomodoro = PomodoroSession(
            study_session_id=self.current_session.id,
            sequence_number=self.pomodoro_count,
            segment_type="BREAK",
            planned_minutes=minutes,
            actual_minutes=0,
            started_at=datetime.now(),
            status="RUNNING"
        )
        self.current_pomodoro = self.repo.create_pomodoro_session(self.current_pomodoro)

        self.transition_to(STATE_BREAK, f"Starting Break ({minutes} min)")
        return True

    def tick_second(self) -> int:
        """Called every second by the timer."""
        if self.seconds_left > 0:
            self.seconds_left -= 1
            if self.state == STATE_STUDY:
                self.total_study_seconds += 1
                if self.current_session:
                    self.current_session.actual_duration_minutes = self.total_study_seconds // 60
            if self.current_pomodoro:
                self.current_pomodoro.actual_minutes = (
                    (self.current_pomodoro.planned_minutes * 60 - self.seconds_left) // 60
                )
        return self.seconds_left

    def register_interruption(self, reason: str = ""):
        """Logs an interruption within the current session."""
        self.interruptions_count += 1
        if self.current_session:
            self.current_session.interruptions_count = self.interruptions_count
            self.repo.update_session(self.current_session)
        event_bus.publish("INTERRUPTION_RECORDED", {
            "session_id": self.current_session.id if self.current_session else None,
            "count": self.interruptions_count,
            "reason": reason
        })

    def complete_session(self) -> bool:
        """Ends the session successfully."""
        if self.state not in [STATE_STUDY, STATE_BREAK]:
            return False

        if self.current_pomodoro:
            self.current_pomodoro.status = "COMPLETED"
            self.current_pomodoro.ended_at = datetime.now()
            self.repo.update_pomodoro_session(self.current_pomodoro)

        if self.current_session:
            self.current_session.ended_at = datetime.now()
            self.current_session.actual_duration_minutes = self.total_study_seconds // 60
            planned = max(1, self.current_session.planned_duration_minutes)
            self.current_session.completion_rate = min(1.0, round(self.current_session.actual_duration_minutes / planned, 2))
            self.current_session.status = STATE_COMPLETED
            self.repo.update_session(self.current_session)

        self.transition_to(STATE_COMPLETED, "Session completed successfully.")
        event_bus.publish("SESSION_ENDED", {"session": self.current_session, "status": STATE_COMPLETED})
        return True

    def interrupt_session(self, reason: str = "User manual stop"):
        """Interrupts or cancels the session."""
        if self.state in [STATE_IDLE, STATE_COMPLETED]:
            return

        if self.current_pomodoro:
            self.current_pomodoro.status = "INTERRUPTED"
            self.current_pomodoro.ended_at = datetime.now()
            self.repo.update_pomodoro_session(self.current_pomodoro)

        if self.current_session:
            self.current_session.ended_at = datetime.now()
            self.current_session.actual_duration_minutes = self.total_study_seconds // 60
            self.current_session.status = STATE_INTERRUPTED
            self.repo.update_session(self.current_session)

        self.transition_to(STATE_INTERRUPTED, reason)
        event_bus.publish("SESSION_ENDED", {"session": self.current_session, "status": STATE_INTERRUPTED})

    def reset_to_idle(self):
        """Resets the controller back to IDLE state."""
        self.state = STATE_IDLE
        self.current_session = None
        self.current_pomodoro = None
        self.seconds_left = 0
        self.total_study_seconds = 0
        self.interruptions_count = 0
        event_bus.publish("STATE_CHANGED", {"old_state": None, "new_state": STATE_IDLE, "reason": "Reset to IDLE"})