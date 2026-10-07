from database.database import get_connection
from database.models import QuestionBatch

class AnalyticsRepository:
    def __init__(self):
        self.conn = get_connection()

    def save_question_batch(self, batch: QuestionBatch):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO question_batches (session_id, subject, topic, correct_count, wrong_count, empty_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (batch.session_id, batch.subject, batch.topic, batch.correct_count, batch.wrong_count, batch.empty_count))
        self.conn.commit()