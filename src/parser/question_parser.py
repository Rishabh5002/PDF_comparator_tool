from src.models.question import Question


class QuestionParser:

    def parse(self, question_blocks):
        questions = []

        for block in question_blocks:
            question = self.parse_question(block)
            questions.append(question)

        return questions

    def parse_question(self, block):
        number = block["number"]
        text = block["text"]
        rows = block["rows"]

        options = [
            row.get_text().strip()
            for row in rows
            if row.get_text().strip()
        ]

        field_type = self.detect_field_type(text, options)

        return Question(
            number=number,
            text=text,
            field_type=field_type,
            options=options,
            child_questions=[],
        )

    def detect_field_type(self, text, options):
        text_lower = text.lower()

        if "check all that apply" in text_lower:
            return "checkbox"

        if len(options) > 1:
            return "single_choice"

        return "text"