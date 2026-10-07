"""
Repository for question_batches table.
"""
import sqlite3
from datetime import datetime
from typing import List, Optional
from database.models import QuestionBatch


class QuestionRepository:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def record_batch(self, batch: QuestionBatch) -> QuestionBatch:
        query = """
        INSERT INTO question_batches (
            study_session_id, exam_type, subject, topic,
            total_questions, correct_count, wrong_count, empty_count,
            net_score, accuracy_rate, recorded_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        recorded_at = batch.recorded_at or datetime.now()
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (
                batch.study_session_id,
                batch.exam_type,
                batch.subject,
                batch.topic,
                batch.total_questions,
                batch.correct_count,
                batch.wrong_count,
                batch.empty_count,
                batch.net_score,
                batch.accuracy_rate,
                recorded_at
            ))
            batch.id = cursor.lastrowid
            batch.recorded_at = recorded_at
            conn.commit()
        return batch

    def get_today_batches(self) -> List[QuestionBatch]:
        query = """
        SELECT * FROM question_batches
        WHERE date(recorded_at) = date('now', 'localtime')
        ORDER BY id DESC
        """
        with self.db_manager.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [self._row_to_batch(r) for r in rows]

    def get_all_batches(self) -> List[QuestionBatch]:
        query = "SELECT * FROM question_batches ORDER BY id DESC"
        with self.db_manager.get_connection() as conn:
            rows = conn.execute(query).fetchall()
            return [self._row_to_batch(r) for r in rows]

    def _parse_dt(self, val) -> Optional[datetime]:
        if val is None:
            return None
        if isinstance(val, datetime):
            return val
        if isinstance(val, str):
            return datetime.fromisoformat(val)
        return None

    def _row_to_batch(self, row: sqlite3.Row) -> QuestionBatch:
        recorded_at = self._parse_dt(row["recorded_at"])
        return QuestionBatch(
            id=row["id"],
            study_session_id=row["study_session_id"],
            exam_type=row["exam_type"],
            subject=row["subject"],
            topic=row["topic"],
            total_questions=row["total_questions"],
            correct_count=row["correct_count"],
            wrong_count=row["wrong_count"],
            empty_count=row["empty_count"],
            net_score=row["net_score"],
            accuracy_rate=row["accuracy_rate"],
            recorded_at=recorded_at
        )
