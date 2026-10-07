from analytics.statistics import calculate_net_score, calculate_accuracy_rate, calculate_daily_summary
from analytics.focus_score import calculate_session_focus_score, calculate_daily_focus_score
from database.models import StudySession, QuestionBatch, Violation


def test_net_score_calculation():
    # 40 questions, 32 correct, 6 wrong, 2 empty -> 32 - 1.5 = 30.5
    assert calculate_net_score(32, 6) == 30.50
    # Zero wrong -> exactly correct
    assert calculate_net_score(20, 0) == 20.0
    # Negative net clamped to 0.0
    assert calculate_net_score(1, 10) == 0.0


def test_accuracy_rate():
    assert calculate_accuracy_rate(32, 40) == 80.0
    assert calculate_accuracy_rate(0, 0) == 0.0


def test_focus_score():
    # Perfect session
    score = calculate_session_focus_score(planned_minutes=25, actual_minutes=25, violations_count=0, interruptions_count=0)
    assert score == 100

    # Half finished (50% completion penalty = 20 pts) -> 80
    score_half = calculate_session_focus_score(planned_minutes=50, actual_minutes=25, violations_count=0, interruptions_count=0)
    assert score_half == 80

    # Violations (-10 pts each) and Interruptions (-5 pts each)
    score_penalized = calculate_session_focus_score(
        planned_minutes=25, actual_minutes=25, violations_count=2, interruptions_count=1
    )
    assert score_penalized == 100 - (2 * 10) - (1 * 5)  # 75
