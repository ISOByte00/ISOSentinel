"""
Crash Recovery and State Audit for YKS Sentinel.
Handles unfinished sessions after unexpected shutdowns or power loss.
"""
import logging
from datetime import datetime
from database.repositories import SessionRepository, SystemEventRepository
from database.models import StudySession

logger = logging.getLogger(__name__)


class RecoveryManager:
    def __init__(self, session_repo: SessionRepository, event_repo: SystemEventRepository):
        self.session_repo = session_repo
        self.event_repo = event_repo

    def perform_startup_check(self) -> dict:
        """
        Executes startup audit:
        1. Checks last system event (if not CLEAN_EXIT, logs UNEXPECTED_SHUTDOWN).
        2. Detects any dangling/unfinished study session and marks it.
        3. Logs STARTED event for the new run.
        """
        result = {
            "unexpected_shutdown": False,
            "recovered_session": None,
            "message": "Clean startup"
        }

        # 1. Audit previous shutdown
        last_event = self.event_repo.get_last_event()
        if last_event and last_event.event_type not in ["CLEAN_EXIT"]:
            logger.warning(f"Unexpected shutdown detected! Last recorded event was: {last_event.event_type}")
            self.event_repo.record_event(
                "UNEXPECTED_SHUTDOWN",
                f"Previous run did not cleanly exit. Last event: {last_event.event_type} at {last_event.recorded_at}"
            )
            result["unexpected_shutdown"] = True

        # 2. Check for unfinished session
        unfinished = self.session_repo.get_unfinished_session()
        if unfinished:
            logger.warning(f"Found unfinished session #{unfinished.id} in state '{unfinished.status}'")
            # Calculate outage / finalize status
            now = datetime.now()
            start_time = unfinished.started_at or now
            elapsed_minutes = max(0, int((now - start_time).total_seconds() // 60))
            
            unfinished.ended_at = now
            unfinished.actual_duration_minutes = min(elapsed_minutes, unfinished.planned_duration_minutes)
            unfinished.status = "RECOVERY"
            self.session_repo.update_session(unfinished)
            result["recovered_session"] = unfinished
            result["message"] = f"Recovered dangling session #{unfinished.id} ({unfinished.subject})"

        # 3. Record STARTED event for current instance
        self.event_repo.record_event("STARTED", "Application initialized and ready.")
        return result
