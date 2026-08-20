"""Evaluation helpers for reviewing local matching decisions."""
from __future__ import annotations

from src.matcher import match_questions, text_similarity, meaningful_tokens


def evaluate_matching(old_questions, new_questions, threshold=0.40):
    matches, removed, added = match_questions(old_questions, new_questions, threshold)
    rows = []
    for old, new, score, signals in matches:
        rows.append({
            "old_number": old.number,
            "new_number": new.number,
            "old_text": old.text,
            "new_text": new.text,
            "score": round(score, 4),
            "confidence": "high" if score >= 0.80 else "medium" if score >= 0.55 else "low",
            "text_similarity": round(text_similarity(old.text, new.text), 4),
            "meaningful_overlap": bool(meaningful_tokens(old.text) & meaningful_tokens(new.text)),
            "same_field_type": old.field_type == new.field_type,
            "same_position": old.number == new.number,
            "option_similarity": round(signals["option_similarity"], 4),
            "field_similarity": round(signals["field_similarity"], 4),
            "position_similarity": round(signals["position_similarity"], 4),
            "neighbor_context": round(signals["neighbor_context"], 4),
        })
    return {
        "match_count": len(matches),
        "removed_count": len(removed),
        "added_count": len(added),
        "matches": rows,
        "removed": [{"number": q.number, "text": q.text} for q in removed],
        "added": [{"number": q.number, "text": q.text} for q in added],
    }
