from unittest.mock import Mock

import main
import core.session_manager as session_manager
import restrictions.process_guard as guard
from core.event_bus import EventBus
from database.database import init_db


def test_session_events_activate_guard_and_guard_tick_scans(
    tmp_path,
    monkeypatch,
):
    db_path = tmp_path / "events.db"
    monkeypatch.setattr("database.database.DB_PATH", str(db_path))
    init_db()

    event_bus = EventBus()
    monkeypatch.setattr(main, "bus", event_bus)
    monkeypatch.setattr(session_manager, "bus", event_bus)
    monkeypatch.setattr(session_manager.RecoveryManager, "save_state", Mock())
    monkeypatch.setattr(session_manager.RecoveryManager, "clear_state", Mock())
    scan_and_kill = Mock()
    monkeypatch.setattr(guard, "scan_and_kill", scan_and_kill)
    guard.clear_ram_cache()
    guard._active_session_id = None

    main.setup_events()
    controller = session_manager.SessionController()
    controller.start_session("Kimya", "Mol", 25)
    session_id = controller.active_session_id

    event_bus.publish("GUARD_TICK")

    scan_and_kill.assert_called_once_with(session_id)
    assert guard._active_session_id == session_id

    controller.stop_session(interrupted=True)

    assert guard._active_session_id is None
    assert not main.lock_manager.is_locked
