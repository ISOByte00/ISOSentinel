"""
Statistics calculation and aggregations for YKS Sentinel.
"""
from typing import Dict, List, Any
from database.models import QuestionBatch, StudySession, Violation
from analytics.focus_score import calculate_daily_focus_score


def calculate_net_score(correct: int, wrong: int) -> float:
    """Calculates YKS standard net score: Dogru - (Yanlis / 4)."""
    net = correct - (wrong / 4.0)
    return round(max(0.0, net), 2)


def calculate_accuracy_rate(correct: int, total: int) -> float:
    """Calculates percentage accuracy: (Correct / Total) * 100."""
    if total <= 0:
        return 0.0
    return round((correct / float(total)) * 100.0, 2)


def calculate_daily_summary(
    sessions: List[StudySession],
    question_batches: List[QuestionBatch],
    violations: List[Violation]
) -> Dict[str, Any]:
    """Computes daily totals and aggregate metrics."""
    total_study_minutes = sum(s.actual_duration_minutes for s in sessions)
    total_planned_minutes = sum(s.planned_duration_minutes for s in sessions)
    total_interruptions = sum(s.interruptions_count for s in sessions)

    total_questions = sum(q.total_questions for q in question_batches)
    total_correct = sum(q.correct_count for q in question_batches)
    total_wrong = sum(q.wrong_count for q in question_batches)
    total_empty = sum(q.empty_count for q in question_batches)
    total_net = sum(q.net_score for q in question_batches)
    
    avg_accuracy = calculate_accuracy_rate(total_correct, total_questions)
    violations_count = len(violations)

    focus_score = calculate_daily_focus_score(
        total_planned_minutes=total_planned_minutes,
        total_actual_minutes=total_study_minutes,
        total_violations=violations_count,
        total_interruptions=total_interruptions
    )

    return {
        "study_minutes": total_study_minutes,
        "planned_minutes": total_planned_minutes,
        "completed_sessions": len([s for s in sessions if s.status == "COMPLETED"]),
        "total_sessions": len(sessions),
        "total_questions": total_questions,
        "total_correct": total_correct,
        "total_wrong": total_wrong,
        "total_empty": total_empty,
        "total_net": round(total_net, 2),
        "avg_accuracy": avg_accuracy,
        "violations_count": violations_count,
        "focus_score": focus_score
    }
