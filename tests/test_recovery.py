from pathlib import Path
import pytest
from database.database import DatabaseManager
from database.models import StudySession
from database.repositories import SessionRepository, SystemEventRepository
from core.recovery import RecoveryManager


@pytest.fixture
def recovery_env(tmp_path):
    db_path = tmp_path / "test_recovery.db"
    mgr = DatabaseManager(db_path)
    mgr.initialize()
    s_repo = SessionRepository(mgr)
    e_repo = SystemEventRepository(mgr)
    rec = RecoveryManager(s_repo, e_repo)
    return rec, s_repo, e_repo


def test_clean_startup(recovery_env):
    rec, s_repo, e_repo = recovery_env
    # First time run (no previous events)
    result = rec.perform_startup_check()
    assert result["unexpected_shutdown"] is False
    assert result["recovered_session"] is None


def test_unexpected_shutdown_and_session_recovery(recovery_env):
    rec, s_repo, e_repo = recovery_env

    # Simulate a run that started, had an active session, but crashed without CLEAN_EXIT
    e_repo.record_event("STARTED", "App crashed before exit")
    e_repo.record_event("HEARTBEAT", "Heartbeat #1")
    
    dangling_session = StudySession(
        subject="Kimya",
        topic="Gazlar",
        planned_duration_minutes=50,
        status="STUDY"
    )
    s_repo.create_session(dangling_session)

    # Next startup
    result = rec.perform_startup_check()
    assert result["unexpected_shutdown"] is True
    assert result["recovered_session"] is not None
    assert result["recovered_session"].status == "RECOVERY"

    # Verify event logged in DB
    events = e_repo.get_recent_events()
    event_types = [e.event_type for e in events]
    assert "UNEXPECTED_SHUTDOWN" in event_types
    assert "STARTED" in event_types
