from pathlib import Path
import pytest
from database.database import DatabaseManager
from database.models import StudySession, QuestionBatch, Violation, SystemEvent
from database.repositories import (
    SessionRepository, QuestionRepository, ViolationRepository, SystemEventRepository
)


@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_guardian.db"
    mgr = DatabaseManager(db_path)
    mgr.initialize()
    return mgr


def test_db_tables_created(temp_db):
    with temp_db.get_connection() as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t["name"] for t in tables]
        assert "study_sessions" in table_names
        assert "pomodoro_sessions" in table_names
        assert "question_batches" in table_names
        assert "violations" in table_names
        assert "system_events" in table_names
        assert "settings" in table_names


def test_session_repository(temp_db):
    repo = SessionRepository(temp_db)
    session = StudySession(
        subject="Matematik",
        topic="Türev",
        planned_duration_minutes=25,
        actual_duration_minutes=25,
        status="STUDY"
    )
    saved = repo.create_session(session)
    assert saved.id is not None
    assert saved.subject == "Matematik"

    # Fetch
    fetched = repo.get_session_by_id(saved.id)
    assert fetched is not None
    assert fetched.topic == "Türev"
    assert fetched.status == "STUDY"


def test_question_repository(temp_db):
    repo = QuestionRepository(temp_db)
    batch = QuestionBatch(
        exam_type="TYT",
        subject="Matematik",
        topic="Problemler",
        total_questions=40,
        correct_count=32,
        wrong_count=6,
        empty_count=2,
        net_score=30.50,
        accuracy_rate=80.0
    )
    saved = repo.record_batch(batch)
    assert saved.id is not None

    all_batches = repo.get_all_batches()
    assert len(all_batches) == 1
    assert all_batches[0].net_score == 30.50


def test_violation_and_events_repository(temp_db):
    v_repo = ViolationRepository(temp_db)
    e_repo = SystemEventRepository(temp_db)

    # Violation
    v = Violation(
        rule_name="valorant",
        process_name="VALORANT-Win64-Shipping.exe",
        executable_path="C:/Games/Valorant.exe",
        reason="Oyun: Valorant çalışma saatinde yasak."
    )
    saved_v = v_repo.record_violation(v)
    assert saved_v.id is not None

    # Event
    e = e_repo.record_event("STARTED", "App launched")
    assert e.id is not None
    last = e_repo.get_last_event()
    assert last.event_type == "STARTED"
