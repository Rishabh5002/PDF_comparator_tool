from pathlib import Path
from src.models.question import Question
from src.matcher import explain_match
from src.semantic import LocalVectorizer
from src.reporter.pdf_report import write_pdf_report
from src.reporter.excel_report import write_excel_report


def q(text):
    return Question(1, text, "text")


def test_local_vector_similarity_is_available_and_bounded():
    vec = LocalVectorizer(["What is your age?", "Please provide your age", "What is your country?"])
    related = vec.similarity("What is your age?", "Please provide your age")
    unrelated = vec.similarity("What is your age?", "What is your country?")
    assert 0 <= related <= 1
    assert 0 <= unrelated <= 1
    assert related > unrelated


def test_match_explanation_contains_local_vector_signal():
    vec = LocalVectorizer(["What is your age?", "Please provide your age"])
    signals = explain_match(q("What is your age?"), q("Please provide your age"), vectorizer=vec)
    assert "local_vector_similarity" in signals


def payload():
    return {
        "old_document": {"filename": "v1.pdf", "pages": 1, "questions": 1},
        "new_document": {"filename": "v2.pdf", "pages": 1, "questions": 1},
        "comparison": {"summary": {"total_changes": 1}, "differences": [{"type": "QUESTION_TEXT_CHANGED", "question_number": 1, "old_value": "Age", "new_value": "Age (years)", "message": "text changed", "confidence": 0.9}]},
    }


def test_pdf_and_excel_reporters_create_files(tmp_path):
    p = write_pdf_report(payload(), tmp_path / "report.pdf")
    x = write_excel_report(payload(), tmp_path / "report.xlsx")
    assert p.exists() and p.stat().st_size > 0
    assert x.exists() and x.stat().st_size > 0
