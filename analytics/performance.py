"""
Topic and subject performance analytics for YKS Sentinel.
"""
from typing import Dict, List, Any
from database.models import QuestionBatch


def compute_subject_performance(batches: List[QuestionBatch]) -> Dict[str, Dict[str, Any]]:
    """Groups question batches by subject to summarize accuracy and net scores."""
    subject_map: Dict[str, Dict[str, Any]] = {}

    for b in batches:
        if b.subject not in subject_map:
            subject_map[b.subject] = {
                "total_questions": 0,
                "correct": 0,
                "wrong": 0,
                "empty": 0,
                "total_net": 0.0,
                "topics": {}
            }
        
        sm = subject_map[b.subject]
        sm["total_questions"] += b.total_questions
        sm["correct"] += b.correct_count
        sm["wrong"] += b.wrong_count
        sm["empty"] += b.empty_count
        sm["total_net"] += b.net_score

        # Topic level
        if b.topic not in sm["topics"]:
            sm["topics"][b.topic] = {
                "total_questions": 0,
                "correct": 0,
                "wrong": 0,
                "net": 0.0
            }
        tm = sm["topics"][b.topic]
        tm["total_questions"] += b.total_questions
        tm["correct"] += b.correct_count
        tm["wrong"] += b.wrong_count
        tm["net"] += b.net_score

    # Compute percentages
    for subj, data in subject_map.items():
        total = data["total_questions"]
        data["accuracy"] = round((data["correct"] / total * 100.0), 2) if total > 0 else 0.0
        data["total_net"] = round(data["total_net"], 2)
        for topic, tdata in data["topics"].items():
            t_total = tdata["total_questions"]
            tdata["accuracy"] = round((tdata["correct"] / t_total * 100.0), 2) if t_total > 0 else 0.0
            tdata["net"] = round(tdata["net"], 2)

    return subject_map
