from unittest.mock import Mock

import pytest

import core.session_manager as session_manager
from core.event_bus import EventBus
from core.states import SessionState
from database.database import init_db


@pytest.mark.parametrize(
    ("interrupted", "expected_status"),
    [
        (False, SessionState.COMPLETED.value),
        (True, SessionState.INTERRUPTED.value),
    ],
)
def test_session_lifecycle_persists_terminal_status_and_duration(
    tmp_path,
    monkeypatch,
    interrupted,
    expected_status,
):
    db_path = tmp_path / "sessions.db"
    monkeypatch.setattr("database.database.DB_PATH", str(db_path))
    init_db()

    events = []
    event_bus = EventBus()
    event_bus.subscribe("SESSION_STARTED", lambda data: events.append(("started", data)))
    event_bus.subscribe("SESSION_STOPPED", lambda data: events.append(("stopped", data)))
    monkeypatch.setattr(session_manager, "bus", event_bus)

    save_state = Mock()
    clear_state = Mock()
    monkeypatch.setattr(session_manager.RecoveryManager, "save_state", save_state)
    monkeypatch.setattr(session_manager.RecoveryManager, "clear_state", clear_state)

    timestamps = iter((100.0, 220.0))
    monkeypatch.setattr(session_manager.time, "monotonic", lambda: next(timestamps))

    controller = session_manager.SessionController()
    controller.start_session("Matematik", "Türev", 25)
    session_id = controller.active_session_id

    controller.stop_session(interrupted=interrupted)
    stored = controller.repo.get_session(session_id)

    assert stored.status == expected_status
    assert stored.actual_duration == 2
    assert controller.state == SessionState.IDLE
    assert controller.active_session_id is None
    save_state.assert_called_once_with(session_id, "Matematik", "Türev", 1500)
    clear_state.assert_called_once_with()
    assert events == [
        ("started", {"session_id": session_id}),
        ("stopped", {"session_id": session_id, "status": expected_status}),
    ]
