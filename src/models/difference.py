class Difference:
    def __init__(
        self,
        difference_type,
        question_number=None,
        old_value=None,
        new_value=None,
        message=None,
        confidence=None,
    ):
        self.difference_type = difference_type
        self.question_number = question_number
        self.old_value = old_value
        self.new_value = new_value
        self.message = message
        self.confidence = confidence

    def __repr__(self):
        return (
            f"Difference("
            f"difference_type={self.difference_type!r}, "
            f"question_number={self.question_number!r}, "
            f"old_value={self.old_value!r}, "
            f"new_value={self.new_value!r}, "
            f"message={self.message!r}, confidence={self.confidence!r}"
            f")"
        )