"""
Deterministic Focus Score Calculator for YKS Sentinel.
Single source of truth for calculating session and daily focus scores.
"""


def calculate_session_focus_score(
    planned_minutes: int,
    actual_minutes: int,
    violations_count: int,
    interruptions_count: int
) -> int:
    """
    Calculates deterministic Focus Score (0 - 100) for a session.
    - Base score: 100
    - Incomplete duration penalty: up to 40 pts
    - Violations penalty: -10 pts each
    - Interruptions penalty: -5 pts each
    """
    score = 100.0

    # 1. Completion adherence penalty
    planned = max(1, planned_minutes)
    completion_ratio = min(1.0, actual_minutes / planned)
    completion_penalty = (1.0 - completion_ratio) * 40.0
    score -= completion_penalty

    # 2. Violations penalty
    violation_penalty = violations_count * 10.0
    score -= violation_penalty

    # 3. Interruptions penalty
    interruption_penalty = interruptions_count * 5.0
    score -= interruption_penalty

    return max(0, min(100, int(round(score))))


def calculate_daily_focus_score(
    total_planned_minutes: int,
    total_actual_minutes: int,
    total_violations: int,
    total_interruptions: int
) -> int:
    """Calculates aggregate daily focus score."""
    if total_planned_minutes <= 0 and total_actual_minutes <= 0:
        return 100
    return calculate_session_focus_score(
        planned_minutes=max(total_planned_minutes, 1),
        actual_minutes=total_actual_minutes,
        violations_count=total_violations,
        interruptions_count=total_interruptions
    )
