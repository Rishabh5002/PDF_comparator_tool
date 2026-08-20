from pathlib import Path
from src.parser.form_parser import parse_pdf
from src.evaluation import evaluate_matching

ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / "data" / "samples" / "samplev1.pdf"
V2 = ROOT / "data" / "samples" / "samplev2.pdf"

def test_sample_documents_have_expected_question_counts():
    old = parse_pdf(V1)["questions"]
    new = parse_pdf(V2)["questions"]
    assert len(old) == 22
    assert len(new) == 18

def test_sample_matching_is_one_to_one_and_flags_known_removals():
    old = parse_pdf(V1)["questions"]
    new = parse_pdf(V2)["questions"]
    report = evaluate_matching(old, new)
    assert report["match_count"] == 18
    assert {x["number"] for x in report["removed"]} == {8, 9, 10, 18}
    assert report["added_count"] == 0

def test_known_logical_matches_are_high_confidence():
    old = parse_pdf(V1)["questions"]
    new = parse_pdf(V2)["questions"]
    report = evaluate_matching(old, new)
    by_old = {x["old_number"]: x for x in report["matches"]}
    assert by_old[11]["new_number"] == 8
    assert by_old[11]["confidence"] == "high"
    assert by_old[22]["new_number"] == 18
    assert by_old[22]["confidence"] == "high"
