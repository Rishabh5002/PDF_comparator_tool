from src.comparator.comparator import FormComparator
from src.matcher import text_similarity
from src.models.question import Question


def test_semantic_question_matching_without_same_number():
    old = [Question(2, "What is your age?", "text")]
    new = [Question(5, "Please enter your age", "text")]
    result = FormComparator(match_threshold=0.5).compare(old, new)
    types = {d.difference_type for d in result.differences}
    assert "QUESTION_NUMBER_CHANGED" in types
    assert "QUESTION_REMOVED" not in types
    assert "QUESTION_ADDED" not in types


def test_options_are_compared():
    old = [Question(1, "Sex", "single_choice", ["Male", "Female"])]
    new = [Question(1, "Sex", "single_choice", ["Male", "Female", "Other"])]
    result = FormComparator().compare(old, new)
    assert any(d.difference_type == "OPTIONS_ADDED" for d in result.differences)


def test_question_reorder_is_detected():
    old = [Question(1, "Name"), Question(2, "Age"), Question(3, "Country")]
    new = [Question(1, "Name"), Question(3, "Country"), Question(2, "Age")]
    result = FormComparator().compare(old, new)
    assert any(d.difference_type == "QUESTION_REORDERED" for d in result.differences)


def test_text_similarity_is_local():
    assert text_similarity("What is your age?", "Please enter your age") > 0.5


def test_unextractable_option_set_is_reported_as_structural_change():
    old = [Question(4, "Country", "text", [])]
    new = [Question(4, "Country", "single_choice", ["India", "Japan"])]
    result = FormComparator().compare(old, new)
    assert any(d.difference_type == "OPTIONS_CHANGED" for d in result.differences)
    assert any(d.difference_type == "FIELD_TYPE_CHANGED" for d in result.differences)


def test_encrypted_pdf_requires_password(tmp_path):
    import pymupdf
    from src.parser.form_parser import parse_pdf

    path = tmp_path / "protected.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "1. Name")
    doc.save(str(path), encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="secret")
    doc.close()

    import pytest
    with pytest.raises(ValueError, match="password protected"):
        parse_pdf(path)

    parsed = parse_pdf(path, "secret")
    assert parsed["questions"][0].text == "Name"
