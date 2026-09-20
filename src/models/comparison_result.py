class ComparisonResult:
    def __init__(self, differences=None, summary=None):
        self.differences = differences or []
        self.summary = summary or {}

    def add_difference(self, difference):
        self.differences.append(difference)

    def get_difference_count(self):
        return len(self.differences)

    def __iter__(self):
        return iter(self.differences)

    def __len__(self):
        return len(self.differences)

    def to_dict(self):
        return {
            "summary": self.summary,
            "differences": [
                {
                    "type": d.difference_type,
                    "category": getattr(d, "category", "modified"),
                    "question_number": d.question_number,
                    "section_number": d.question_number,
                    "old_value": d.old_value,
                    "new_value": d.new_value,
                    "message": d.message,
                    "confidence": d.confidence,
                }
                for d in self.differences
            ],
        }

    def __repr__(self):
        return f"ComparisonResult(differences={len(self.differences)}, summary={self.summary!r})"
