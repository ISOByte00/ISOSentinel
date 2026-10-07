from pathlib import Path
import pytest
from database.database import DatabaseManager
from database.repositories import SessionRepository
from core.session_manager import (
    SessionController, STATE_IDLE, STATE_PREPARING, STATE_STUDY,
    STATE_BREAK, STATE_COMPLETED, STATE_INTERRUPTED
)


@pytest.fixture
def session_ctrl(tmp_path):
    db_path = tmp_path / "test_sessions.db"
    mgr = DatabaseManager(db_path)
    mgr.initialize()
    repo = SessionRepository(mgr)
    return SessionController(repo)


def test_session_lifecycle(session_ctrl):
    assert session_ctrl.get_state() == STATE_IDLE

    # 1. Prepare
    ok = session_ctrl.prepare_session("Fizik", "Kuvvet ve Hareket", 25)
    assert ok is True
    assert session_ctrl.get_state() == STATE_PREPARING

    # 2. Start Study Block
    ok = session_ctrl.start_study_block(25)
    assert ok is True
    assert session_ctrl.get_state() == STATE_STUDY
    assert session_ctrl.pomodoro_count == 1
    assert session_ctrl.seconds_left == 25 * 60

    # 3. Tick
    left = session_ctrl.tick_second()
    assert left == (25 * 60) - 1
    assert session_ctrl.total_study_seconds == 1

    # 4. Switch to Break
    ok = session_ctrl.start_break_block()
    assert ok is True
    assert session_ctrl.get_state() == STATE_BREAK

    # 5. Complete Session
    ok = session_ctrl.complete_session()
    assert ok is True
    assert session_ctrl.get_state() == STATE_COMPLETED
    assert session_ctrl.current_session.status == STATE_COMPLETED


def test_invalid_transitions(session_ctrl):
    # Cannot jump directly from IDLE to BREAK
    assert session_ctrl.can_transition_to(STATE_BREAK) is False
    assert session_ctrl.transition_to(STATE_BREAK) is False
