"""Deterministic, offline question matching.

Matching is deliberately explainable: text, token overlap, field type, options,
position and local sequence context are combined into one score. No network
service or hosted model is required.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from src.semantic import LocalVectorizer

STOPWORDS = {
    "what", "is", "your", "please", "enter", "provide", "the", "a", "an",
    "of", "for", "to", "be", "and", "or", "this", "that", "do", "does",
    "following", "question", "select", "choose", "specify", "patient",
}


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    text = text.replace("\xad", "-").lower()
    text = re.sub(r"_{2,}", " ", text)
    text = re.sub(r"[^\w\s:/()'’-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokens(text: str):
    return set(re.findall(r"[a-z0-9]+", normalize_text(text)))


def meaningful_tokens(text: str):
    return {t for t in tokens(text) if t not in STOPWORDS and len(t) > 2}


def has_meaningful_overlap(a: str, b: str) -> bool:
    return bool(meaningful_tokens(a) & meaningful_tokens(b))


def text_similarity(a: str, b: str) -> float:
    na, nb = normalize_text(a), normalize_text(b)
    if not na or not nb:
        return 0.0
    seq = SequenceMatcher(None, na, nb).ratio()
    ta, tb = tokens(na), tokens(nb)
    jaccard = len(ta & tb) / len(ta | tb) if ta | tb else 0.0
    ma, mb = meaningful_tokens(na), meaningful_tokens(nb)
    meaningful_jaccard = len(ma & mb) / len(ma | mb) if ma | mb else 0.0
    return min(1.0, 0.45 * seq + 0.25 * jaccard + 0.30 * meaningful_jaccard)


def option_similarity(a, b) -> float:
    sa = {normalize_text(x) for x in (a or []) if normalize_text(x)}
    sb = {normalize_text(x) for x in (b or []) if normalize_text(x)}
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def field_similarity(a, b) -> float:
    if not a or not b:
        return 0.5
    return 1.0 if a == b else 0.0


def position_similarity(old, new) -> float:
    """Soft positional signal; question number is evidence, not identity."""
    old_n, new_n = getattr(old, "number", None), getattr(new, "number", None)
    if old_n is None or new_n is None:
        return 0.5
    delta = abs(old_n - new_n)
    if delta == 0:
        return 1.0
    if delta == 1:
        return 0.75
    if delta == 2:
        return 0.45
    return 0.0


def neighbor_context_score(old_index, new_index, old_questions, new_questions) -> float:
    """Compare immediate neighboring question text when available.

    This helps distinguish a small renumbering from a completely different
    question. It is deliberately low-weight and therefore cannot override
    strong textual evidence.
    """
    checks = []
    for offset in (-1, 1):
        oi, ni = old_index + offset, new_index + offset
        if 0 <= oi < len(old_questions) and 0 <= ni < len(new_questions):
            checks.append(text_similarity(old_questions[oi].text, new_questions[ni].text))
    return sum(checks) / len(checks) if checks else 0.5


def explain_match(old, new, old_index=None, new_index=None, old_questions=None, new_questions=None, vectorizer=None):
    text = text_similarity(old.text, new.text)
    semantic = vectorizer.similarity(old.text, new.text) if vectorizer is not None else text
    options = option_similarity(old.options, new.options)
    field = field_similarity(old.field_type, new.field_type)
    position = position_similarity(old, new)
    neighbor = 0.5
    if old_index is not None and new_index is not None and old_questions is not None and new_questions is not None:
        neighbor = neighbor_context_score(old_index, new_index, old_questions, new_questions)

    # Text is dominant. Position and neighbors are supporting evidence only.
    score = (
        0.47 * text
        + 0.15 * semantic
        + 0.10 * options
        + 0.10 * field
        + 0.10 * position
        + 0.08 * neighbor
    )
    overlap = has_meaningful_overlap(old.text, new.text)
    return {
        "score": min(score, 1.0),
        "text_similarity": text,
        "local_vector_similarity": semantic,
        "option_similarity": options,
        "field_similarity": field,
        "position_similarity": position,
        "neighbor_context": neighbor,
        "meaningful_overlap": overlap,
    }


def match_score(old, new, old_index=None, new_index=None, old_questions=None, new_questions=None, vectorizer=None) -> float:
    return explain_match(old, new, old_index, new_index, old_questions, new_questions, vectorizer)["score"]


def _candidate_is_plausible(signals, threshold):
    score = signals["score"]
    overlap = signals["meaningful_overlap"]
    # Strong exact/near-exact text is enough. Otherwise require meaningful
    # content overlap; structural evidence alone must not create a match.
    return score >= threshold and (score >= 0.82 or overlap)


def match_diagnostics(old_questions, new_questions, threshold: float = 0.40):
    diagnostics = []
    vectorizer = LocalVectorizer([q.text for q in old_questions] + [q.text for q in new_questions])
    for oi, old in enumerate(old_questions):
        for ni, new in enumerate(new_questions):
            signals = explain_match(old, new, oi, ni, old_questions, new_questions, vectorizer)
            diagnostics.append({
                "old_index": oi, "new_index": ni,
                "old_number": getattr(old, "number", None),
                "new_number": getattr(new, "number", None),
                "old_text": old.text, "new_text": new.text,
                **{k: round(v, 4) if isinstance(v, float) else v for k, v in signals.items()},
                "accepted_candidate": _candidate_is_plausible(signals, threshold),
            })
    diagnostics.sort(key=lambda x: (-x["score"], x["old_index"], x["new_index"]))
    return diagnostics


def match_questions(old_questions, new_questions, threshold: float = 0.40):
    candidates = []
    vectorizer = LocalVectorizer([q.text for q in old_questions] + [q.text for q in new_questions])
    for oi, old in enumerate(old_questions):
        for ni, new in enumerate(new_questions):
            signals = explain_match(old, new, oi, ni, old_questions, new_questions, vectorizer)
            if _candidate_is_plausible(signals, threshold):
                candidates.append((signals["score"], oi, ni, signals))

    candidates.sort(key=lambda x: (-x[0], x[1], x[2]))
    used_old, used_new = set(), set()
    matches = []
    for score, oi, ni, signals in candidates:
        if oi in used_old or ni in used_new:
            continue
        used_old.add(oi); used_new.add(ni)
        matches.append((old_questions[oi], new_questions[ni], score, signals))

    unmatched_old = [q for i, q in enumerate(old_questions) if i not in used_old]
    unmatched_new = [q for i, q in enumerate(new_questions) if i not in used_new]
    matches.sort(key=lambda item: getattr(item[1], "number", 0))
    return matches, unmatched_old, unmatched_new
