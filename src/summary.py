"""Deterministic summary generation; intentionally no LLM dependency."""


def build_local_summary(result):
    s = result.summary
    total = s.get("total_changes", 0)
    if total == 0:
        return "No differences were detected between the two parsed document revisions."

    parts = []
    mapping = [
        ("QUESTION_ADDED", "added sections/items"),
        ("QUESTION_REMOVED", "removed sections/items"),
        ("QUESTION_REORDERED", "reordered sections"),
        ("QUESTION_TEXT_CHANGED", "text changes"),
        ("OPTIONS_ADDED", "option additions"),
        ("OPTIONS_CHANGED", "option-set changes"),
        ("OPTIONS_REMOVED", "option removals"),
        ("FIELD_TYPE_CHANGED", "field-type changes"),
        ("CHILD_LOGIC_CHANGED", "sub-item logic changes"),
        ("QUESTION_NUMBER_CHANGED", "section renumberings"),
    ]
    for key, label in mapping:
        if s.get(key):
            parts.append(f"{s[key]} {label}")
    return f"Detected {total} recorded changes: " + ", ".join(parts) + "."
