class Difference:
    def __init__(
        self,
        difference_type,
        question_number=None,
        old_value=None,
        new_value=None,
        message=None,
        confidence=None,
        category=None,
    ):
        self.difference_type = difference_type
        self.question_number = question_number
        self.old_value = old_value
        self.new_value = new_value
        self.message = message
        self.confidence = confidence
        
        # Categorize difference canonically
        if category:
            self.category = category
        else:
            dtype = str(difference_type).upper()
            if dtype in ("QUESTION_REMOVED", "SECTION_REMOVED", "CONTENT_REMOVED", "REMOVED") or (
                old_value is not None and new_value is None and not dtype.startswith("OPTIONS_")
            ):
                self.category = "removed"
            elif dtype in ("QUESTION_ADDED", "SECTION_ADDED", "CONTENT_ADDED", "ADDED") or (
                new_value is not None and old_value is None and not dtype.startswith("OPTIONS_")
            ):
                self.category = "added"
            else:
                self.category = "modified"

    def __repr__(self):
        return (
            f"Difference("
            f"difference_type={self.difference_type!r}, "
            f"question_number={self.question_number!r}, "
            f"category={self.category!r}, "
            f"old_value={self.old_value!r}, "
            f"new_value={self.new_value!r}, "
            f"message={self.message!r}, confidence={self.confidence!r}"
            f")"
        )