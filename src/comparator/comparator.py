"""Local form comparison engine."""

from __future__ import annotations

from src.matcher import match_questions, normalize_text, option_similarity
from src.models.comparison_result import ComparisonResult
from src.models.difference import Difference


class FormComparator:
    def __init__(self, match_threshold: float = 0.40):
        self.match_threshold = match_threshold

    def compare(self, old_questions, new_questions):
        result = ComparisonResult()
        matches, removed, added = match_questions(
            old_questions, new_questions, threshold=self.match_threshold
        )

        for question in removed:
            result.add_difference(
                Difference(
                    "QUESTION_REMOVED",
                    question_number=question.number,
                    old_value=question.text,
                    message=f"Question {question.number} was removed: {question.text}",
                    confidence=1.0,
                )
            )

        for question in added:
            result.add_difference(
                Difference(
                    "QUESTION_ADDED",
                    question_number=question.number,
                    new_value=question.text,
                    message=f"Question {question.number} was added: {question.text}",
                    confidence=1.0,
                )
            )

        for old, new, score, signals in matches:
            result.differences.extend(self.compare_matched_question(old, new, score, signals))

        # Compare order using original list positions, not question numbers.
        # Renumbering a logical question is not itself a reorder.
        old_positions = {id(q): i for i, q in enumerate(old_questions)}
        new_positions = {id(q): i for i, q in enumerate(new_questions)}
        ordered_matches = sorted(matches, key=lambda x: old_positions[id(x[0])])
        new_positions_in_old_order = [new_positions[id(new)] for _, new, _, _ in ordered_matches]
        if new_positions_in_old_order != sorted(new_positions_in_old_order) and len(matches) > 1:
            result.add_difference(
                Difference(
                    "QUESTION_REORDERED",
                    old_value=[old.number for old, _, _, _ in ordered_matches],
                    new_value=[new.number for _, new, _, _ in ordered_matches],
                    message="One or more matched questions changed sequence/order.",
                    confidence=min(item[2] for item in ordered_matches),
                )
            )

        result.summary = self.build_summary(result.differences)
        return result

    def compare_matched_question(self, old, new, score, signals=None):
        differences = []
        question_number = new.number
        if not self.cosmetic_text_equivalent(old.text, new.text):
            differences.append(
                Difference(
                    "QUESTION_TEXT_CHANGED",
                    question_number=question_number,
                    old_value=old.text,
                    new_value=new.text,
                    message=f"Question matched with {score:.2f} similarity; text changed.",
                    confidence=score,
                )
            )

        old_options = {normalize_text(x) for x in old.options if normalize_text(x)}
        new_options = {normalize_text(x) for x in new.options if normalize_text(x)}
        added = sorted(new_options - old_options)
        removed = sorted(old_options - new_options)

        # If only one revision exposes options, report a structural option-set
        # change rather than claiming that every option was literally added or
        # removed. This is important when the older PDF exposes a plain text
        # field while the newer PDF exposes a dropdown/list.
        if not old_options and new_options:
            differences.append(
                Difference(
                    "OPTIONS_CHANGED",
                    question_number,
                    list(old_options),
                    list(new_options),
                    f"Revision exposes {len(new_options)} options; original revision had no extractable options.",
                    score,
                )
            )
        elif old_options and not new_options:
            differences.append(
                Difference(
                    "OPTIONS_CHANGED",
                    question_number,
                    list(old_options),
                    list(new_options),
                    f"Original revision exposes {len(old_options)} options; revision has no extractable options.",
                    score,
                )
            )
        else:
            if added:
                differences.append(Difference("OPTIONS_ADDED", question_number, list(old_options), list(new_options), self._option_change_message("added", added), score))
            if removed:
                differences.append(Difference("OPTIONS_REMOVED", question_number, list(old_options), list(new_options), self._option_change_message("removed", removed), score))

        if old.field_type != new.field_type and (old.field_type or new.field_type):
            differences.append(
                Difference(
                    "FIELD_TYPE_CHANGED",
                    question_number=question_number,
                    old_value=old.field_type,
                    new_value=new.field_type,
                    message=f"Field type changed from {old.field_type} to {new.field_type}.",
                    confidence=score,
                )
            )

        old_children = {normalize_text(x) for x in old.child_questions}
        new_children = {normalize_text(x) for x in new.child_questions}
        if old_children != new_children:
            differences.append(
                Difference(
                    "CHILD_LOGIC_CHANGED",
                    question_number=question_number,
                    old_value=list(old_children),
                    new_value=list(new_children),
                    message="Child-question logic changed.",
                    confidence=score,
                )
            )

        # Explicitly record a number change when the same logical question moved.
        if old.number != new.number:
            differences.append(
                Difference(
                    "QUESTION_NUMBER_CHANGED",
                    question_number=new.number,
                    old_value=old.number,
                    new_value=new.number,
                    message=f"Logical question moved from number {old.number} to {new.number}.",
                    confidence=score,
                )
            )
        return differences

    @staticmethod
    def _option_change_message(action, values):
        if len(values) <= 10:
            return f"Options {action}: {values}"
        preview = values[:5]
        return f"{len(values)} options {action}; first 5: {preview}"

    @staticmethod
    def cosmetic_text_equivalent(old_text, new_text):
        """Treat casing, punctuation, field underscores and common form annotations as cosmetic."""
        import re
        def core(value):
            value = normalize_text(value)
            value = re.sub(r"\((?:patient|optional[^)]*|not applicable[^)]*)\)", " ", value)
            value = re.sub(r"[^a-z0-9]+", " ", value)
            return re.sub(r"\s+", " ", value).strip()
        return core(old_text) == core(new_text)

    @staticmethod
    def build_summary(differences):
        summary = {}
        for d in differences:
            summary[d.difference_type] = summary.get(d.difference_type, 0) + 1
        summary["total_changes"] = len(differences)
        return summary
