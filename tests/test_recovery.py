from pathlib import Path
from unittest.mock import Mock

from database.database import init_db
from database.models import StudySession
from database.repositories.session_repository import SessionRepository

import core.recovery as recovery


def test_recovery_returns_active_session_and_discards_completed_session(
    tmp_path,
    monkeypatch,
):
    db_path = tmp_path / "recovery.db"
    recovery_path = tmp_path / "recovery_state.json"
    monkeypatch.setattr("database.database.DB_PATH", str(db_path))
    monkeypatch.setattr(recovery, "RECOVERY_FILE_PATH", str(recovery_path))

    def replace_in_fixture(source, destination):
        Path(destination).write_bytes(Path(source).read_bytes())
        Path(source).unlink()

    monkeypatch.setattr(recovery.os, "replace", replace_in_fixture)
    remove_state_file = Mock()
    monkeypatch.setattr(recovery.os, "remove", remove_state_file)
    init_db()

    repo = SessionRepository()
    session_id = repo.create_session(
        StudySession(
            id=None,
            subject="Fizik",
            topic="Kuvvet",
            planned_duration=25,
            status="STUDYING",
        )
    )
    recovery.RecoveryManager.save_state(
        session_id,
        "Fizik",
        "Kuvvet",
        1200,
    )

    assert recovery.RecoveryManager.get_pending_recovery() == {
        "session_id": session_id,
        "subject": "Fizik",
        "topic": "Kuvvet",
        "remaining_seconds": 1200,
        "status": "STUDYING",
    }

    repo.update_session_status(session_id, "COMPLETED")

    assert recovery.RecoveryManager.get_pending_recovery() is None
    remove_state_file.assert_called_once_with(str(recovery_path))
