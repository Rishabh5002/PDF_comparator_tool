class FormDocument:
    def __init__(
        self,
        filename=None,
        questions=None,
        pages=None,
    ):
        self.filename = filename
        self.questions = questions or []
        self.pages = pages or []

    def add_question(self, question):
        self.questions.append(question)

    def get_question_count(self):
        return len(self.questions)

    def __repr__(self):
        return (
            f"FormDocument("
            f"filename={self.filename!r}, "
            f"questions={len(self.questions)}, "
            f"pages={len(self.pages)}"
            f")"
        )