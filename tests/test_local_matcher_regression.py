from src.matcher import match_questions, text_similarity
from src.models.question import Question
from src.comparator.comparator import FormComparator


def q(n, text, field="text", options=None, children=None):
    return Question(n, text, field, options or [], children or [])


def test_same_logical_question_survives_renumbering():
    old = [q(1, "Name"), q(2, "State")]
    new = [q(1, "Name"), q(5, "State / territory")]
    matches, removed, added = match_questions(old, new)
    assert [(a.number, b.number) for a, b, _, _ in matches] == [(1, 1), (2, 5)]
    assert not removed
    assert not added


def test_added_and_removed_questions_are_not_forced_into_matches():
    old = [q(1, "First name"), q(2, "Age"), q(3, "Country")]
    new = [q(1, "First name"), q(2, "Country"), q(3, "Occupation")]
    matches, removed, added = match_questions(old, new)
    assert {x.text for x in removed} == {"Age"}
    assert {x.text for x in added} == {"Occupation"}
    assert {(a.text, b.text) for a, b, _, _ in matches} == {
        ("First name", "First name"),
        ("Country", "Country"),
    }


def test_true_reorder_is_detected_separately_from_renumbering():
    old = [q(1, "Name"), q(2, "Age"), q(3, "Country")]
    new = [q(1, "Country"), q(2, "Name"), q(3, "Age")]
    result = FormComparator().compare(old, new)
    assert any(d.difference_type == "QUESTION_REORDERED" for d in result.differences)


def test_option_change_is_reported_without_cloud_ai():
    old = [q(1, "Gender", "checkbox", ["Male", "Female"])]
    new = [q(1, "Gender", "checkbox", ["Male", "Female", "Other"])]
    result = FormComparator().compare(old, new)
    assert any(d.difference_type == "OPTIONS_ADDED" for d in result.differences)


def test_field_type_change_is_reported():
    old = [q(1, "Country", "text")]
    new = [q(1, "Country", "dropdown", ["India", "USA"])]
    result = FormComparator().compare(old, new)
    assert any(d.difference_type == "FIELD_TYPE_CHANGED" for d in result.differences)


def test_child_logic_change_is_reported():
    old = [q(1, "Do you have another name?", children=["Other name"])]
    new = [q(1, "Do you have another name?", children=["Other name", "Reason"])]
    result = FormComparator().compare(old, new)
    assert any(d.difference_type == "CHILD_LOGIC_CHANGED" for d in result.differences)


def test_cosmetic_text_change_is_not_semantic_change():
    old = [q(1, "First Name:")]
    new = [q(1, "First name (patient)")]
    result = FormComparator().compare(old, new)
    assert not any(d.difference_type == "QUESTION_TEXT_CHANGED" for d in result.differences)


def test_generic_text_does_not_create_match_without_content_signal():
    old = [q(1, "Please provide information")]
    new = [q(1, "Please enter address")]
    matches, removed, added = match_questions(old, new)
    assert not matches
    assert removed and added


def test_similarity_is_higher_for_related_questions():
    related = text_similarity("What is your age?", "Please enter your age")
    unrelated = text_similarity("What is your age?", "What is your country?")
    assert related > unrelated


def test_renumbering_without_sequence_change_is_not_reorder():
    old = [q(1, "Name"), q(2, "Age"), q(3, "Country")]
    new = [q(1, "Name"), q(5, "Age"), q(6, "Country")]
    result = FormComparator().compare(old, new)
    assert not any(d.difference_type == "QUESTION_REORDERED" for d in result.differences)
    assert sum(d.difference_type == "QUESTION_NUMBER_CHANGED" for d in result.differences) == 2
