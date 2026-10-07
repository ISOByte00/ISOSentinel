"""
Data models for YKS Sentinel SQLite Database.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class StudySession:
    id: Optional[int] = None
    subject: str = ""
    topic: str = ""
    planned_duration_minutes: int = 25
    actual_duration_minutes: int = 0
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    status: str = "PREPARING"  # PREPARING, STUDY, BREAK, COMPLETED, INTERRUPTED, RECOVERY, ERROR
    interruptions_count: int = 0
    completion_rate: float = 0.0


@dataclass
class PomodoroSession:
    id: Optional[int] = None
    study_session_id: int = 0
    sequence_number: int = 1
    segment_type: str = "STUDY"  # STUDY, BREAK
    planned_minutes: int = 25
    actual_minutes: int = 0
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    status: str = "RUNNING"  # RUNNING, COMPLETED, INTERRUPTED


@dataclass
class QuestionBatch:
    id: Optional[int] = None
    study_session_id: Optional[int] = None
    exam_type: str = "TYT"  # TYT, AYT
    subject: str = ""
    topic: str = ""
    total_questions: int = 0
    correct_count: int = 0
    wrong_count: int = 0
    empty_count: int = 0
    net_score: float = 0.0
    accuracy_rate: float = 0.0
    recorded_at: Optional[datetime] = None


@dataclass
class Violation:
    id: Optional[int] = None
    study_session_id: Optional[int] = None
    rule_name: str = ""
    process_name: str = ""
    executable_path: str = ""
    process_hash: str = ""
    severity: str = "HIGH"
    action_taken: str = "kill"
    reason: str = ""
    detected_at: Optional[datetime] = None


@dataclass
class SystemEvent:
    id: Optional[int] = None
    event_type: str = ""  # STARTED, HEARTBEAT, CLEAN_EXIT, UNEXPECTED_SHUTDOWN, CLOCK_CHANGED
    details: str = ""
    recorded_at: Optional[datetime] = None
