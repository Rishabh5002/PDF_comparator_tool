import os
import sys
from pathlib import Path

# Ensure root in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models.difference import Difference
from src.comparator.comparator import FormComparator
from src.models.question import Question
from backend.service import build_side_by_side_diff, build_payload


def test_difference_categories():
    diff_removed = Difference("QUESTION_REMOVED", question_number=1, old_value="Old text", new_value=None)
    assert diff_removed.category == "removed", f"Expected 'removed', got {diff_removed.category}"

    diff_added = Difference("QUESTION_ADDED", question_number=2, old_value=None, new_value="New text")
    assert diff_added.category == "added", f"Expected 'added', got {diff_added.category}"

    diff_opt_removed = Difference("OPTIONS_REMOVED", question_number=3, old_value=["A", "B"], new_value=["A"])
    assert diff_opt_removed.category == "modified", f"Expected 'modified' for OPTIONS_REMOVED, got {diff_opt_removed.category}"

    diff_text_changed = Difference("QUESTION_TEXT_CHANGED", question_number=4, old_value="Foo", new_value="Bar")
    assert diff_text_changed.category == "modified", f"Expected 'modified' for QUESTION_TEXT_CHANGED, got {diff_text_changed.category}"
    print("test_difference_categories passed successfully!")


def test_side_by_side_diff():
    sample1 = Path("data/samples/samplev1.pdf")
    sample2 = Path("data/samples/samplev2.pdf")
    if not (sample1.exists() and sample2.exists()):
        print("Samples not found, skipping side_by_side test.")
        return

    payload = build_payload(str(sample1), str(sample2), None, None, 0.4)
    assert "side_by_side_diff" in payload, "Missing side_by_side_diff in payload"
    diff_rows = payload["side_by_side_diff"]
    assert len(diff_rows) > 0, "Expected non-empty diff_rows"

    statuses = {r["status"] for r in diff_rows}
    assert "modified" in statuses or "unchanged" in statuses, f"Unexpected statuses: {statuses}"
    # Check that added/deleted have counterpart spacers (None on opposite side)
    for r in diff_rows:
        if r["status"] == "added":
            assert r["old"] is None and r["new"] is not None
        elif r["status"] == "deleted":
            assert r["old"] is not None and r["new"] is None
        elif r["status"] == "modified":
            assert r["old"] is not None and r["new"] is not None

    print(f"test_side_by_side_diff passed successfully with {len(diff_rows)} aligned rows!")


if __name__ == "__main__":
    test_difference_categories()
    test_side_by_side_diff()
