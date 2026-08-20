class Question:
    def __init__(
        self,
        number,
        text,
        field_type=None,
        options=None,
        child_questions=None,
        page=None,
        y=None,
        option_source=None,
    ):
        self.number = number
        self.text = text
        self.field_type = field_type
        self.options = options if options is not None else []
        self.child_questions = child_questions if child_questions is not None else []
        self.page = page
        self.y = y
        self.option_source = option_source

    def __repr__(self):
        return (
            f"Question(number={self.number}, text={self.text!r}, "
            f"field_type={self.field_type!r}, options={self.options!r}, "
            f"child_questions={self.child_questions!r}, page={self.page!r})"
        )
