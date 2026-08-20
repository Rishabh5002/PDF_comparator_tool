from src.models.question import Question
from src.comparator.comparator import FormComparator


old_questions = [
    Question(
        number=1,
        text="What is your gender?",
        field_type="checkbox",
        options=["Male", "Female"],
    ),
    Question(
        number=2,
        text="What is your age?",
        field_type="text",
    ),
    Question(
        number=3,
        text="What is your country?",
        field_type="dropdown",
        options=["India", "USA"],
    ),
]


new_questions = [
    Question(
        number=1,
        text="What is your gender?",
        field_type="checkbox",
        options=["Male", "Female", "Other"],
    ),
    Question(
        number=3,
        text="What is your country of residence?",
        field_type="dropdown",
        options=["India", "USA", "Canada"],
    ),
    Question(
        number=4,
        text="What is your occupation?",
        field_type="text",
    ),
]


comparator = FormComparator()

differences = comparator.compare(
    old_questions,
    new_questions,
)

for difference in differences:
    print(difference)